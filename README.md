# Enabling Db2 Historical Monitoring (db2histmon) - continuous diagnostic data collection and archival
When a problem with Db2 arises, and after the time-frame of the problem event. When the diagnostic messages in the db2diag.log are insufficient, it is not uncommon for IBM Db2 support or development to provide instructions to enable a specific set of diagnostic data, and wait for a re-occurrence of the problem, in order to begin narrowing the root cause.
The new Db2 Historic Monitoring (db2histmon) scripts are a successor to the older Db2 Persistent Diagnostic Data Collection scripts, and similarly collect a broad range of Db2 and Operating System diagnostic data, and retain this data for a period of time, allowing for basic triage of many types of issues. Diagnostic information is collected at various intervals (ranging from 1min to 1hour, depending on the kind of data), and can be easily customized and expanded. The scripts will collect data only while the database is activated, which can help to reduce the generation of unnecessary redundant data. 
By enabling the collection of Db2 Historical Monitoring(db2histmon), you can improve the odds that helpful diagnostic information is available after the first occurrence of a problem.

## Prerequisites
* The scripts can be deployed in any Unix or Windows environment
* setup scripts: Python2 or higher, as well as the python ibm_db module are required to execute the scripts
* loader and quickparser scripts: Python3 and the python ibm_db module
* The scripts can be deployed on any relatively modern versions of Db2 (Version 10.1, 10.5, 11.1, 11.5)
* Db2 DBADM authority is required on the database where the historic monitoring will be deployed
* A C++ compiler (for example g++ on Unix or Visual Studio on Windows) is required (in order to use bldrtn to compile the control UDFS which are used by the historical monitoring framework)

## Setup folder
The setup scripts are used to set up and deploy the historical monitoring framework and begin data collection. 
For detailed instructions, please refer to db2histmon/1_setup/README.md

## Loader folder
This loader script is a companion to the db2histmon suite. It is used to load the db2histmon data collection files into a Db2 database, so that an administrator or analyst can query or analyze the data. 
For detailed instructions, please refer to db2histmon/2_loader/README.md

## Quickparse folder
This quickparse script is a companion to the db2histmon suite. It is used to display db2histmon generated data (which are in comma delimited format) to the screen in a more human readable columnar format.
For detailed instructions, please refer to db2histmon/3_quickparse/README.md
