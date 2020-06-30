# Introduction

This program reccuringly collects monitoring data to assist in problem determination.

Each collection is referred to as a 'task'. Tasks can store the output of
SQL statements or operating SYStem commands and are scheduled using the Admin Task Scheduler.

The output from each execution of a task is stored in a seperate file: `collection_name_yrmndyhrmm.del`

The files are organized into hourly directories: `db_name_yrmndyhr`

Previous hourly directories are archived to conserve storage and
old ones are deleted once a maximum size is reached.

## Overview:


    PROC_COLLECT(DB, MON_GET_X)     PROC_COLLECT(DB, VMSTAT)
    x--------------------------x    x--------------------------x
    | MON_GET_X_yrmndyhrmm.del |    | VMSTAT_yrmndyhrmm.del    |
    x--------------------------x    x--------------------------x
                        |                   |
                        |                   |       Each scheduled execution of PROC_COLLECT outputs
                        |                   |       the results of an SQL or SYS class data collection
                        |                   |       task to a seperate file in an hourly folder
                        |                   |
                        V                   v
            x==========================================x
            || coll_path/db_yyyymmddhh (current hour) ||
            x==========================================x
                                |
                                |                   Each scheduled execution of PROC_ARCHIVE archives
                                |                   past hourly directories and deletes old ones
                                |                   if max size is exceeded
            PROC_ARCHIVE(DB)    v
            x==========================================x
            || arch_path/db_yyyymmddhh.zip (1hr ago)  ||
            x==========================================x --x
                || arch_path/db_yyyymmddhh.zip (2hrs ago) ||
                x==========================================x --x
                    || arch_path/db_yyyymmddhh.zip (3hrs ago) ||
                    x==========================================x --x
                        || deleted (4hrs ago)                     ||
                        x==========================================x


# Instructions to Get Started

As a prerequisite, python and the ibm_db module are required:
https://www.ibm.com/support/knowledgecenter/SSEPGG_11.5.0/com.ibm.swg.im.dbclient.python.doc/doc/t0054367.html

## task_details.json file

All data collection tasks and their details are defined in the task_details.json file.
A default file is provided, but it can be customized as needed. For each task,
the following fields are required:

field                      | value                                   | optional | description
---------------------------|-----------------------------------------|----------|------------
collection_name            | string <64 chars                        | required | Chosen name for the data collection task.
collection_class           | "SQL", "SYS"                            | required | Defines if the collection_command is a SQL statement, or an operating SYStem command.
collection_command         | string <32672 chars                     | required | Command to be executed.
collection_freq            | CRON format string                      | required | Frequency of collection.
collection_level           | "1", "2"                                | required | Data collection tasks can be separated into two subsets based on importance, for example, in the default file two levels are specified, with level 1 being an essential subset, and 2 being a broader subset.
collection_condition       | "PURESCALE", "HADR", "WINDOWS", "UNIX"  | optional | When specified, the task will only be scheduled if the specified environment is detected. PURESCALE if pureScale environment. HADR if High Availability Disaster Recovery environment (primary or standby).
loader_join_columns        | comma delimited list                    | optional | Used by Loader script to join outputs of consecutive executions of data collections.
loader_diff_exempt_columns | comma delimited list                    | optional | Used by Loader script to exempt columns from being diffed.
quickparse_summary_columns | comma delimited list                    | optional | Used by Quickparser script to determine which columns to display when -display 'summary' option is specified.

## To use this program:

1. Run `python setup.py _db_name_ ...options...`

    This script creates the IBMHIST schema and builds/registers all procedures/tables,
    enables Admin Task Scheduler, and schedules the tasks specified in the task_details.json file.

    It can be invoked multiple times if the task_details.json file is modified or
    if the configurations need to be updated.

    The script will need to be run from an account with admin authority, and dbadm authority on the database.
    It will also need to be run from an environment with access to a C++ compiler (For example
    g++ on Unix or Visual Studio on Windows).

    Run with `--help` for further instructions, and the configurations that can be specified.
    These include the collection and archival paths, a maximum size for the data, the archival command/extension, etc.

    Run with `--update_config_only` to update config only.
    This will update config values to passed in arguments or reset to defaults for those not explicitly specified.

    Run with `--update_tasks_only` to update tasks only.
    This will unschedule all old tasks and reschedule to match with the task_details.json file.

    Run with `--cleanup` for cleanup only.
    This will drop the IBMHIST schema and all of its objects, and unschedule its tasks.

2. Data collection tasks will start executing approximately 5 minutes after scheduling.

    If this is not the case, check the IBMHIST.TAB_ERRS for any generated errors.
    (For example `db2 "select * from IBMHIST.TAB_ERRS"`).


# Implementation Details

The program consists of procedures to collect and archive the data,
as well as tables to store configuration, task details, directory information, and errors.
These are all stored in './sql'

## Main procedures and tables:

### Procedure IBMHIST.PROC_COLLECT
Scheduled using Admin Task Scheduler to execute a SQL or SYS data collection task
(as defined in the task_details.json file) and outputs the result to a file in
the collection path. It is called with the task collection_name as an argument,
and uses it to get corresponding details such as command type, command, and header
from IBMHIST.TAB_TASKS.

### Procedure IBMHIST.PROC_ARCHIVE
Scheduled using Admin Task Scheduler to archive past directories to
archival path and delete the oldest directories if a maximum size is exceeded.
It uses IBMHIST.TAB_DIRS to keep track of all directories currently saved.

### Table IBMHIST.TAB_CONFIG
Stores configuration information including
- COLL_PATH where collection hourly directories are stored
- ARCH_PATH where archival hourly directories are stored
- MAX_SIZE which specifies in bytes the upper threshold how much collection/archival
can be stored before old directories are deleted
- ARCH_CMD which is the command used to archive the hourly folders with '\_src\_' and '\_dest\_' placeholders
(for example, `powershell -command "Compress-Archive" -Path _src_ -DestinationPath _dest_` for Windows)
- ARCH_EXT which is the extension of archived hourly directories beginning with '.'
(for example, `.zip` for Windows)
- TASK_DETAILS_PATH which indicates the path of the task_details.json file

### Table IBMHIST.TAB_TASKS
Stores information about all the tasks currently scheduled including
the task collection_name, the type of command, the command itself, and the header
which is prepended to each of the output files.

### Table IBMHIST.TAB_DIRS
Stores information about all the directories currently stored including
their path, size, status, and time of last collection.

### Table IBMHIST.TAB_ERRS
Any errors generated using execution of the procedures are outputted here.

### External C++ functions
Additionally, a set of C++ functions are required by the program to interface with the operating system
and handle operations that SQL cannot.  These can be found in external.h and external.C and are
built during setup using the bldrtn script found at sqllib/samples/cpp/bldrtn. They are registered
to Db2 as external udfs in the external.sql file.

