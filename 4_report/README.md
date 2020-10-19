# Introduction

This report script is a companion to the db2histmon suite. It generates reports similar to those in the MONREPORT module using the collected data. The reports currently supported are:
- DBSUMMARY (Similar to MONREPORT.DBSUMMARY)
- CONNECTION (Similar to MONREPORT.CONNECTION)
- PKGCACHE (Similar to MONREPORT.PKGCACHE)

## Overview

The overall structures of the reports are similar to their original counterparts.
However, to better understand changes in the database, data from multiple collections is displayed in the same report.
This is handled differently by different reports as outlined below.

### Format of DBSUMMARY and CONNECTION reports
- The collection intervals used are indicated in the header of the report.
- For each metric, the values corresponding to each interval are displayed horizontally, accross each row.
- Outliers are highlighted in red color when displayed in terminal, or preceded by an asterisk when piped to a file.

```
  ================================================================================

  Replica of MONREPORT.DBSUMMARY

  Collection time intervals:
    Interval 1: (2020-08-12 13:40:00) - (2020-08-12 13:50:00)
    Interval 2: (2020-08-12 13:50:00) - (2020-08-12 14:00:00)
    Interval 3: (2020-08-12 14:00:00) - (2020-08-12 14:10:00)
    Interval 4: (2020-08-12 14:10:00) - (2020-08-12 14:20:00)
    Interval 5: (2020-08-12 14:20:00) - (2020-08-12 14:30:00)
    Interval 6: (2020-08-12 14:30:00) - (2020-08-12 14:40:00)

  All values shown are diffs of the values at beginning and end of the interval

  Outliers are highlighted in red or preceded by an asterisk

  ================================================================================
.
.
.
  Direct I/O
    DIRECT_READS                         | 1: 24566.0     2:*36920.0     ...   6: 21062.0     |
    DIRECT_READ_REQS                     | 1: 2862.0      2:*6221.0      ...   6: 2807.0      |
.
.
.
```

### Format of PKGCACHE reports
- The collection times used are indicated in the header of the report.
- The top 10 statements for each metric are chosen based on their peak value for that metric across the collection times.
- The collection time when the peak value occured is shown in the PEAK TIME column.

```
================================================================================

Replica of MONREPORT.PKGCACHE

Collection times:
  Time   1: (2020-09-25 23:15:01)
  Time   2: (2020-09-25 23:20:00)
  Time   3: (2020-09-25 23:25:00)
  Time   4: (2020-09-25 23:30:00)

================================================================================
.
.
.
Top 10 statements by TOTAL_CPU_TIME
--------------------------------------------------------------------------------

TOTAL_CPU_TIME       PEAK TIME            STMT_TEXT
 1020659.0           2020-09-25 23:30:00   SELECT (CURRENT SQLID) INTO :H00038          FROM SYSIBM.SYSDUMMY1
  331077.0           2020-09-25 23:25:00   SELECT CURRENT TIMESTAMP AS COLLECTION_TIME, T.* FROM TABLE (MON_GET_MEMORY_...
.
.
.
```

# Instructions

As a prerequisite, python and the python pandas module are required.

To generate a report, run `python report.py collection_path ...options...`

The `collection_path` is where the collected data is stored, and must have hourly subdirectories.

The following is a list of notable options:
- `--report`: Specify which report to generate. For example, `--report connection` will generate the COLLECTION report similar to MONREPORT.CONNECTION.
- `--start_time`/`--end_time`: Display collections within this time range. The format must be identical to either the one in the report header (YYYY-mm-dd HH:MM:SS) or the COLLECTION_TIME column in the .del files (YYYY-mm-dd-HH-MM-SS.ffffff). For example, `--end_time "2020-08-12 14:20:00"` will only show collections before that time.
- `-- period`: Display collections at a lesser frequency. For example `--period 3` will show every third collection. (Only for DBSUMMARY and CONNECTION reports)
- `--stats`: show min, max, mean for each metric following a series of values. (Only for DBSUMMARY and CONNECTION reports)
- `--members`/`--application_handles`: Filter collections based on members or application handles before calculations. For example, `--members 2 3` will calculate and show data for only members 2 and 3.

# Example use cases

1. Show everything: `python report.py ./collection`
```
  ================================================================================

  Replica of MONREPORT.DBSUMMARY

  Collection time intervals:
    Interval 1: (2020-08-12 13:40:00) - (2020-08-12 13:50:00)
    Interval 2: (2020-08-12 13:50:00) - (2020-08-12 14:00:00)
    Interval 3: (2020-08-12 14:00:00) - (2020-08-12 14:10:00)
    Interval 4: (2020-08-12 14:10:00) - (2020-08-12 14:20:00)
    Interval 5: (2020-08-12 14:20:00) - (2020-08-12 14:30:00)
    Interval 6: (2020-08-12 14:30:00) - (2020-08-12 14:40:00)

  All values shown are diffs of the values at beginning and end of the interval

  Outliers are highlighted in red or preceded by an asterisk

  ================================================================================
```

2. Narrowed down problem area, show between 13:50 and 14:20: `python report.py ./collection --start_time "2020-08-12 13:50:00" --end_time "2020-08-12 14:20:00"`
```
  ================================================================================

  Replica of MONREPORT.DBSUMMARY

  Collection time intervals:
    Interval 1: (2020-08-12 13:50:00) - (2020-08-12 14:00:00)
    Interval 2: (2020-08-12 14:00:00) - (2020-08-12 14:10:00)
    Interval 3: (2020-08-12 14:10:00) - (2020-08-12 14:20:00)

  All values shown are diffs of the values at beginning and end of the interval

  Outliers are highlighted in red or preceded by an asterisk

  ================================================================================
```

3. Too many collections, use every 2nd collection: `python report.py ./collection --period 2`
(only for DBSUMMARY and CONNECTION reports)
```
  ================================================================================

  Replica of MONREPORT.DBSUMMARY

  Collection time intervals:
    Interval 1: (2020-08-12 13:40:00) - (2020-08-12 14:00:00)
    Interval 2: (2020-08-12 14:00:00) - (2020-08-12 14:20:00)
    Interval 3: (2020-08-12 14:20:00) - (2020-08-12 14:40:00)

  All values shown are diffs of the values at beginning and end of the interval

  Outliers are highlighted in red or preceded by an asterisk

  ================================================================================
```

4. Would like to see stats for the values currently displayed: `python report.py ./collection --stats`
(only for DBSUMMARY and CONNECTION reports)
```
  Direct I/O
    DIRECT_READS                         | 1: 24566.0     2: 36920.0     ...   6: 21062.0     | min=17034.0         | max=36920.0         | mean=24182.67        |
    DIRECT_READ_REQS                     | 1: 2862.0      2: 6221.0      ...   6: 2807.0      | min=1608.0          | max=6221.0          | mean=3100.17         |
```

5. See results for only members 2 and 3: `python report.py ./collection --members 2 3`
```
  Direct I/O
    DIRECT_READS                         | 1: 278.0       2: 296.0       ...   6: 266.0       |
    DIRECT_READ_REQS                     | 1: 38.0        2: 39.0        ...   6: 37.0        |
```
Note the lower values when compared to using all members in above examples.
