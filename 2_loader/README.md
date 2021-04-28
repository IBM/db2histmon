## INTRODUCTION
This loader script is a companion to the db2histmon suite. It is used to load the db2histmon data collection files into a Db2 database, so that an administrator or analyst can query or analyze the data. 
The loader script currently only supports the loading of db2histmon delimited data of data_collection_class 'SQL', and not raw operating system data of data_collection_class 'SYS'. 
The path to the db2histmon data collection files is passed to the loader script as an input argument. 
The loader script will parse the embedded task_details.json file to extract information about each unique data_collection_class in the data set. 
The loader script will create a table for each unique data collection class, and populate it from all iterations of files for that collection class (a COLLECTIONTIME column is included to differentiate data from different data collection iterations).

## SETUP
Setup required by the script:
1. install python3 
2. install ibm_db module and set up the library path
https://www.ibm.com/support/knowledgecenter/SSEPGG_11.5.0/com.ibm.swg.im.dbclient.python.doc/doc/t0054367.html
3. run the python script (as specified below)

usage: loader.py [-h] -d DBNAME -sourcePath SOURCEPATH
  -h, --help            show this help message and exit
  
  -d DBNAME, -dbname DBNAME (required)
                        Target database to load the data into
                        
  -sourcePath SOURCEPATH (required)
                        The path which contains the db2histmon data collection directory.
                        E.g. /home/db2inst1/sqllib/db2dump/IBMHIST_SAMPLE
                   
  -dataCollectionName   
                        Data collection name, as defined in the task_details.json file.
                        If not specified, all data collections will be loaded.

  -startDate           
                         Start timestamp of interested collected data
                        (Must be of format YYYY-MM-DD-hh.mm.ss)
			
  -endDate              
                        End timestamp of interested collected data 
                        (Must be of format YYYY-MM-DD-hh.mm.ss)
                        
### Note: 
1. The task_details.json file is embedded in the db2histmon data collection directory, stored under each hourly collection period. 
This file is used by the db2histmon setup scripts to define the attributes of each data collection, and include details about join columns, exemption columns, and diff columns which are used by this loader script. 
See the Setup script README for further details about the attributes of this file.

## SAMPLE USAGE:
python3 loader.py -d sample -sourcePath /home/yunpeng/IBMHIST_DTW/ -startDate 2020-05-10-10.00.00 -endDate 2020-05-12-08.08.09

## EXAMPLES OF QUERYING THE DATA:
1. Display all data collection tables:
   db2 "select TABNAME from SYSIBMADM.ADMINTABINFO where tabschema='IBMHIST'"
     
```
TABNAME                                                                                                                         
----------------------------------------------------------------------------------------------------------
MON_GET_PAGE_ACCESS_INFO_DELTA                                                                                                  
MON_GET_SERVERLIST                                                                                                              
MON_GET_TABLE                                                                                                                   
MON_GET_TABLE_DELTA                                                                                                             
MON_GET_CONNECTION                                                                                                              
MON_GET_CONNECTION_DELTA                                                                                                        
MON_GET_ACTIVITY                                                                                                                
MON_GET_PAGE_ACCESS_INFO                                                                                                        
MON_GET_UNIT_OF_WORK                                                                                                            
MON_GET_UNIT_OF_WORK_DELTA                                                                                                      
MON_GET_ACTIVITY_DELTA                                                                                                          
ENV_CF_SYS_RESOURCES                                                                                                            
ENV_GET_SYSTEM_RESOURCES                                                                                                        
MON_CURRENT_SQL                                                                                                                 
MON_CURRENT_SQL_DELTA                                                                                                           
MON_GET_APPL_LOCKWAIT                                                                                                           
MON_GET_BUFFERPOOL                                                                                                              
MON_GET_BUFFERPOOL_DELTA                                                                                                        
MON_GET_CF                                                                                                                      
MON_GET_CF_WAIT_TIME                                                                                                            
MON_GET_CF_WAIT_TIME_DELTA                                                                                                      
MON_GET_EXTENDED_LATCH_WAIT                                                                                                     
MON_GET_EXTENDED_LATCH_WAIT_DELTA                                                                                               
MON_GET_MEMORY_POOL                                                                                                             
MON_GET_MEMORY_POOL_DELTA                                                                                                       
MON_GET_MEMORY_SET                                                                                                              
MON_GET_MEMORY_SET_DELTA                                                                                                        

  27 record(s) selected.
```
  
2. Display the highest CPU consuming queries from the IBMHIST.MON_GET_PKG_CACHE_STMT data collection:
   
   db2 "select COLLECTION_TIME, TOTAL_CPU_TIME, substr(STMT_TEXT, 1, 50) from IBMHIST.MON_GET_PKG_CACHE_STMT order by TOTAL_CPU_TIME desc fetch first 5 rows"
   
