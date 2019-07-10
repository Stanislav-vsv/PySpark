#!/opt/anaconda/bin/python3

import argparse
import sys
import os


parser = argparse.ArgumentParser(description="Arguments")
parser.add_argument('--DATABASE')
parser.add_argument('--TMP_DATABASE')
parser.add_argument('--JIRA_USER')
parser.add_argument('--JIRA_PASSWORD')
parser.add_argument('--INITIAL_LOAD')
parser.add_argument('--KERBEROS_PRINCIPAL')
parser.add_argument('--HIVE_PRINCIPAL')
parser.add_argument('--HIVE_URI')
args = parser.parse_args()

# Workaround for spark

if os.environ.get('SPARK_HOME'):
    PYSPARK_PYTHON = os.environ['SPARK_HOME']+'/python'
    sys.path.append(PYSPARK_PYTHON)
    sys.path.append(PYSPARK_PYTHON+'/lib/py4j-0.10.4-src.zip')


# HDFS OOZIE Workaround for local modules
sys.path.append(os.getcwd())
sys.path.append(os.getcwd()+'/lib')


import dateutil.parser
from subprocess import call
from jira_api import *
import pyspark.sql
from pyspark.sql.functions import *
from pyspark.sql import SparkSession
from pyspark.sql.column import Column, _to_java_column


## Because of Spark 2.2!!!
def explode_outer_(col):
    _explode_outer = spark.sparkContext._jvm.org.apache.spark.sql.functions.explode_outer
    return Column(_explode_outer(_to_java_column(col)))

# uncomment for local
# spark = SparkSession.builder\
#     .appName('testapp') \
#     .master("local") \
#     .getOrCreate()
#


# try:
#     call(f'kinit {args.KERBEROS_PRINCIPAL} -kt KERBEROS_KEYTAB', shell=True)
#     os.system(f'kinit {args.KERBEROS_PRINCIPAL} -kt KERBEROS_KEYTAB')
#     call('klist', shell=True)
#     call('id', shell=True)
#     call('hadoop fs -ls /user/oozie/share/lib/', shell=True)
# except Exception as e:
#     print("Terminating program because of Kerberos: ", e)
#     exit(1)

try:
    print('Creating Session')  # TODO Remove on production
    spark = SparkSession.builder\
        .appName('jiraEtl') \
        .master('yarn-client') \
        .config('spark.yarn.principal', args.KERBEROS_PRINCIPAL) \
        .config('spark.yarn.keytab', 'KERBEROS_KEYTAB') \
        .config('spark.driver.memory', '4096m') \
        .config('spark.yarn.executor.memoryOverhead', '16192m') \
        .config('hive.metastore.sasl.enabled', 'true') \
        .config('hive.security.authorization.enabled', 'false') \
        .config('hive.metastore.kerberos.principal', args.HIVE_PRINCIPAL) \
        .config('hive.metastore.uris', args.HIVE_URI) \
        .config('hive.metastore.execute.setugi', 'true') \
        .enableHiveSupport() \
        .getOrCreate()
except Exception as e:
    print("Cannot create session, because of: ", e)
    exit(1)



# .config("spark.yarn.security.tokens.hive.enabled", "false") \
# .config('spark.sql.warehouse.dir', '/user/u_m10k4/db/') \

issues_temp_view = 'jira_issues_temp_view'
comments_temp_view = 'jira_comments_temp_view'

db_schema = args.DATABASE
db_tmp_schema = args.TMP_DATABASE
initial_load = args.INITIAL_LOAD

user = args.JIRA_USER
password = args.JIRA_PASSWORD

session = jira_login(user, password, jira_endpoint='http://jira.moscow.alfaintra.net/rest/auth/1/session')

fields = ['project',
          'description',
          'summary',
          'subtasks',
          'status',
          'creator',
          'assignee',
          'duedate',
          'issuetype',
          'customfield_24779',
          'comment',
          'created',
          'resolutiondate',
          'updated']

try:
    print("Load from Jira")  # TODO remove on production
    if initial_load == 'y':
        response = paging_for_issues("Улучшение клиентских впечатлений", "type",
                                     expand='operations,versionedRepresentations,editmeta,changelog,renderedFields',
                                     user=user, password=password, fields=fields, jira_endpoint='http://jira.moscow.alfaintra.net/rest/api/2/')
    else:
        last_date = spark.sql(f"select max(updated) from {db_schema}.jira_clientfeedback_issues").head()[0]
        # start_from = dateutil.parser.parse(last_date).strftime("%Y-%m-%d")
        start_from = last_date.strftime("%Y-%m-%d")
        response = paging_for_issues("Улучшение клиентских впечатлений", "type",
                                     expand='operations,versionedRepresentations,editmeta,changelog,renderedFields',
                                     user=user, password=password, fields=fields, jira_endpoint='http://jira.moscow.alfaintra.net/rest/api/2/',
                                     datefrom=start_from)
except Exception as e:
    print("Something gone wrong with JIRA API: ", e)
    exit(1)

result = json.dumps(response, indent=4, sort_keys=True)

with open('temp_file', 'w') as temp_file:
    print(result, file=temp_file)
    try:
        print("Put temp file to hadoop")  # TODO remove on production
        call('hadoop fs -put -f temp_file temp_file', shell=True)
    except Exception as e:
        print("Error while copying files to HDFS", e)
        exit(1)

df = spark.read.json('temp_file', multiLine=True)

try:
    print('Transforming df dataframe')  # TODO remove on production
    df = df.select('issues') \
        .withColumn('issues_flat', explode(col('issues'))) \
        .drop('issues')

    df = df.select('issues_flat.*') \
           .drop('issues_flat')

    df = df.select('id', 'key', 'self', 'fields.*') \
           .drop('fields')

except pyspark.sql.utils.AnalysisException as e:
    print('something gone wrong on base transformations: ', e)
    exit(1)


try:
    df = df.select('id', 'key', 'self',
                   'assignee', 'comment', to_timestamp(df['created'], "yyyy-MM-dd'T'HH:mm:ss.SSS").alias('created'),
                   'creator', 'description', 'duedate',
                   'issuetype', 'project', df['customfield_24779.value'].alias('products'), 'resolutiondate', 'status',
                   'summary', to_timestamp(df['updated'], "yyyy-MM-dd'T'HH:mm:ss.SSS").alias('updated'), 'subtasks') \
        .withColumn('subtasks_l', explode_outer_(col('subtasks'))) \
        .drop('subtasks')
except pyspark.sql.utils.AnalysisException as e:
    # If 'subtasks_l' field is empty it is not unwrapped structure
    if str(e).find('need struct type but got string') != -1:  # if string will be founded
        print('Exception catched!', e)  # TODO remove on production
        df = df.select('id', 'key', 'self',
                       'assignee', 'comment', to_timestamp(df['created'], "yyyy-MM-dd'T'HH:mm:ss.SSS").alias('created'),
                       'creator', 'description', 'duedate',
                       'issuetype', 'project', df['customfield_24779'].alias('products'), 'resolutiondate',
                       'status',
                       'summary', to_timestamp(df['updated'], "yyyy-MM-dd'T'HH:mm:ss.SSS").alias('updated'), 'subtasks') \
            .withColumn('subtasks_l', explode_outer_(col('subtasks'))) \
            .drop('subtasks')
    else:
        print("something gone wrong with df dataframe:", e)
        exit(1)


try:
    df = df.select('id', 'key', 'self',
                   df['assignee.displayName'].alias('assignee'), 'comment', 'created',
                   df['creator.displayName'].alias('creator'), 'description', 'duedate',
                   df['issuetype.name'].alias('issuetype'), df['project.key'].alias('project'), 'products',
                   'resolutiondate', df['status.name'].alias('status'),
                   'summary', 'updated', df['subtasks_l.key'].alias('subtasks_key')) \
        .drop('subtasks_l')
except pyspark.sql.utils.AnalysisException as e:
    # If 'subtasks_l' field is empty it is not unwrapped structure
    if str(e).find('need struct type but got string') != -1:  # if string will be founded
        print('Exception catched!', e)  # TODO remove on production
        df = df.select('id', 'key', 'self',
                       df['assignee.displayName'].alias('assignee'), 'comment', 'created',
                       df['creator.displayName'].alias('creator'), 'description', 'duedate',
                       df['issuetype.name'].alias('issuetype'), df['project.key'].alias('project'), 'products',
                       'resolutiondate', df['status.name'].alias('status'),
                       'summary', 'updated', df['subtasks_l'].alias('subtasks_key')) \
            .drop('subtasks_l')
    else:
        print("something gone wrong with df dataframe:", e)
        exit(1)


comments = df.select('comment', 'key')
comments_are_not_empty = True
df = df.drop('comment')

try:
    comments = comments.select('key', explode(col('comment.comments'))) \
        .drop('comment') \
        .select('key', 'col.*') \
        .drop('col')

    comments = comments.select('id', 'key', 'author', 'body',
                to_timestamp(comments['created'], "yyyy-MM-dd'T'HH:mm:ss.SSS").alias('created'),
                'self', 'updateAuthor', to_timestamp(comments['updated'], "yyyy-MM-dd'T'HH:mm:ss.SSS").alias('updated'))
except Exception as e:
    if str(e).find('Can only star expand struct data types') != -1:
        print('Exception catched!', e)
        comments_are_not_empty = False
    else:
        print("something gone wrong with comments dataframe", e)
else:
    comments = comments.select('key', comments['author.displayName'].alias('author'),
                               'body', to_timestamp(comments['created'], "yyyy-MM-dd'T'HH:mm:ss.SSS").alias('created'),
                               'id', 'self',
                               comments['updateAuthor.displayName'].alias('updateAuthor'),
                               to_timestamp(comments['updated'], "yyyy-MM-dd'T'HH:mm:ss.SSS").alias('updated'))


df.createOrReplaceTempView(issues_temp_view)
if comments_are_not_empty:
    comments.createOrReplaceTempView(comments_temp_view)

# Moved to hql scripts
# create_issues_src_table = f"""CREATE TABLE IF NOT EXISTS {db_tmp_schema}.jira_clientfeedback_issues_src
#     ROW FORMAT SERDE
#         "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
#     STORED AS INPUTFORMAT
#         "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
#     OUTPUTFORMAT
#         "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
#     TBLPROPERTIES ("kite.compression.type"="snappy")
# AS SELECT
# id, key, self, assignee, created, creator,
# description, duedate, issuetype, project, products, resolutiondate, status, updated, summary, subtasks_key FROM {issues_temp_view}
# """
#
# create_issues_tmp_table = f"""CREATE TABLE IF NOT EXISTS {db_tmp_schema}.jira_clientfeedback_issues_tmp
#     ROW FORMAT SERDE
#         "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
#     STORED AS INPUTFORMAT
#         "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
#     OUTPUTFORMAT
#         "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
#     TBLPROPERTIES ("kite.compression.type"="snappy")
# AS SELECT
# id, key, self, assignee, created, creator,
# description, duedate, issuetype, project, products, resolutiondate, status, updated, summary, subtasks_key FROM {issues_temp_view}
# """
#
# create_issues_prod_table = f"""CREATE TABLE IF NOT EXISTS {db_schema}.jira_clientfeedback_issues
#     ROW FORMAT SERDE
#         "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
#     STORED AS INPUTFORMAT
#         "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
#     OUTPUTFORMAT
#         "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
#     TBLPROPERTIES ("kite.compression.type"="snappy")
# AS SELECT
# id, key, self, assignee, created, creator,
# description, duedate, issuetype, project, products, resolutiondate, status, updated, summary, subtasks_key FROM {issues_temp_view}
# """

overwrite_issues_src_table = f"""INSERT OVERWRITE TABLE {db_tmp_schema}.jira_clientfeedback_issues_src
SELECT
id, key, self, assignee, created, creator,
description, duedate, issuetype, project, products, resolutiondate, status, updated, summary, subtasks_key FROM {issues_temp_view}
"""

get_old_issues_without_increment = f"""INSERT OVERWRITE TABLE {db_tmp_schema}.jira_clientfeedback_issues_tmp
SELECT b.id as id, b.key as key, b.self as self, b.assignee as assignee,
b.created as created, b.creator as creator, b.description as description, b.duedate as duedate,
b.issuetype as issuetype, b.project as project, b.products as products, b.resolutiondate as resolutiondate,
b.status as status, b.updated as updated, b.summary as summary, b.subtasks_key as subtasks_key
FROM {db_schema}.jira_clientfeedback_issues b LEFT JOIN {db_tmp_schema}.jira_clientfeedback_issues_src a
ON b.id = a.id WHERE a.id is null
"""

load_increment_issues = f"""INSERT INTO {db_tmp_schema}.jira_clientfeedback_issues_tmp
SELECT
id, key, self, assignee, created, creator,
description, duedate, issuetype, project, products, resolutiondate, status, updated, summary, subtasks_key
FROM {db_tmp_schema}.jira_clientfeedback_issues_src
"""

reload_tmp_production_issues = f"""INSERT OVERWRITE TABLE {db_schema}.jira_clientfeedback_issues
SELECT
id, key, self, assignee, created, creator,
description, duedate, issuetype, project, products, resolutiondate, status, updated, summary, subtasks_key
FROM {db_tmp_schema}.jira_clientfeedback_issues_tmp
"""

# Moved to hql scripts
# create_comments_src_table = f"""CREATE TABLE IF NOT EXISTS {db_tmp_schema}.jira_clientfeedback_comments_src
#     ROW FORMAT SERDE
#         "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
#     STORED AS INPUTFORMAT
#         "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
#     OUTPUTFORMAT
#         "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
#     TBLPROPERTIES ("kite.compression.type"="snappy")
# AS SELECT
# id, key, author, body, created, self, updateAuthor, updated FROM {comments_temp_view}
# """
#
# create_comments_tmp_table = f"""CREATE TABLE IF NOT EXISTS {db_tmp_schema}.jira_clientfeedback_comments_tmp
#     ROW FORMAT SERDE
#         "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
#     STORED AS INPUTFORMAT
#         "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
#     OUTPUTFORMAT
#         "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
#     TBLPROPERTIES ("kite.compression.type"="snappy")
# AS SELECT
# id, key, author, body, created, self, updateAuthor, updated FROM {comments_temp_view}
# """
#
# create_comments_prod_table = f"""CREATE TABLE IF NOT EXISTS {db_schema}.jira_clientfeedback_comments
#     ROW FORMAT SERDE
#         "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
#     STORED AS INPUTFORMAT
#         "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
#     OUTPUTFORMAT
#         "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
#     TBLPROPERTIES ("kite.compression.type"="snappy")
# AS SELECT
# id, key, author, body, created, self, updateAuthor, updated FROM {comments_temp_view}
# """


overwrite_comments_src_table = f"""INSERT OVERWRITE TABLE {db_tmp_schema}.jira_clientfeedback_comments_src
SELECT
id, key, author, body, created, self, updateAuthor, updated FROM {comments_temp_view}
"""

get_old_comments_without_increment = f"""INSERT OVERWRITE TABLE {db_tmp_schema}.jira_clientfeedback_comments_tmp
SELECT b.id as id, b.key as key, b.author as author, b.body as body, b.created as created, b.self as self,
b.updateAuthor as updateAuthor, b.updated as updated
FROM {db_schema}.jira_clientfeedback_comments b LEFT JOIN {db_tmp_schema}.jira_clientfeedback_comments_src a
ON b.id = a.id WHERE a.id is null
"""

load_increment_comments = f"""INSERT INTO {db_tmp_schema}.jira_clientfeedback_comments_tmp
SELECT
id, key, author, body, created, self, updateAuthor, updated
FROM {db_tmp_schema}.jira_clientfeedback_comments_src
"""

reload_tmp_production_comments = f"""INSERT OVERWRITE TABLE {db_schema}.jira_clientfeedback_comments
SELECT
id, key, author, body, created, self, updateAuthor, updated
FROM {db_tmp_schema}.jira_clientfeedback_comments_tmp
"""

try:
    print('spark sql tasks')  # TODO remove on production
    # Deleted because of moved HQL scripts
    # if initial_load == 'y':
    #     spark.sql(create_issues_src_table)
    #     spark.sql(create_issues_tmp_table)
    #     spark.sql(create_issues_prod_table)
    #     spark.sql(create_comments_src_table)
    #     spark.sql(create_comments_tmp_table)
    #     spark.sql(create_comments_prod_table)

    spark.sql(overwrite_issues_src_table)
    spark.sql(get_old_issues_without_increment)
    spark.sql(load_increment_issues)
    if int(spark.sql(f'select count(1) from {db_tmp_schema}.jira_clientfeedback_issues_tmp').head()[0]) > 0:
        spark.sql(reload_tmp_production_issues)
    else:
        print("Something with temp table gone wrong!")
        exit(1)
    if comments_are_not_empty:
        print('spark sql tasks for comments dataframe') # TODO remove on production
        spark.sql(overwrite_comments_src_table)
        spark.sql(get_old_comments_without_increment)
        spark.sql(load_increment_comments)
        if int(spark.sql(f'select count(1) from {db_tmp_schema}.jira_clientfeedback_comments_tmp').head()[0]) > 0:
            spark.sql(reload_tmp_production_comments)
        else:
            print("Something with temp table gone wrong!")
            exit(1)
except Exception as e:
    print("Exception while executing spark.sql:", e)
    exit(1)


## For Debug reasons only!!:
# for table in ['jira_clientfeedback_comments', 'jira_clientfeedback_comments_src',
#               'jira_clientfeedback_comments_tmp', 'jira_clientfeedback_issues',
#               'jira_clientfeedback_issues_src', 'jira_clientfeedback_issues_tmp']:
#     print(table)
#     spark.sql(f'select count(1) from u_m10k4.{table}').show()

#
# drop table d_sourcedata.jira_clientfeedback_comments;
# drop table d_sourcedata.jira_clientfeedback_comments_src;
# drop table d_sourcedata.jira_clientfeedback_comments_tmp;
# drop table d_sourcedata.jira_clientfeedback_issues;
# drop table d_sourcedata.jira_clientfeedback_issues_src;
# drop table d_sourcedata.jira_clientfeedback_issues_tmp;

