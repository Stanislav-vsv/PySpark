CREATE TABLE IF NOT EXISTS ${DATABASE}.jira_clientfeedback_comments(
id STRING,
key STRING,
author STRING,
body STRING,
created TIMESTAMP,
self STRING,
updateAuthor STRING,
updated TIMESTAMP
)
ROW FORMAT SERDE
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
STORED AS INPUTFORMAT
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat'
OUTPUTFORMAT
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
TBLPROPERTIES ('kite.compression.type'='snappy');