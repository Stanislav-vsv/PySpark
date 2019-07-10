#!/usr/bin/env bash
err=0
custom_mode=0
import_user_properties() {
    if [[ -f /home/${username}/properties/hive_params.sh ]]
    then
        source /home/${username}/properties/hive_params.sh
    else
        echo "ERROR: There is no hive_params in /home/${username}/properties/"
        err=1
    fi
}

err_check() {
    if [[ err -eq 1 ]];
    then
        read -p "WARNING: Errors detected! Continue? (Y/n): " answer
        [[ ! ${answer} =~ ^("y"|"Y") ]] && exit 1
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

arg_parse $@
username=$(whoami) #DO NOT REMOVE!

#---!!!Should be in root of hive_scripts catalog:  ..oozie_patches/C111111/hive_scripts/run_hive_scripts.sh
#---!!!Params to Configure!!!---
hive2_jdbc_url=jdbc:hive2://bda11node04.moscow.alfaintra.net:10000/default
hive2_server_principal=hive/bda11node04.moscow.alfaintra.net@BDA.MOSCOW.ALFAINTRA.NET

env_prefix_storage=s
env_storage_root_storage=/storage
env_prefix_livesystem=l
env_storage_root_livesystem=/live_system
env_prefix_datamart=l
# ------------------------------

import_user_properties
err_check

for dir in */ ; do
	case "$(echo "${dir}" | cut -d'_' -f1)" in
		"s")
		env_prefix=${env_prefix_storage}
		env_storage_root=${env_storage_root_storage}
		;;
		"l")
		env_prefix=${env_prefix_livesystem}
		env_storage_root=${env_storage_root_livesystem}
		;;
	esac
	
	DATABASE=${env_prefix}_$(echo "${dir}" | cut -d@ -f1 | cut -c3-)
	TMP_DATABASE=${DATABASE}
	PATH_TO_TMP=${env_storage_root}/${DATABASE}/db
	environment=${env_prefix}
	environment_path=${env_storage_root}/${environment}
	mart_environment=${env_prefix_datamart}

	if [[ ${custom_mode} -eq 1 ]]; then
	    echo "RUNNING CUSTOM CONFIGURATION"
        DATABASE=${custom_DATABASE}
        TMP_DATABASE=${custom_TMP_DATABASE}
        PATH_TO_TMP=${custom_PATH_TO_TMP}
        environment=${custom_environment}
        environment_path=${custom_environment_path}
        mart_environment=${custom_env_prefix_datamart}
#        FOR DEBUG REASONS
#        echo PARAMS: ${DATABASE} ${TMP_DATABASE} ${PATH_TO_TMP} ${environment}
	fi
	
	#exceptions
	case "$TMP_DATABASE" in
		"s_dwh_tmp") PATH_TO_TMP=/storage/s_dwh/tmp
		;;
		"s_odh_tmp") PATH_TO_TMP=/storage/s_odh/tmp
		;;
	esac
	
	echo "----------------------------------------------------------------"
	echo "Database: ${DATABASE}"
	echo "Path: ${PATH_TO_TMP}"
	echo "----"

	for filename in ${dir}/*.hql; do
		beeline -u "${hive2_jdbc_url};principal=${hive2_server_principal}" -f "${filename}" --hivevar mart_environment="${mart_environment}" --hivevar DATABASE="${DATABASE}" --hivevar TMP_DATABASE="${TMP_DATABASE}" --hivevar PATH_TO_TMP="${PATH_TO_TMP}" --hivevar environment="${environment}" --hivevar environment_path="${environment_path}"
	done
done