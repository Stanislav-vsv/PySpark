CREATE EXTERNAL TABLE ${TMP_DATABASE}.jira_clientfeedback_issues_tmp(
id STRING,
key STRING,
self STRING,
assignee STRING,
created TIMESTAMP,
creator STRING,
description STRING,
duedate STRING,
issuetype STRING,
project STRING,
products STRING,
resolutiondate STRING,
status STRING,
updated TIMESTAMP,
summary STRING,
subtasks_key STRING
)
ROW FORMAT SERDE
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
STORED AS INPUTFORMAT
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat'
OUTPUTFORMAT
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
'${PATH_TO_TMP}/jira_clientfeedback_issues_tmp';
