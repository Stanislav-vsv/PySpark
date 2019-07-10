#!/usr/bin/env bash

HDFS_WF_HOME_DIR=/user/${USER}/oozie_workflows
UNIX_WF_HOME_DIR=/home/${USER}/oozie_workflows
PATCH_HOME_DIR=${PWD}


# Перенос новой версии функционала из патча в Unix
cp -Rf ${PATCH_HOME_DIR}/atom/* ${UNIX_WF_HOME_DIR}/atom
cp -Rf ${PATCH_HOME_DIR}/ctl/* ${UNIX_WF_HOME_DIR}/ctl
cp -Rf ${PATCH_HOME_DIR}/reg/* ${UNIX_WF_HOME_DIR}/reg
cp -Rf ${PATCH_HOME_DIR}/man/* ${UNIX_WF_HOME_DIR}/man

hadoop fs -put -f ${PATCH_HOME_DIR}/atom/* ${HDFS_WF_HOME_DIR}/atom
hadoop fs -put -f ${PATCH_HOME_DIR}/ctl/* ${HDFS_WF_HOME_DIR}/ctl
hadoop fs -put -f ${PATCH_HOME_DIR}/reg/* ${HDFS_WF_HOME_DIR}/reg
hadoop fs -put -f ${PATCH_HOME_DIR}/man/* ${HDFS_WF_HOME_DIR}/man


for d in $(find $PATCH_HOME_DIR/atom/* -maxdepth 0 -type d) ; do
	hadoop fs -mkdir ${HDFS_WF_HOME_DIR}/atom/$(basename $d)/lib

	if [[ ${d} =~ 'jira' ]]
	then
	    hadoop fs -put -f ${PATCH_HOME_DIR}/../hdfs_home/libs/jira_api.py ${HDFS_WF_HOME_DIR}/atom/$(basename $d)/lib
	fi
	
	if [[ ${d} != *"wf_cc"* ]] && [[ ${d} != *"wf_rcndo"* ]] && [[ ${d} != *"wf_rcpay"* ]] && [[ ${d} != *"wf_sm_rep"* ]] && [[ ${d} != *"wf_lm_lm1"* ]] && [[ ${d} != *"wf_olimpus"* ]] && [[ ${d} != *"wf_cbdb"* ]]
	then
		hadoop fs -put -f ${PATCH_HOME_DIR}/../hdfs_home/libs/ojdbc6.jar ${HDFS_WF_HOME_DIR}/atom/$(basename $d)/lib 
	else
		hadoop fs -put -f ${PATCH_HOME_DIR}/../hdfs_home/libs/sqljdbc4-4.0.jar ${HDFS_WF_HOME_DIR}/atom/$(basename $d)/lib 
	fi
done


hadoop fs -put -f ${PATCH_HOME_DIR}/../hdfs_home/scripts/* /user/${USER}/scripts

hadoop fs -put -f ${PATCH_HOME_DIR}/../hdfs_home/libs/generator-1.0-SNAPSHOT-jar-with-dependencies.jar /user/${USER}/libs