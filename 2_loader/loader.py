#!/usr/bin/env python3
################################################################################
## (c) Copyright IBM Corp. 2020 All rights reserved.
##
## The following sample of source code ("Sample") is owned by International
## Business Machines Corporation or one of its subsidiaries ("IBM") and is
## copyrighted and licensed, not sold. You may use, copy, modify, and
## distribute the Sample in any form without payment to IBM, for the purpose of
## assisting you in the development of your applications.
##
## The Sample code is provided to you on an "AS IS" basis, without warranty of
## any kind. IBM HEREBY EXPRESSLY DISCLAIMS ALL WARRANTIES, EITHER EXPRESS OR
## IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
## MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. Some jurisdictions do
## not allow for the exclusion or limitation of implied warranties, so the above
## limitations or exclusions may not apply to you. IBM shall not be liable for
## any damages you suffer as a result of using, copying, modifying or
## distributing the Sample, even if IBM has been advised of the possibility of
## such damages.
################################################################################

################################################################################
## Script name: loader.py
## Version : 1.00
################################################################################

import sys, os
import argparse
import getpass
import ibm_db
import re
import json
from pathlib import Path
import time

collectionTimeColName = "COLLECTION_TIME"
monTSName = "HISTMON"
delExt = "_DELTA"
schemaName = "IBMHIST"
tempTsName = "MONTMP32K"
bp32kName = "MONBP32K"
taskDetailFileName = "task_details_copy.json"

# Set up preconditions. Set up the table space with proper page size.
def createDBObjects(conn):
  # Drop the system temporary table space
  try:
    stmt = ibm_db.exec_immediate(conn, "drop tablespace {}".format(tempTsName))
  except:
     pass

  # Drop tables
  try:
    print("Drop table space", monTSName)
    stmt = ibm_db.exec_immediate(conn,"drop tablespace {}".format(monTSName))
  except:
    pass

  # Drop buffer pool
  try:
    stmt = ibm_db.exec_immediate(conn, "drop bufferpool {}".format(bp32kName))
  except:
    pass

  # Create buffer pool and table spaces
  stmt = ibm_db.exec_immediate(conn, "create bufferpool {} pagesize 32K".format(bp32kName))
  stmt = ibm_db.exec_immediate(conn, "create system temporary tablespace {} pagesize 32K bufferpool {}".format(tempTsName, bp32kName))
  print("Create table space", monTSName)
  stmt = ibm_db.exec_immediate(conn,"create tablespace {} pagesize 32K bufferpool {}".format(monTSName, bp32kName))

  return 0

def main():
  # Parse the input arguments
  parser = argparse.ArgumentParser()
  parser.add_argument("-d","-dbname", dest="dbname", required=True, help = "Target database to load the data into")
  parser.add_argument("-sourcePath", dest="sourcePath", required=True, help = "Path containing output from Historical Monitorinig. E.g. /home/db2inst1/sqllib/db2dump/IBMHIST_SAMPLE")
  parser.add_argument("-dataCollectionName", dest="dataCollectionName", help = "Data collection name, as defined in the task_details.json file")
  parser.add_argument("-startDate", dest="startDate", help = "Start timestamp (Default: localtime) (Must be of format YYYY-MM-DD-hh.mm.ss)")
  parser.add_argument("-endDate", dest="endDate", help = "End timestamp (Default: localtime) (Must be of format YYYY-MM-DD-hh.mm.ss)")
  args = parser.parse_args()
  sourcePath = Path(args.sourcePath)
  # Check if the raw data path exists
  if not sourcePath.exists():
    print("Raw data folder is not found: ", sourcePath)
    exit(1)
 
  print("Connecting to database:", args.dbname)
  conn = ibm_db.connect(args.dbname, '', '')

  # Set up preconditions
  createDBObjects(conn)
  
  # When -startDate and -endDate are specified, filter the qualified raw files 
  startDate, endDate = args.startDate, args.endDate
  if startDate and endDate:
    startTs = time.mktime(time.strptime(startDate, '%Y-%m-%d-%H.%M.%S'))
    startHour = time.mktime(time.strptime(startDate[:startDate.find('.')], '%Y-%m-%d-%H'))
    endTs = time.mktime(time.strptime(endDate, '%Y-%m-%d-%H.%M.%S'))
    endHour = time.mktime(time.strptime(endDate[:endDate.find('.')], '%Y-%m-%d-%H'))
    hourDirList = [hourDir for hourDir in sourcePath.glob('*_??????????') if startHour <= time.mktime(time.strptime(hourDir.name[-10:], '%Y%m%d%H')) <= endTs ]
  else:
    hourDirList = [hourDir for hourDir in sourcePath.glob('*_??????????')]

  if not hourDirList:
    print("No hourly directory found in {}".format(sourcePath))
    exit(1)

  # Load task details from json file
  searchTaskDetailFile = [file for file in hourDirList[0].glob(taskDetailFileName)]
  if searchTaskDetailFile:
    taskDetailFile = searchTaskDetailFile.pop()
  else:
    print("Task details file {} is not found under {}".format(taskDetailFileName, hourDirList[0]))
    exit(1)
  print("Loading tasks from task_details.json ...")
  with open(taskDetailFile) as file:
    tasks = json.load(file)

  # For each SQL task, import the data and delta data into tables if needed
  for task in tasks:
    collectionName = task['collection_name']
    if args.dataCollectionName and args.dataCollectionName != collectionName:
      continue
    if task['collection_class'] == "SQL":
      # Find raw data files
      fileList = []
      if startDate and endDate:
        files = list(sourcePath.rglob(collectionName + "*.del"))
        for file in files:
          tsPattern = re.search("[0-9]{12}", file.name)
          if tsPattern:
            fileTs = time.mktime(time.strptime(tsPattern.group(0), "%Y%m%d%H%M"))
            if startTs <= fileTs <= endTs:
              fileList.append(file)
        if not fileList:
          print("No raw data file found for {} with the time range from {} to {}".format(collectionName, startDate, endDate))
          continue
      else:
        fileList = list(sourcePath.rglob(collectionName + "*.del"))
      if not fileList:
        print("No raw data file found for {}".format(collectionName))
        continue
      tableName = schemaName + '.' + collectionName
      deltaTableName = tableName + delExt

      # Create the data table
      print("Creating the data table:",tableName) 
      createTable = "create table {} as ( {} ) WITH NO DATA NOT LOGGED INITIALLY IN {}".format(tableName, task['collection_command'], monTSName)
      stmt = ibm_db.exec_immediate(conn, createTable)
      
      # Load data into table
      print("Loading data into", tableName)
      for file in fileList:
        importCmd = "CALL SYSPROC.ADMIN_CMD('import from {} of del insert into {}' )".format(file, tableName)
        stmt = ibm_db.exec_immediate(conn, importCmd)

      # Check whether we need to create and load the delta table
      if task['loader_diff_exempt_columns'] != "ALL":
        print("Creating the delta data table:",deltaTableName)
        createDeltaTable = "create table {} as ( {} ) WITH NO DATA NOT LOGGED INITIALLY IN {}".format(deltaTableName, task['collection_command'], monTSName)
        stmt = ibm_db.exec_immediate(conn, createDeltaTable)
 
        # Read column names and types from the describe command
        desCmd = "CALL SYSPROC.ADMIN_CMD('describe table {} show detail' )".format(deltaTableName)
        tabDes = ibm_db.exec_immediate(conn, desCmd)
        loadDeltaStmt = "insert into {} (".format(deltaTableName)
        alterColList, colList = [], ""
        exemptionColList = [col.strip() for col in task['loader_diff_exempt_columns'].split(',')]
        joinColumns = [col.strip() for col in task['loader_join_columns'].split(",") ]
        orderByList = ','.join(joinColumns + [collectionTimeColName])
        tuple = ibm_db.fetch_tuple(tabDes)
        while tuple != False:
          colName, colType = tuple[0], tuple[2]
          loadDeltaStmt = "{} {},".format(loadDeltaStmt, colName)
          if colType in ["TIMESTAMP", "BIGINT"] and colName not in exemptionColList:
            if colType == "TIMESTAMP":
              alterColList.append(colName)
              colList="{} COALESCE(TIMESTAMPDIFF(2, current.{} - previous.{}), 0),".format(colList, colName, colName)
            else:
              colList="{} COALESCE(current.{} - previous.{}, 0),".format(colList, colName, colName)
          else:
            colList = "{} current.{},".format(colList, colName)
          tuple = ibm_db.fetch_tuple(tabDes)

        # Alter the column data type from TIMESTAMP to BIGINT
        for col in alterColList:
          stmt = ibm_db.exec_immediate(conn,"alter table {} alter column {} set data type bigint".format(deltaTableName, col))
          stmt = ibm_db.exec_immediate(conn, "CALL SYSPROC.ADMIN_CMD('reorg table {}' )".format(deltaTableName))
          stmt = ibm_db.exec_immediate(conn, "commit")

        # Remove the last comma and append the closing bracket
        loadDeltaStmt = loadDeltaStmt.rstrip(',') + ")"
        colList = colList.rstrip(',')
        loadDeltaStmt = "{} with current as ( SELECT ( row_number() over ( order by {} ) ) rowId, \
                         {}.* from {} order by {} ) select ".format(loadDeltaStmt, orderByList, tableName, tableName, orderByList)
        # Append the column list
        loadDeltaStmt += colList
        # Append the join clause
        loadDeltaStmt = "{} FROM current AS previous RIGHT JOIN current ON previous.rowId + 1 = current.rowId ".format(loadDeltaStmt)
        for col in joinColumns:
          loadDeltaStmt = "{} and previous.{} = current.{} ".format(loadDeltaStmt, col, col)
       
        # Load the delta data into table
        print("Loading data into", deltaTableName)
        stmt = ibm_db.exec_immediate(conn, loadDeltaStmt)

  print("Closing connection ...")
  ibm_db.close(conn)

if __name__== "__main__":
  main()


