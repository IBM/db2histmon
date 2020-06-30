## INTRODUCTION 
This quickparse script is a companion to the db2histmon suite. It is used to display db2histmon generated data (which are in comma delimited format) to the screen in a more human readable columnar format. The quickparse script currently only supports the loading of db2histmon delimited data of data_collection_class 'SQL', and not raw operating system data of data_collection_class 'SYS'.
If the -applHandle option is specified, the quickparse will only display data for that specific application handle.
If the -display 'summary' option is specified, the quickparse script will parse the embedded task_details.json file to extract information about which columns should be displayed. If the 'details' option is specified then all columns are displayed.

## SETUP 
Setup required by the script:
1. install python3 (if not already installed)
2. run the python script (as specified below)

## QUICKPARSE INPUT PARAMETERS
python3 quickparse.py   -dataCollectionName <data_collection_name> 
                        -sourcePath <path where data resides> 
                        -display <summary | details> 
                        -startDate <start-date-timestamp> -endDate <end-date-timestamp> 
                        -applHandle <application_handle>
                        
where 
  -dataCollectionName   Data collection name, as defined in the task_details.json file.
                        E.g. MON_GET_CONNECTION, MON_GET_BUFFERPOOL, ...
                        
                        
  -sourcePath           The path where the db2histmon generated data resides.
                        E.g. /home/db2inst1/sqllib/db2dump/IBMHIST_SAMPLE
                        
  -display {summary,details}
                        Display either a summary of the columns in the data source, or all columns.
                        (The summary columns for the data source type are defined in the quickparse_summary_columns attribute within the task_details.json file).
                        
  -startDate            Start timestamp of interested collected data (Default: localtime) 
                        (Must be of format YYYY-MM-DD-hh.mm.ss)
                        
  -endDate              End timestamp of interested collected data (Default: localtime) 
                        (Must be of format YYYY-MM-DD-hh.mm.ss)
                        
  -applHandle           If applHandle is specified, it only displays data that
                        matches the application handle

### Note: 
1. The task_details.json file is embedded in the db2histmon data collection directory, stored under each hourly collection period. This file is used by the db2histmon setup scripts to define the attributes of each data collection type, and include details about summary columns that are used by the quickparse script. See the Setup script README for further details about the attributes of this file.
2. The -display 'details' option will often generate output that wraps beyond the terminal screen, and may still be difficult to view. Consider redirecting this output to a file and viewing it with an viewer/editor with the 'no wrap' option enabled."

## Sample usage:
Senario 1: Show summary columns for the MON_GET_CONNECTION data collection type from 2020-01-22-10.00.00 to 2020-01-23-08.08.09

python3 quickparse.py -dataCollectionName MON_GET_CONNECTION -sourcePath /home/yunpeng/IBMHIST_DTW/ -display summary -startDate 2020-01-22-10.00.00 -endDate 2020-01-23-08.08.09
```
                COLLECTION_TIME   MEMBER   COORD_MEMBER   APPLICATION_HANDLE         APPLICATION_NAME              APPLICATION_ID          CONNECTION_START_TIME
   "2020-01-22-10.00.01.000000"        0              0                   13                 "db2fw1"   "*LOCAL.DB2.200122140120"   "2020-01-22-09.01.15.345152"
   "2020-01-22-10.00.01.000000"        0              0                   26                "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-10.00.01.000000"        0              0                   19                 "db2fw7"   "*LOCAL.DB2.200122140126"   "2020-01-22-09.01.15.354036"
   "2020-01-22-10.00.01.000000"        0              0                   32   "db2evml_DB2DETAILDEA"   "*LOCAL.DB2.200122140139"   "2020-01-22-09.01.15.380183"
   "2020-01-22-10.00.01.000000"        0              0                   12                 "db2fw0"   "*LOCAL.DB2.200122140119"   "2020-01-22-09.01.15.343616"
   "2020-01-22-10.00.01.000000"        0              0                   25                "db2fw13"   "*LOCAL.DB2.200122140132"   "2020-01-22-09.01.15.363003"
   "2020-01-22-10.00.01.000000"        0              0                   18                 "db2fw6"   "*LOCAL.DB2.200122140125"   "2020-01-22-09.01.15.352576"
   "2020-01-22-10.00.01.000000"        0              0                   31                "db2cmpd"   "*LOCAL.DB2.200122140138"   "2020-01-22-09.01.15.373077"
   "2020-01-22-10.00.01.000000"        0              0                   11             "db2dbctrld"   "*LOCAL.DB2.200122140118"   "2020-01-22-09.01.15.342136"
   "2020-01-22-10.00.01.000000"        0              0                   24                "db2fw12"   "*LOCAL.DB2.200122140131"   "2020-01-22-09.01.15.361585"
   "2020-01-22-10.00.01.000000"        0              0                   17                 "db2fw5"   "*LOCAL.DB2.200122140124"   "2020-01-22-09.01.15.351061"
   "2020-01-22-10.00.01.000000"        0              0                   30                 "db2mcd"   "*LOCAL.DB2.200122140137"   "2020-01-22-09.01.15.370367"
   "2020-01-22-10.00.01.000000"        0              0                   10               "db2lused"   "*LOCAL.DB2.200122140117"   "2020-01-22-09.01.15.340573"
   "2020-01-22-10.00.01.000000"        0              0                   23                "db2fw11"   "*LOCAL.DB2.200122140130"   "2020-01-22-09.01.15.359918"
   "2020-01-22-10.00.01.000000"        0              0                   16                 "db2fw4"   "*LOCAL.DB2.200122140123"   "2020-01-22-09.01.15.349572"
   "2020-01-22-10.00.01.000000"        0              0                    9                "db2wlmd"   "*LOCAL.DB2.200122140116"   "2020-01-22-09.01.15.338960"
   "2020-01-22-10.00.01.000000"        0              0                   22                "db2fw10"   "*LOCAL.DB2.200122140129"   "2020-01-22-09.01.15.358452"
   "2020-01-22-10.00.01.000000"        0              0                   15                 "db2fw3"   "*LOCAL.DB2.200122140122"   "2020-01-22-09.01.15.348152"
   "2020-01-22-10.00.01.000000"        0              0                   28                "db2pcsd"   "*LOCAL.DB2.200122140135"   "2020-01-22-09.01.15.367461"
   "2020-01-22-10.00.01.000000"        0              0                    8               "db2taskd"   "*LOCAL.DB2.200122140115"   "2020-01-22-09.01.15.337245"
   "2020-01-22-10.00.01.000000"        0              0                   21                 "db2fw9"   "*LOCAL.DB2.200122140128"   "2020-01-22-09.01.15.356987"
   "2020-01-22-10.00.01.000000"        0              0                   14                 "db2fw2"   "*LOCAL.DB2.200122140121"   "2020-01-22-09.01.15.346663"
   "2020-01-22-10.00.01.000000"        0              0                   27                "db2fw15"   "*LOCAL.DB2.200122140134"   "2020-01-22-09.01.15.366005"
   "2020-01-22-10.00.01.000000"        0              0                   20                 "db2fw8"   "*LOCAL.DB2.200122140127"   "2020-01-22-09.01.15.355508"   
```   

Scenario 2: Show the summary for the MON_GET_CONNECTION data collection type from 2020-01-22-09.00.00 to 2020-01-23-08.08.09 that matches <appl_handl>.

python3 quickparse.py -dataCollectionName MON_GET_CONNECTION -sourcePath /home/yunpeng/IBMHIST_DTW/ -display summary -startDate 2020-01-22-09.00.00 -endDate 2020-01-23-08.08.09 -applHandle 26
```
                COLLECTION_TIME   MEMBER   COORD_MEMBER   APPLICATION_HANDLE   APPLICATION_NAME              APPLICATION_ID          CONNECTION_START_TIME
   "2020-01-22-09.12.02.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.15.01.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.18.01.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.21.01.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.24.01.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.27.02.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.30.01.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.33.01.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.36.01.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.39.01.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.42.01.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.45.01.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.48.01.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.51.02.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.54.01.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-09.57.01.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
   "2020-01-22-10.00.01.000000"        0              0                   26          "db2fw14"   "*LOCAL.DB2.200122140133"   "2020-01-22-09.01.15.364556"
```

Scenario 3: Show the details for DB_GET_CFG data collectoin type from 2020-05-09-20.00.00 -endDate 2020-05-09-21.08.09

python3 quickparse.py -dataCollectionName DB_GET_CFG -sourcePath /home/yunpeng/IBMHIST_BLUDB/ -display details -startDate 2020-05-09-20.00.00 -endDate 2020-05-09-21.08.09
```
                COLLECTION_TIME                     NAME       VALUE   VALUE_FLAGS    DEFERRED_VALUE   DEFERRED_VALUE_FLAGS          DATATYPE   DBPARTITIONNUM   MEMBER
   "2020-05-09-20.00.00.314209"        "app_ctl_heap_sz"       "256"        "NONE"             "256"                 "NONE"         "INTEGER"                0       0

   "2020-05-09-20.00.00.314209"        "appgroup_mem_sz"     "20000"        "NONE"           "20000"                 "NONE"          "BIGINT"                0       0

   "2020-05-09-20.00.00.314209"            "appl_memory"     "40000"   "AUTOMATIC"           "40000"            "AUTOMATIC"          "BIGINT"                0       0

   "2020-05-09-20.00.00.314209"             "applheapsz"       "256"   "AUTOMATIC"             "256"            "AUTOMATIC"          "BIGINT"                0       0

   "2020-05-09-20.00.00.314209"         "archretrydelay"        "20"        "NONE"              "20"                 "NONE"         "INTEGER"                0       0

   "2020-05-09-20.00.00.314209"   "authn_cache_duration"         "3"        "NONE"               "3"                 "NONE"        "SMALLINT"                0       0

   "2020-05-09-20.00.00.314209"      "authn_cache_users"         "0"        "NONE"               "0"                 "NONE"        "SMALLINT"                0       0

   "2020-05-09-20.00.00.314209"          "auto_cg_stats"       "OFF"        "NONE"             "OFF"                 "NONE"      "VARCHAR(3)"                0       0

   "2020-05-09-20.00.00.314209"         "auto_db_backup"       "OFF"        "NONE"             "OFF"                 "NONE"      "VARCHAR(3)"                0       0
   
   ......
   
   Printing the output into a file with no wrap provides a more readable view.
```
