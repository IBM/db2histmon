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
## Script name: quickparse.py
## Version : 1.00
################################################################################

import sys
import os
import argparse
import re
import time
import json
from pathlib import Path

firstCol = "SCHEDULEDTIME"
colTimeColName = "COLLECTION_TIME"
colTimeColIndex = 0
applHandleColName = "APPLICATION_HANDLE"
taskDetailFileName = "task_details_copy.json"

# Read raw data from raw files and print the data in tabular format.
def readAndPrintData(columns, fileList, summaryCols, applHandle, dataType):
  rawData = []
  if summaryCols == "ALL":
    for file in fileList:
      with open(file, encoding="latin-1") as f:
        # Skip the first line which are the column names
        next(f)
        for line in f:
          detailLine = line.encode('ascii', 'ignore').decode('ascii').split(',')
          if matchApplHandle(detailLine, applHandle, columns):
            rawData.append(detailLine)
    if not rawData:
      print("Data not found for {}".format(dataType))
      exit(1)
    # Sort the collection data by COLLECTION_TIME
    rawData.sort()
    printTabularData([columns] + rawData)
    print("Printing the output into a file with no wrap provides a more readable view.")
  else:
    summaryColsIn = [col.strip() for col in summaryCols.split(",") ]
    summaryIndex, summaryCols = [colTimeColIndex], [colTimeColName]
    for col in summaryColsIn:
      try:
        index = columns.index(col)
      except ValueError:
        print(col,"is not a valid column name.")
      else:
        summaryIndex.append(index)
        summaryCols.append(col)
    for file in fileList:
      with open(file, encoding="latin-1") as f:
        # Skip the first line which are the column names
        next(f)
        for line in f:
          lineList = line.encode('ascii', 'ignore').decode('ascii').split(',')
          summaryLine = [lineList[i] for i in summaryIndex]
          # Filter the raw data by application handle if needed
          if matchApplHandle(lineList, applHandle, columns):
            rawData.append(summaryLine)
    if not rawData:
      print("Data not found for {}".format(dataType))
      exit(1)
    # Sort the collection data by COLLECTION_TIME
    rawData.sort()
    printTabularData([summaryCols] + rawData)

# Helper function to print the raw data in tabular format
def printTabularData(table):
  longest_cols = [ (max([len(str(row[i])) for row in table]) + 3) for i in range(len(table[0]))]
  row_format = "".join(["{:>" + str(longest_col) + "}" for longest_col in longest_cols])
  for row in table:
    print(row_format.format(*row))

# Check if the given data record matches the specified application handle.
def matchApplHandle(line, applHandle, columns):
  if applHandle:
    try: 
      applHandleIndex = columns.index(applHandleColName)
    except ValueError:
      print("{} is not a valid column name.".format(applHandleColName))
      print("The -applHandle option is not supported for this data type.")
      exit(1)
    else:
      if line[applHandleIndex] != applHandle:
        return False
  return True

def main():
  # read parameters from command line;
  parser = argparse.ArgumentParser()
  parser.add_argument("-dataCollectionName", dest="dataCollectionName", required=True,  help = "Data collection name, as defined in the task_details.json file.")
  parser.add_argument("-sourcePath", dest="sourcePath", required=True,  help = "The path the historical data. E.g. /home/db2inst1/sqllib/db2dump/IBMHIST_SAMPLE")
  parser.add_argument("-display", dest="displayMode", choices=['summary', 'details'], help = "Display subset/all of the table function columns")
  parser.add_argument("-startDate", dest="startDate", help = "Start timestamp (Default: localtime) (Must be of format YYYY-MM-DD-hh.mm.ss)")
  parser.add_argument("-endDate", dest="endDate", help = "End timestamp (Default: localtime) (Must be of format YYYY-MM-DD-hh.mm.ss)")
  parser.add_argument("-applHandle", dest="applHandle", help = "If applHandle is specified we only show data that matches the application_handle")

  args = parser.parse_args()
 
  # Check if the input source path exists
  basePath = Path(args.sourcePath)
  if not basePath.exists():
    print("Raw data folder is not found: ", basePath)
    exit(1)
  dataType = args.dataCollectionName

  # Based on the start timestamp and the end timestamp provided, find the qualified hourly directories
  startDate, endDate = args.startDate, args.endDate
  startTs = time.mktime(time.strptime(startDate, '%Y-%m-%d-%H.%M.%S')) if startDate else time.time()
  startHour = time.mktime(time.strptime(startDate[:startDate.find('.')], '%Y-%m-%d-%H')) if startDate else time.time()
  endTs = time.mktime(time.strptime(endDate, '%Y-%m-%d-%H.%M.%S')) if endDate else time.time()
  endHour = time.mktime(time.strptime(endDate[:endDate.find('.')], '%Y-%m-%d-%H')) if endDate else time.time()
  hourDirList = [hourDir for hourDir in basePath.glob('*_??????????') if startHour <= time.mktime(time.strptime(hourDir.name[-10:], '%Y%m%d%H')) <= endTs ]
  if not hourDirList:
    print("No hourly directory found with startDate: {} and endDate: {}".format(startDate, endDate))
    exit(1)

  # Find the task details file and read the defined summary columns in summary display mode
  summaryCols = "ALL"
  if args.displayMode == "summary":
    searchTaskDetailFile = [file for file in hourDirList[0].glob(taskDetailFileName)]
    if searchTaskDetailFile:
      taskDetailFile = searchTaskDetailFile.pop()
    else:
      print("Task details file {} is not found under {}".format(taskDetailFileName, hourDirList[0]))
      exit(1)
    with open(taskDetailFile) as file:
      tasks = json.load(file)
    for task in tasks:
      if task['collection_name'] == dataType:
        if task['collection_class'] != "SQL":
          print("Data type {} with command type {} is not supported.".format(dataType, task['collection_class']))
          exit(1) 
        summaryCols = task['quickparse_summary_columns']
  
  # Find the qualified raw data files based on the time range given
  fileList = []
  for dir in hourDirList:
    files = list(dir.glob(dataType + "_*.del"))
    for file in files:
      tsPattern = re.search("[0-9]{12}", file.name)
      if tsPattern:
        fileTs = time.mktime(time.strptime(tsPattern.group(0), "%Y%m%d%H%M"))
        if startTs <= fileTs <= endTs:
          fileList.append(file)
      else:
        print("Invalid raw data file name: {}".format(file))
  if not fileList:
    print("No raw data file found with the time range from {} to {}".format(startDate, endDate))
    exit(1)

  # Read the first line of a sample raw data file to get the column names
  with open(fileList[0], encoding="latin-1") as file:
    columnLine = file.readline().split(',')
  columns = [col.strip().strip('\n') for col in columnLine]
    
  # Read raw data from files and print the data
  readAndPrintData(columns, fileList, summaryCols, args.applHandle, dataType)

if __name__== "__main__":
    main()

