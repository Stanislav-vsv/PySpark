#!/usr/bin/env bash
#VERSION1
err=0

err_check() {
    if [[ err -eq 1 ]];
    then
        read -p "WARNING: Errors detected! Continue? (Y/n): " answer
        [[ ! ${answer} =~ ^("y"|"Y") ]] && exit 1
    fi
}

import_user_properties() {
    if [[ -f /home/${user_name}/properties/oozie_params.sh ]]
    then
        source /home/${user_name}/properties/oozie_params.sh
    else
        echo "ERROR: There is no oozie_params.sh in /home/${user_name}/properties/"
        err=1
    fi
}

arg_parse() {
    if [[ $# > 0 ]]
      then
        for arg in "$@"; do
        [[ ${arg} =~ "custom" ]] && custom_mode=1
        done
    fi
}

custom_mode() {
## TODO convert to list
if [[ ${custom_mode} -eq 1 ]]; then
    hive2_server_principal=${custom_hive2_server_principal}
    hive2_jdbc_url=${custom_hive2_jdbc_url}
    oracle_jdbc_url=${custom_oracle_jdbc_url}
    oracle_jdbc_user=${custom_oracle_jdbc_user}
    oracle_jdbc_password=${custom_oracle_jdbc_password}

    coord_start_time=${custom_coord_start_time}
    coord_end_time=${custom_coord_end_time}


    DATABASE=${custom_DATABASE}
    TMP_DATABASE=${custom_TMP_DATABASE}
    PATH_TO_TMP=${custom_PATH_TO_TMP}
    TMP_TABLE_TYPE=${custom_TMP_TABLE_TYPE}
    echo RUNNING IN CUSTOM CONFIGURATION!
fi
}

user_name=$(whoami) #DO NOT REMOVE!
# Params to Configure
#------------------------------------------------------------------
# Cluster settings moved to oozie_params.sh (/home/<USERNAME>/properties/oozie_params.sh)

# Workflow Path Parameters moved to oozie_params.sh (/home/<USERNAME>/properties/oozie_params.sh)
#------------------------------------------------------------------
# Hive settings moved to oozie_params.sh (/home/<USERNAME>/properties/oozie_params.sh)
# ADD YOUR JOB PROPERTIES HERE:

KERBEROS_PRINCIPAL="tech_oozie@BDA.MOSCOW.ALFAINTRA.NET"
KERBEROS_KEYTAB="/user/tech_oozie/config/tech_oozie.keytab"
JIRA_USER="debitsvzn_tech_user"
JIRA_PASSWORD="6yfn^THC"
INITIAL_LOAD="y"

coord_start_time=2019-06-17T10:00+0300
coord_end_time=2019-06-17T11:00+0300

DATABASE=t_sourcedata
TMP_DATABASE=t_sourcedata

#------------------------------------------------------------------

### Injection for running jobs inluding personal parameters
arg_parse $@
import_user_properties
custom_mode
err_check

# Workflow to Run ##TODO needed to be automatic path
workflow_application_path=${wf_man_path}/crd_hist_jira_clientfeedback

echo "Run oozie job.."
# Run Oozie Job
oozie job -auth KERBEROS \
-D nameNode="${nameNode}" \
-D wf_reg_path="${wf_reg_path}" \
-D wf_ctl_path="${wf_ctl_path}" \
-D wf_atom_path="${wf_atom_path}" \
-D workflow_application_path="${workflow_application_path}" \
-D coord_start_time="${coord_start_time}" \
-D coord_end_time="${coord_end_time}" \
-D ORA_USER="${ORA_USER}" \
-D ORA_PASSWORD="${ORA_PASSWORD}" \
-D DATABASE="${DATABASE}" \
-D TMP_DATABASE="${TMP_DATABASE}" \
-D PATH_TO_TMP="${PATH_TO_TMP}" \
-D TMP_TABLE_TYPE="${TMP_TABLE_TYPE}" \
-D INITIAL_LOAD="${INITIAL_LOAD}" \
-D KERBEROS_KEYTAB="${KERBEROS_KEYTAB}" \
-D KERBEROS_PRINCIPAL="${KERBEROS_PRINCIPAL}" \
-D jobTracker="${jobTracker}" \
-D hive2_server_principal="${hive2_server_principal}" \
-D hive2_jdbc_url="${hive2_jdbc_url}" \
-D hcat_metastore_uri="${hcat_metastore_uri}" \
-D oracle_jdbc_url="${oracle_jdbc_url}" \
-D oracle_jdbc_user="${oracle_jdbc_user}" \
-D oracle_jdbc_password="${oracle_jdbc_password}" \
-D user_name="${user_name}" \
-D connection_string="${connection_string}" \
-D JIRA_USER="${JIRA_USER}" \
-D JIRA_PASSWORD="${JIRA_PASSWORD}" \
-D "oozie.coord.application.path"="${workflow_application_path}" \
-D "oozie.use.system.libpath"=true \
-run