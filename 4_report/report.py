import argparse
import os
import io
import codecs
import re, glob, json
import numpy as np
import pandas as pd

# collection time format
collection_time_format = '%Y-%m-%d-%H.%M.%S.%f'

# global output variables
label_chars = 40
value_chars = 15
str_chars = 80
stats = False

# cached lobs
lob_cache = dict()

# function to create dataframe from collections based on name
def collection_to_df(collection_name):

    # look for collection files
    files = glob.glob( '*/'+ collection_name +'_*.del' )
    assert files, "No " + collection_name + " files found."

    # load all files into dataframes
    # dfs = [pd.read_csv(file) for file in files]
    dfs = []
    for file in files:
        with codecs.open(file, 'r', encoding='utf-8', errors='ignore') as f:
            # need to replace null bytes so binary data does not terminate
            f = f.read()
            f = f.replace('\x00', '.')
            f = io.StringIO(f)
            # load file into dataframe
            dfs.append( pd.read_csv(f) )

    # concatante all the dataframes together
    df = pd.concat( dfs )

    return df

# function to read lobs from lob id
def get_lob(lob_id):

    global str_chars, lob_cache

    # return lob from lob cache if previously read
    if lob_id in lob_cache:
        return lob_cache[lob_id]

    # parse components of lob id
    lob_id_parsed = lob_id[:-1].split('.')
    if len(lob_id_parsed) < 2:
        return "LOB_ID: " + lob_id + " INCORRECT FORMAT"

    lob_file = '.'.join(lob_id_parsed[:-2])
    lob_start, lob_size = int(lob_id_parsed[-2]), int(lob_id_parsed[-1])

    # get matching lob files
    lob_files = glob.glob( '*/lob/'+ lob_file )
    if not lob_files:
        return "LOB_FILE: " + lob_file + " NOT FOUND"

    # read lob file and get lob
    with open(lob_files[0], 'rb') as lob:
        lob = lob.read()
        lob = lob.replace(b'\x00', b'.')
        lob = lob[lob_start : lob_start + lob_size]
        lob = lob.decode('utf-8')
        lob = lob.ljust(str_chars-1)

    # cache to lob cache and return lob
    lob_cache[lob_id] = lob
    return lob

# function to convert series to a string with values and additional information
def series_to_str(series, round_places=2, sep='|', prefix='', suffix='', z_threshold=3):

    global stats
    global value_chars

    string = ''

    # reset index
    series = series.reset_index(drop=True)

    # numerical values
    if series.dtype == np.float64 or series.dtype == np.int64:

        string += ' ' + sep

        # append values to string
        for i, v in enumerate(series.to_list()):

            # remove current value for outlier calculations
            # as it can skew results for small series
            series_wo_val = series.drop(i)

            # calculate z = ( v - mean ) / std wihout current value
            with np.errstate(divide='ignore', invalid='ignore'):
                z = ( v - series_wo_val.mean() ) / series_wo_val.std()

            # if z > z_threshold or z < -z_threshold, consider value as outlier
            outlier, color_begin, color_end = ' ', '', ''
            if abs(z) > z_threshold:
                # color outlier as red if being outputted to terminal
                if os.fstat(0) == os.fstat(1):
                    color_begin, color_end = '\033[91m', '\033[0m'
                # place asterisk next to outlier if being outputted to file
                else:
                    outlier = '*'

            # append value to string
            string += color_begin + ( ' ' + str(i+1) + ':' + outlier + prefix + str(round(v, round_places)) + suffix ).ljust(value_chars) + color_end

        string += ' ' + sep

        # append stats to string
        if stats:
            string += " min=" + str( round(series.min(), round_places) ).ljust(value_chars)
            string += ' ' + sep
            string += " max=" + str( round(series.max(), round_places) ).ljust(value_chars)
            string += ' ' + sep
            string += " mean=" + str( round(series.mean(), round_places) ).ljust(value_chars)
            string += ' ' + sep
            # string += " std=" + str( round(series.std(), round_places) ).ljust(value_chars)
            # string += ' ' + sep

    # string values
    else:

        string += ' ' + sep

        # append values to string
        for i, v in enumerate(series.to_list()):

            # append value to string
            string += ( ' ' + str(i+1) + ': ' + prefix + str(v) + suffix ).ljust(value_chars)

        string += ' ' + sep

    return string

# function to print seperator
def print_seperator(lines):

    if lines == 0:
        print( "" )
    elif lines == 1:
        print( "--------------------------------------------------------------------------------" )
        print( "" )
    elif lines == 2:
        print( "" )
        print( "================================================================================" )
        print( "" )

# function to print header and collection times
def print_header(report, collection_times=None, period=1, diff=False, outliers=False):

    print_seperator(2)

    # print report name
    print( "Replica of %s" % report )

    # print collection times
    if collection_times is not None:

        print_seperator(0)

        # print collection intervals if diff
        if diff:
            print( "Collection time intervals:" )
            for i in range(period, len(collection_times), period):
                print( "  Interval %s: (%s) - (%s)" % ( str(int(i/period)).rjust(3) , collection_times[i-period], collection_times[i] ) )
            print_seperator(0)
            print( "All values shown are diffs of the values at beginning and end of the interval" )

        # print collection times if absolute values
        else:
            print( "Collection times:" )
            for i in range(period, len(collection_times), period):
                print( "  Time %s: (%s)" % ( str(int(i/period)).rjust(3), collection_times[i] ) )

        # print outliers message
        if outliers:
            print_seperator(0)
            print( "Outliers are highlighted in red or preceded by an asterisk" )

    print_seperator(2)

# function to print common req metrics
# requires mon_get_database or mon_get connection with diff values
def print_common_req_metrics(df):

    global label_chars

    print( "Work volume and throughput" )
    print_seperator(1)

    # print( "                                  Per second             Total" )
    # print( "                                  ---------------------  -----------------------" )
    # print( "TOTAL_APP_COMMITS                 0                      0" )
    series = df['TOTAL_APP_COMMITS']
    print( "TOTAL_APP_COMMITS".ljust(label_chars) + series_to_str(series) )
    series = df['TOTAL_APP_COMMITS'] / df['SECONDS_ELAPSED']
    print( "  Per second".ljust(label_chars) + series_to_str(series) )
    # print( "ACT_COMPLETED_TOTAL               0                      0" )
    series = df['ACT_COMPLETED_TOTAL']
    print( "ACT_COMPLETED_TOTAL".ljust(label_chars) + series_to_str(series) )
    series = df['ACT_COMPLETED_TOTAL'] / df['SECONDS_ELAPSED']
    print( "  Per second".ljust(label_chars) + series_to_str(series) )
    # print( "APP_RQSTS_COMPLETED_TOTAL         0                      0" )
    series = df['APP_RQSTS_COMPLETED_TOTAL']
    print( "APP_RQSTS_COMPLETED_TOTAL".ljust(label_chars) + series_to_str(series) )
    series = df['APP_RQSTS_COMPLETED_TOTAL'] / df['SECONDS_ELAPSED']
    print( "  Per second".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    series = df['TOTAL_CPU_TIME']
    print( "TOTAL_CPU_TIME".ljust(label_chars) + series_to_str(series) )
    series = df['TOTAL_CPU_TIME'] / df['APP_RQSTS_COMPLETED_TOTAL']
    print( "  Per request".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    print( "Row processing" )
    # print( "  ROWS_READ/ROWS_RETURNED         = 0 (0/0)" )
    series = df['ROWS_READ'] / df['ROWS_RETURNED']
    print( "  ROWS_READ/ROWS_RETURNED".ljust(label_chars) + series_to_str(series) )
    series = df['ROWS_READ']
    print( "    ROWS_READ".ljust(label_chars) + series_to_str(series) )
    series = df['ROWS_RETURNED']
    print( "    ROWS_RETURNED".ljust(label_chars) + series_to_str(series) )
    series = df['ROWS_MODIFIED']
    print( "  ROWS_MODIFIED".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    print( "Wait times" )
    print_seperator(1)

    print( "-- Wait time as a percentage of elapsed time --" )
    print_seperator(0)

    # print( "                                         %    Wait time/Total time" )
    # print( "                                         ---  ----------------------------------" )
    # print( "For requests                             0    0/0" )
    print( "For requests" )
    series = 100 * ( df['TOTAL_WAIT_TIME'] / df['TOTAL_RQST_TIME'] )
    print( "  Percent Wait time/Total time".ljust(label_chars) + series_to_str(series, suffix='%') )
    series = df['TOTAL_WAIT_TIME']
    print( "    Wait time".ljust(label_chars) + series_to_str(series) )
    series = df['TOTAL_RQST_TIME']
    print( "    Total time".ljust(label_chars) + series_to_str(series) )
    # print( "For activities                           0    0/0" )
    print( "For activities" )
    series = 100 * ( df['TOTAL_ACT_WAIT_TIME'] / df['TOTAL_ACT_TIME'] )
    print( "  Percent Wait time/Total time".ljust(label_chars) + series_to_str(series, suffix='%') )
    series = df['TOTAL_ACT_WAIT_TIME']
    print( "    Wait time".ljust(label_chars) + series_to_str(series) )
    series = df['TOTAL_ACT_TIME']
    print( "    Total time".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    print( "-- Time waiting for next client request --" )
    print_seperator(0)

    series = df['CLIENT_IDLE_WAIT_TIME']
    print( "CLIENT_IDLE_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    series = df['CLIENT_IDLE_WAIT_TIME'] / df['SECONDS_ELAPSED']
    print( "  Per second".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    print( "-- Detailed breakdown of TOTAL_WAIT_TIME --" )
    print_seperator(0)

    # print( "                              %    Total" )
    # print( "                              ---  ---------------------------------------------" )
    # print( "TOTAL_WAIT_TIME               100  0" )
    series = df['TOTAL_WAIT_TIME']
    print( "TOTAL_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    print( "I/O wait time" )
    # print( "  POOL_READ_TIME              0    0" )
    series = df['POOL_READ_TIME']
    print( "  POOL_READ_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['POOL_READ_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "    Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "  POOL_WRITE_TIME             0    0" )
    series = df['POOL_WRITE_TIME']
    print( "  POOL_WRITE_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['POOL_WRITE_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "    Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "  DIRECT_READ_TIME            0    4" )
    series = df['DIRECT_READ_TIME']
    print( "  DIRECT_READ_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['DIRECT_READ_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "    Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "  DIRECT_WRITE_TIME           0    0" )
    series = df['DIRECT_WRITE_TIME']
    print( "  DIRECT_WRITE_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['DIRECT_WRITE_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "    Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "  LOG_DISK_WAIT_TIME          0    0" )
    series = df['LOG_DISK_WAIT_TIME']
    print( "  LOG_DISK_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['LOG_DISK_WAIT_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "    Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "LOCK_WAIT_TIME                0    0" )
    series = df['LOCK_WAIT_TIME']
    print( "LOCK_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['LOCK_WAIT_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "  Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "AGENT_WAIT_TIME               0    0" )
    series = df['AGENT_WAIT_TIME']
    print( "AGENT_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['AGENT_WAIT_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "  Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    print( "Network and FCM" )
    # print( "  TCPIP_SEND_WAIT_TIME        0    0" )
    series = df['TCPIP_SEND_WAIT_TIME']
    print( "  TCPIP_SEND_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['TCPIP_SEND_WAIT_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "    Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "  TCPIP_RECV_WAIT_TIME        0    0" )
    series = df['TCPIP_RECV_WAIT_TIME']
    print( "  TCPIP_RECV_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['TCPIP_RECV_WAIT_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "    Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "  IPC_SEND_WAIT_TIME          0    0" )
    series = df['IPC_SEND_WAIT_TIME']
    print( "  IPC_SEND_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['IPC_SEND_WAIT_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "    Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "  IPC_RECV_WAIT_TIME          0    0" )
    series = df['IPC_RECV_WAIT_TIME']
    print( "  IPC_RECV_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['IPC_RECV_WAIT_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "    Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "  FCM_SEND_WAIT_TIME          0    0" )
    series = df['FCM_SEND_WAIT_TIME']
    print( "  FCM_SEND_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['FCM_SEND_WAIT_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "    Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "  FCM_RECV_WAIT_TIME          0    0" )
    series = df['FCM_RECV_WAIT_TIME']
    print( "  FCM_RECV_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['FCM_RECV_WAIT_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "    Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "WLM_QUEUE_TIME_TOTAL          0    0" )
    series = df['WLM_QUEUE_TIME_TOTAL']
    print( "WLM_QUEUE_TIME_TOTAL".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['WLM_QUEUE_TIME_TOTAL'] / df['TOTAL_WAIT_TIME'] )
    print( "  Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "CF_WAIT_TIME                  0    0" )
    series = df['CF_WAIT_TIME']
    print( "CF_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['CF_WAIT_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "  Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "RECLAIM_WAIT_TIME             0    0" )
    series = df['RECLAIM_WAIT_TIME']
    print( "RECLAIM_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['RECLAIM_WAIT_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "  Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "SMP_RECLAIM_WAIT_TIME         0    0" )
    series = df['SPACEMAPPAGE_RECLAIM_WAIT_TIME']
    print( "SMP_RECLAIM_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['SPACEMAPPAGE_RECLAIM_WAIT_TIME'] / df['TOTAL_WAIT_TIME'] )
    print( "  Percent of total wait time".ljust(label_chars) + series_to_str(series, suffix='%') )
    print_seperator(0)

    print( "Component times" )
    print_seperator(1)

    print( "-- Detailed breakdown of processing time --" )
    print_seperator(0)

    # print( "                                    %                 Total" )
    # print( "                                    ----------------  --------------------------" )
    # print( "Total processing                    100               0" )
    series = df['TOTAL_RQST_TIME'] - df['TOTAL_WAIT_TIME']
    print( "Total processing".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    print( "Section execution" )
    # print( "  TOTAL_SECTION_PROC_TIME           0                 0" )
    series = df['TOTAL_SECTION_PROC_TIME']
    print( "  TOTAL_SECTION_PROC_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['TOTAL_SECTION_PROC_TIME'] / (df['TOTAL_RQST_TIME'] - df['TOTAL_WAIT_TIME'] ) )
    print( "    Percent of total proc time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "    TOTAL_SECTION_SORT_PROC_TIME    0                 0" )
    series = df['TOTAL_SECTION_SORT_PROC_TIME']
    print( "  TOTAL_SECTION_SORT_PROC_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['TOTAL_SECTION_SORT_PROC_TIME'] / (df['TOTAL_RQST_TIME'] - df['TOTAL_WAIT_TIME'] ) )
    print( "    Percent of total proc time".ljust(label_chars) + series_to_str(series, suffix='%') )
    print( "Compile" )
    # print( "  TOTAL_COMPILE_PROC_TIME           0                 0" )
    series = df['TOTAL_COMPILE_PROC_TIME']
    print( "  TOTAL_COMPILE_PROC_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['TOTAL_COMPILE_PROC_TIME'] / (df['TOTAL_RQST_TIME'] - df['TOTAL_WAIT_TIME'] ) )
    print( "    Percent of total proc time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "  TOTAL_IMPLICIT_COMPILE_PROC_TIME  0                 0" )
    series = df['TOTAL_IMPLICIT_COMPILE_PROC_TIME']
    print( "  TOTAL_IMPLICIT_COMPILE_PROC_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['TOTAL_IMPLICIT_COMPILE_PROC_TIME'] / (df['TOTAL_RQST_TIME'] - df['TOTAL_WAIT_TIME'] ) )
    print( "    Percent of total proc time".ljust(label_chars) + series_to_str(series, suffix='%') )
    print( "Transaction end processing" )
    # print( "  TOTAL_COMMIT_PROC_TIME            0                 0" )
    series = df['TOTAL_COMMIT_PROC_TIME']
    print( "  TOTAL_COMMIT_PROC_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['TOTAL_COMMIT_PROC_TIME'] / (df['TOTAL_RQST_TIME'] - df['TOTAL_WAIT_TIME'] ) )
    print( "    Percent of total proc time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "  TOTAL_ROLLBACK_PROC_TIME          0                 0" )
    series = df['TOTAL_ROLLBACK_PROC_TIME']
    print( "  TOTAL_ROLLBACK_PROC_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['TOTAL_ROLLBACK_PROC_TIME'] / (df['TOTAL_RQST_TIME'] - df['TOTAL_WAIT_TIME'] ) )
    print( "    Percent of total proc time".ljust(label_chars) + series_to_str(series, suffix='%') )
    print( "Utilities" )
    # print( "  TOTAL_RUNSTATS_PROC_TIME          0                 0" )
    series = df['TOTAL_RUNSTATS_PROC_TIME']
    print( "  TOTAL_RUNSTATS_PROC_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['TOTAL_RUNSTATS_PROC_TIME'] / (df['TOTAL_RQST_TIME'] - df['TOTAL_WAIT_TIME'] ) )
    print( "    Percent of total proc time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "  TOTAL_REORGS_PROC_TIME            0                 0" )
    series = df['TOTAL_REORG_PROC_TIME']
    print( "  TOTAL_REORGS_PROC_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['TOTAL_REORG_PROC_TIME'] / (df['TOTAL_RQST_TIME'] - df['TOTAL_WAIT_TIME'] ) )
    print( "    Percent of total proc time".ljust(label_chars) + series_to_str(series, suffix='%') )
    # print( "  TOTAL_LOAD_PROC_TIME              0                 0" )
    series = df['TOTAL_LOAD_PROC_TIME']
    print( "  TOTAL_LOAD_PROC_TIME".ljust(label_chars) + series_to_str(series) )
    series = 100 * ( df['TOTAL_LOAD_PROC_TIME'] / (df['TOTAL_RQST_TIME'] - df['TOTAL_WAIT_TIME'] ) )
    print( "    Percent of total proc time".ljust(label_chars) + series_to_str(series, suffix='%') )
    print_seperator(0)

    print( "Buffer pool" )
    print_seperator(1)

    print( "Buffer pool hit ratios" )
    print_seperator(0)

    # print( "Type             Ratio            Formula" )
    # print( "---------------  ---------------  ----------------------------------------------" )
    # print( "Data             96               (1-(1+0-0)/(29+0))" )
    series = ( 1  - ( ( df['POOL_DATA_P_READS'] + df['POOL_TEMP_DATA_P_READS'] - df['POOL_ASYNC_DATA_READS'] ) / ( df['POOL_DATA_L_READS'] + df['POOL_TEMP_DATA_L_READS'] ) ) ) * 100
    print( "Data hit ratio".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_DATA_P_READS']
    print( "  POOL_DATA_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_DATA_P_READS']
    print( "  POOL_TEMP_DATA_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_DATA_READS']
    print( "  POOL_ASYNC_DATA_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_DATA_L_READS']
    print( "  POOL_DATA_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_DATA_L_READS']
    print( "  POOL_TEMP_DATA_L_READS".ljust(label_chars) + series_to_str(series) )
    print( "  Formula".ljust(label_chars) + " ( 1 - ( POOL_DATA_P_READS + POOL_TEMP_DATA_P_READS - POOL_ASYNC_DATA_READS) / ( POOL_DATA_L_READS + POOL_TEMP_DATA_L_READS ) " )
    # print( "Index            100              (1-(0+0-0)/(24+0))" )
    series = ( 1  - ( ( df['POOL_INDEX_P_READS'] + df['POOL_TEMP_INDEX_P_READS'] - df['POOL_ASYNC_INDEX_READS'] ) / ( df['POOL_INDEX_L_READS'] + df['POOL_TEMP_INDEX_L_READS'] ) ) ) * 100
    print( "Index hit ratio".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_INDEX_P_READS']
    print( "  POOL_INDEX_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_INDEX_P_READS']
    print( "  POOL_TEMP_INDEX_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_INDEX_READS']
    print( "  POOL_ASYNC_INDEX_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_INDEX_L_READS']
    print( "  POOL_INDEX_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_INDEX_L_READS']
    print( "  POOL_TEMP_INDEX_L_READS".ljust(label_chars) + series_to_str(series) )
    print( "  Formula".ljust(label_chars) + " ( 1 - ( POOL_INDEX_P_READS + POOL_TEMP_INDEX_P_READS - POOL_ASYNC_INDEX_READS) / ( POOL_INDEX_L_READS + POOL_TEMP_INDEX_L_READS ) " )
    # print( "XDA              0                (1-(0+0-0)/(0+0))" )
    series = ( 1  - ( ( df['POOL_XDA_P_READS'] + df['POOL_TEMP_XDA_P_READS'] - df['POOL_ASYNC_XDA_READS'] ) / ( df['POOL_XDA_L_READS'] + df['POOL_TEMP_XDA_L_READS'] ) ) ) * 100
    print( "XDA hit ratio".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_XDA_P_READS']
    print( "  POOL_XDA_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_XDA_P_READS']
    print( "  POOL_TEMP_XDA_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_XDA_READS']
    print( "  POOL_ASYNC_XDA_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_XDA_L_READS']
    print( "  POOL_XDA_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_XDA_L_READS']
    print( "  POOL_TEMP_XDA_L_READS".ljust(label_chars) + series_to_str(series) )
    print( "  Formula".ljust(label_chars) + " ( 1 - ( POOL_XDA_P_READS + POOL_TEMP_XDA_P_READS - POOL_ASYNC_XDA_READS) / ( POOL_XDA_L_READS + POOL_TEMP_XDA_L_READS ) " )
    # print( "COL              0                (1-(0+0-0)/(0+0))" )
    series = ( 1  - ( ( df['POOL_COL_P_READS'] + df['POOL_TEMP_COL_P_READS'] - df['POOL_ASYNC_COL_READS'] ) / ( df['POOL_COL_L_READS'] + df['POOL_TEMP_COL_L_READS'] ) ) ) * 100
    print( "COL hit ratio".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_COL_P_READS']
    print( "  POOL_COL_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_COL_P_READS']
    print( "  POOL_TEMP_COL_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_COL_READS']
    print( "  POOL_ASYNC_COL_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_COL_L_READS']
    print( "  POOL_COL_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_COL_L_READS']
    print( "  POOL_TEMP_COL_L_READS".ljust(label_chars) + series_to_str(series) )
    print( "  Formula".ljust(label_chars) + " ( 1 - ( POOL_COL_P_READS + POOL_TEMP_COL_P_READS - POOL_ASYNC_COL_READS) / ( POOL_COL_L_READS + POOL_TEMP_COL_L_READS ) " )
    # print( "LBP Data         96               (28-0)/(29+0)" )
    series = ( ( df['POOL_DATA_LBP_PAGES_FOUND'] - df['POOL_ASYNC_DATA_LBP_PAGES_FOUND'] ) / ( df['POOL_DATA_L_READS'] + df['POOL_DATA_L_READS'] ) ) * 100
    print( "LBP Data hit ratio".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_DATA_LBP_PAGES_FOUND']
    print( "  POOL_DATA_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_DATA_LBP_PAGES_FOUND']
    print( "  POOL_ASYNC_DATA_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_DATA_L_READS']
    print( "  POOL_DATA_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_DATA_L_READS']
    print( "  POOL_TEMP_DATA_L_READS".ljust(label_chars) + series_to_str(series) )
    print( "  Formula".ljust(label_chars) + " ( POOL_DATA_LBP_PAGES_FOUND - POOL_ASYNC_DATA_LBP_PAGES_FOUND ) / ( POOL_DATA_L_READS + POOL_DATA_L_READS ) " )
    # print( "LBP Index        0                (0-0)/(24+0)" )
    series = ( ( df['POOL_INDEX_LBP_PAGES_FOUND'] - df['POOL_ASYNC_INDEX_LBP_PAGES_FOUND'] ) / ( df['POOL_INDEX_L_READS'] + df['POOL_INDEX_L_READS'] ) ) * 100
    print( "LBP Index hit ratio".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_INDEX_LBP_PAGES_FOUND']
    print( "  POOL_INDEX_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_INDEX_LBP_PAGES_FOUND']
    print( "  POOL_ASYNC_INDEX_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_INDEX_L_READS']
    print( "  POOL_INDEX_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_INDEX_L_READS']
    print( "  POOL_TEMP_INDEX_L_READS".ljust(label_chars) + series_to_str(series) )
    print( "  Formula".ljust(label_chars) + " ( POOL_INDEX_LBP_PAGES_FOUND - POOL_ASYNC_INDEX_LBP_PAGES_FOUND ) / ( POOL_INDEX_L_READS + POOL_INDEX_L_READS ) " )
    # print( "LBP XDA          0                (0-0)/(0+0)" )
    series = ( ( df['POOL_XDA_LBP_PAGES_FOUND'] - df['POOL_ASYNC_XDA_LBP_PAGES_FOUND'] ) / ( df['POOL_XDA_L_READS'] + df['POOL_XDA_L_READS'] ) ) * 100
    print( "LBP XDA hit ratio".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_XDA_LBP_PAGES_FOUND']
    print( "  POOL_XDA_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_XDA_LBP_PAGES_FOUND']
    print( "  POOL_ASYNC_XDA_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_XDA_L_READS']
    print( "  POOL_XDA_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_XDA_L_READS']
    print( "  POOL_TEMP_XDA_L_READS".ljust(label_chars) + series_to_str(series) )
    print( "  Formula".ljust(label_chars) + " ( POOL_XDA_LBP_PAGES_FOUND - POOL_ASYNC_XDA_LBP_PAGES_FOUND ) / ( POOL_XDA_L_READS + POOL_XDA_L_READS ) " )
    # print( "LBP COL          0                (0-0)/(0+0)" )
    series = ( ( df['POOL_COL_LBP_PAGES_FOUND'] - df['POOL_ASYNC_COL_LBP_PAGES_FOUND'] ) / ( df['POOL_COL_L_READS'] + df['POOL_COL_L_READS'] ) ) * 100
    print( "LBP COL hit ratio".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_COL_LBP_PAGES_FOUND']
    print( "  POOL_COL_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_COL_LBP_PAGES_FOUND']
    print( "  POOL_ASYNC_COL_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_COL_L_READS']
    print( "  POOL_COL_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_COL_L_READS']
    print( "  POOL_TEMP_COL_L_READS".ljust(label_chars) + series_to_str(series) )
    print( "  Formula".ljust(label_chars) + " ( POOL_COL_LBP_PAGES_FOUND - POOL_ASYNC_COL_LBP_PAGES_FOUND ) / ( POOL_COL_L_READS + POOL_COL_L_READS ) " )
    # print( "GBP Data         0                (0 - 0)/0" )s
    series = ( ( df['POOL_DATA_GBP_L_READS'] - df['POOL_DATA_GBP_P_READS'] ) / df['POOL_DATA_GBP_L_READS'] ) * 100
    print( "GBP Data hit ratio".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_DATA_GBP_L_READS']
    print( "  POOL_DATA_GBP_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_DATA_GBP_P_READS']
    print( "  POOL_DATA_GBP_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_DATA_GBP_L_READS']
    print( "  POOL_DATA_GBP_L_READS".ljust(label_chars) + series_to_str(series) )
    print( "  Formula".ljust(label_chars) + " ( POOL_DATA_GBP_L_READS - POOL_DATA_GBP_P_READS ) / POOL_DATA_GBP_L_READS " )
    # print( "GBP Index        0                (0 - 0)/0" )
    series = ( ( df['POOL_INDEX_GBP_L_READS'] - df['POOL_INDEX_GBP_P_READS'] ) / df['POOL_INDEX_GBP_L_READS'] ) * 100
    print( "GBP Index hit ratio".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_INDEX_GBP_L_READS']
    print( "  POOL_INDEX_GBP_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_INDEX_GBP_P_READS']
    print( "  POOL_INDEX_GBP_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_INDEX_GBP_L_READS']
    print( "  POOL_INDEX_GBP_L_READS".ljust(label_chars) + series_to_str(series) )
    print( "  Formula".ljust(label_chars) + " ( POOL_INDEX_GBP_L_READS - POOL_INDEX_GBP_P_READS ) / POOL_INDEX_GBP_L_READS " )
    # print( "GBP XDA          0                (0 - 0)/0" )
    series = ( ( df['POOL_XDA_GBP_L_READS'] - df['POOL_XDA_GBP_P_READS'] ) / df['POOL_XDA_GBP_L_READS'] ) * 100
    print( "GBP XDA hit ratio".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_XDA_GBP_L_READS']
    print( "  POOL_XDA_GBP_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_XDA_GBP_P_READS']
    print( "  POOL_XDA_GBP_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_XDA_GBP_L_READS']
    print( "  POOL_XDA_GBP_L_READS".ljust(label_chars) + series_to_str(series) )
    print( "  Formula".ljust(label_chars) + " ( POOL_XDA_GBP_L_READS - POOL_XDA_GBP_P_READS ) / POOL_XDA_GBP_L_READS " )
    # print( "GBP COL          0                (0 - 0)/0" )
    series = ( ( df['POOL_COL_GBP_L_READS'] - df['POOL_COL_GBP_P_READS'] ) / df['POOL_COL_GBP_L_READS'] ) * 100
    print( "GBP COL hit ratio".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_COL_GBP_L_READS']
    print( "  POOL_COL_GBP_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_COL_GBP_P_READS']
    print( "  POOL_COL_GBP_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_COL_GBP_L_READS']
    print( "  POOL_COL_GBP_L_READS".ljust(label_chars) + series_to_str(series) )
    print( "  Formula".ljust(label_chars) + " ( POOL_COL_GBP_L_READS - POOL_COL_GBP_P_READS ) / POOL_COL_GBP_L_READS " )
    print_seperator(0)

    print( "I/O" )
    print_seperator(1)

    print( "Buffer pool reads" )
    series = df['POOL_DATA_L_READS']
    print( "  POOL_DATA_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_DATA_L_READS']
    print( "  POOL_TEMP_DATA_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_DATA_P_READS']
    print( "  POOL_DATA_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_DATA_P_READS']
    print( "  POOL_TEMP_DATA_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_DATA_READS']
    print( "  POOL_ASYNC_DATA_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_INDEX_L_READS']
    print( "  POOL_INDEX_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_INDEX_L_READS']
    print( "  POOL_TEMP_INDEX_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_INDEX_P_READS']
    print( "  POOL_INDEX_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_INDEX_P_READS']
    print( "  POOL_TEMP_INDEX_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_INDEX_READS']
    print( "  POOL_ASYNC_INDEX_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_XDA_L_READS']
    print( "  POOL_XDA_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_XDA_L_READS']
    print( "  POOL_TEMP_XDA_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_XDA_P_READS']
    print( "  POOL_XDA_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_XDA_P_READS']
    print( "  POOL_TEMP_XDA_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_XDA_READS']
    print( "  POOL_ASYNC_XDA_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_COL_L_READS']
    print( "  POOL_COL_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_COL_L_READS']
    print( "  POOL_TEMP_COL_L_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_COL_P_READS']
    print( "  POOL_COL_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_TEMP_COL_P_READS']
    print( "  POOL_TEMP_COL_P_READS".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_COL_READS']
    print( "  POOL_ASYNC_COL_READS".ljust(label_chars) + series_to_str(series) )
    print( "Buffer pool pages found" )
    series = df['POOL_DATA_LBP_PAGES_FOUND']
    print( "  POOL_DATA_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_DATA_LBP_PAGES_FOUND']
    print( "  POOL_ASYNC_DATA_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_INDEX_LBP_PAGES_FOUND']
    print( "  POOL_INDEX_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_INDEX_LBP_PAGES_FOUND']
    print( "  POOL_ASYNC_INDEX_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_XDA_LBP_PAGES_FOUND']
    print( "  POOL_XDA_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_XDA_LBP_PAGES_FOUND']
    print( "  POOL_ASYNC_XDA_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_COL_LBP_PAGES_FOUND']
    print( "  POOL_COL_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_ASYNC_COL_LBP_PAGES_FOUND']
    print( "  POOL_ASYNC_COL_LBP_PAGES_FOUND".ljust(label_chars) + series_to_str(series) )
    print( "Buffer pool writes" )
    series = df['POOL_DATA_WRITES']
    print( "  POOL_DATA_WRITES".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_XDA_WRITES']
    print( "  POOL_XDA_WRITES".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_INDEX_WRITES']
    print( "  POOL_INDEX_WRITES".ljust(label_chars) + series_to_str(series) )
    series = df['POOL_COL_WRITES']
    print( "  POOL_COL_WRITES".ljust(label_chars) + series_to_str(series) )
    print( "Direct I/O" )
    series = df['DIRECT_READS']
    print( "  DIRECT_READS".ljust(label_chars) + series_to_str(series) )
    series = df['DIRECT_READ_REQS']
    print( "  DIRECT_READ_REQS".ljust(label_chars) + series_to_str(series) )
    series = df['DIRECT_WRITES']
    print( "  DIRECT_WRITES".ljust(label_chars) + series_to_str(series) )
    series = df['DIRECT_WRITE_REQS']
    print( "  DIRECT_WRITE_REQS".ljust(label_chars) + series_to_str(series) )
    print( "Log I/O" )
    series = df['LOG_DISK_WAITS_TOTAL']
    print( "  LOG_DISK_WAITS_TOTAL".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    print( "Locking" )
    print_seperator(1)

    # print( "                        Per activity                    Total" )
    # print( "                        ------------------------------  ----------------------  " )
    # print( "LOCK_WAIT_TIME          0                               0" )
    series = df['LOCK_WAIT_TIME']
    print( "LOCK_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
    series = df['LOCK_WAIT_TIME'] / df['ACT_COMPLETED_TOTAL']
    print( "  Per activity".ljust(label_chars) + series_to_str(series) )
    # print( "LOCK_WAITS              0                               0" )
    series = df['LOCK_WAITS']
    print( "LOCK_WAITS".ljust(label_chars) + series_to_str(series) )
    series = ( df['LOCK_WAITS'] / df['ACT_COMPLETED_TOTAL'] ) * 100
    print( "  Per activity".ljust(label_chars) + series_to_str(series) )
    # print( "LOCK_TIMEOUTS           0                               0" )
    series = df['LOCK_TIMEOUTS']
    print( "LOCK_TIMEOUTS".ljust(label_chars) + series_to_str(series) )
    series = ( df['LOCK_TIMEOUTS'] / df['ACT_COMPLETED_TOTAL'] ) * 100
    print( "  Per activity".ljust(label_chars) + series_to_str(series) )
    # print( "DEADLOCKS               0                               0" )
    series = df['DEADLOCKS']
    print( "DEADLOCKS".ljust(label_chars) + series_to_str(series) )
    series = ( df['DEADLOCKS'] / df['ACT_COMPLETED_TOTAL'] ) * 100
    print( "  Per activity".ljust(label_chars) + series_to_str(series) )
    # print( "LOCK_ESCALS             0                               0" )
    series = df['LOCK_ESCALS']
    print( "LOCK_ESCALS".ljust(label_chars) + series_to_str(series) )
    series = ( df['LOCK_ESCALS'] / df['ACT_COMPLETED_TOTAL'] ) * 100
    print( "  Per activity".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    print( "Routines" )
    print_seperator(1)

    # print( "                              Per activity              Total" )
    # print( "                              ------------------------  ------------------------" )
    # print( "TOTAL_ROUTINE_INVOCATIONS     0                         0" )
    series = df['TOTAL_ROUTINE_INVOCATIONS']
    print( "TOTAL_ROUTINE_INVOCATIONS".ljust(label_chars) + series_to_str(series) )
    series = df['TOTAL_ROUTINE_INVOCATIONS'] / df['ACT_COMPLETED_TOTAL']
    print( "  Per activity".ljust(label_chars) + series_to_str(series) )
    # print( "TOTAL_ROUTINE_TIME            0                         0" )
    series = df['TOTAL_ROUTINE_TIME']
    print( "TOTAL_ROUTINE_TIME".ljust(label_chars) + series_to_str(series) )
    series = df['TOTAL_ROUTINE_TIME'] / df['ACT_COMPLETED_TOTAL']
    print( "  Per activity".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    series = df['TOTAL_ROUTINE_TIME'] / df['TOTAL_ROUTINE_INVOCATIONS']
    print( "TOTAL_ROUTINE_TIME per invocation".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    print( "Sort" )
    print_seperator(1)

    series = df['TOTAL_SORTS']
    print( "TOTAL_SORTS".ljust(label_chars) + series_to_str(series) )
    series = df['SORT_OVERFLOWS']
    print( "SORT_OVERFLOWS".ljust(label_chars) + series_to_str(series) )
    series = df['POST_THRESHOLD_SORTS']
    print( "POST_THRESHOLD_SORTS".ljust(label_chars) + series_to_str(series) )
    series = df['POST_SHRTHRESHOLD_SORTS']
    print( "POST_SHRTHRESHOLD_SORTS".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    print( "Network" )
    print_seperator(1)

    print( "Communications with remote clients" )
    # print( "TCPIP_SEND_VOLUME per send          = 0          (0/0)" )
    series = df['TCPIP_SEND_VOLUME'] / df['TCPIP_SENDS_TOTAL']
    print( "TCPIP_SEND_VOLUME per send".ljust(label_chars) + series_to_str(series) )
    series = df['TCPIP_SEND_VOLUME']
    print( "  TCPIP_SEND_VOLUME".ljust(label_chars) + series_to_str(series) )
    series = df['TCPIP_SENDS_TOTAL']
    print( "  TCPIP_SENDS_TOTAL".ljust(label_chars) + series_to_str(series) )
    # print( "TCPIP_RECV_VOLUME per receive       = 0          (0/0)" )
    series = df['TCPIP_RECV_VOLUME'] / df['TCPIP_RECVS_TOTAL']
    print( "TCPIP_RECV_VOLUME per send".ljust(label_chars) + series_to_str(series) )
    series = df['TCPIP_RECV_VOLUME']
    print( "  TCPIP_RECV_VOLUME".ljust(label_chars) + series_to_str(series) )
    series = df['TCPIP_RECVS_TOTAL']
    print( "  TCPIP_RECVS_TOTAL".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    print( "Communications with local clients" )
    # print( "IPC_SEND_VOLUME per send            = 0          (0/0)" )
    series = df['IPC_SEND_VOLUME'] / df['IPC_SENDS_TOTAL']
    print( "IPC_SEND_VOLUME per send".ljust(label_chars) + series_to_str(series) )
    series = df['IPC_SEND_VOLUME']
    print( "  IPC_SEND_VOLUME".ljust(label_chars) + series_to_str(series) )
    series = df['IPC_SENDS_TOTAL']
    print( "  IPC_SENDS_TOTAL".ljust(label_chars) + series_to_str(series) )
    # print( "IPC_RECV_VOLUME per receive         = 0          (0/0)" )
    series = df['IPC_RECV_VOLUME'] / df['IPC_RECVS_TOTAL']
    print( "IPC_RECV_VOLUME per send".ljust(label_chars) + series_to_str(series) )
    series = df['IPC_RECV_VOLUME']
    print( "  IPC_RECV_VOLUME".ljust(label_chars) + series_to_str(series) )
    series = df['IPC_RECVS_TOTAL']
    print( "  IPC_RECVS_TOTAL".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    print( "Fast communications manager" )
    # print( "FCM_SEND_VOLUME per send            = 0          (0/0)" )
    series = df['FCM_SEND_VOLUME'] / df['FCM_SENDS_TOTAL']
    print( "FCM_SEND_VOLUME per send".ljust(label_chars) + series_to_str(series) )
    series = df['FCM_SEND_VOLUME']
    print( "  FCM_SEND_VOLUME".ljust(label_chars) + series_to_str(series) )
    series = df['FCM_SENDS_TOTAL']
    print( "  FCM_SENDS_TOTAL".ljust(label_chars) + series_to_str(series) )
    # print( "FCM_RECV_VOLUME per receive         = 0          (0/0)" )
    series = df['FCM_RECV_VOLUME'] / df['FCM_RECVS_TOTAL']
    print( "FCM_RECV_VOLUME per send".ljust(label_chars) + series_to_str(series) )
    series = df['FCM_RECV_VOLUME']
    print( "  FCM_RECV_VOLUME".ljust(label_chars) + series_to_str(series) )
    series = df['FCM_RECVS_TOTAL']
    print( "  FCM_RECVS_TOTAL".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    print( "Other" )
    print_seperator(1)

    print( "Compilation" )
    series = df['TOTAL_COMPILATIONS']
    print( "  TOTAL_COMPILATIONS".ljust(label_chars) + series_to_str(series) )
    series = df['PKG_CACHE_INSERTS']
    print( "  PKG_CACHE_INSERTS".ljust(label_chars) + series_to_str(series) )
    series = df['PKG_CACHE_LOOKUPS']
    print( "  PKG_CACHE_LOOKUPS".ljust(label_chars) + series_to_str(series) )
    print( "Catalog cache" )
    series = df['CAT_CACHE_INSERTS']
    print( "  CAT_CACHE_INSERTS".ljust(label_chars) + series_to_str(series) )
    series = df['CAT_CACHE_LOOKUPS']
    print( "  CAT_CACHE_LOOKUPS".ljust(label_chars) + series_to_str(series) )
    print( "Transaction processing" )
    series = df['TOTAL_APP_COMMITS']
    print( "  TOTAL_APP_COMMITS".ljust(label_chars) + series_to_str(series) )
    series = df['INT_COMMITS']
    print( "  INT_COMMITS".ljust(label_chars) + series_to_str(series) )
    series = df['TOTAL_APP_ROLLBACKS']
    print( "  TOTAL_APP_ROLLBACKS".ljust(label_chars) + series_to_str(series) )
    series = df['INT_ROLLBACKS']
    print( "  INT_ROLLBACKS".ljust(label_chars) + series_to_str(series) )
    print( "Log buffer" )
    series = df['NUM_LOG_BUFFER_FULL']
    print( "  NUM_LOG_BUFFER_FULL".ljust(label_chars) + series_to_str(series) )
    print( "Activities aborted/rejected" )
    series = df['ACT_ABORTED_TOTAL']
    print( "  ACT_ABORTED_TOTAL".ljust(label_chars) + series_to_str(series) )
    series = df['ACT_REJECTED_TOTAL']
    print( "  ACT_REJECTED_TOTAL".ljust(label_chars) + series_to_str(series) )
    print( "Workload management controls" )
    series = df['WLM_QUEUE_ASSIGNMENTS_TOTAL']
    print( "  WLM_QUEUE_ASSIGNMENTS_TOTAL".ljust(label_chars) + series_to_str(series) )
    series = df['WLM_QUEUE_TIME_TOTAL']
    print( "  WLM_QUEUE_TIME_TOTAL".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

    print( "DB2 utility operations" )
    print_seperator(1)

    series = df['TOTAL_RUNSTATS']
    print( "  TOTAL_RUNSTATS".ljust(label_chars) + series_to_str(series) )
    series = df['TOTAL_REORGS']
    print( "  TOTAL_REORGS".ljust(label_chars) + series_to_str(series) )
    series = df['TOTAL_LOADS']
    print( "  TOTAL_LOADS".ljust(label_chars) + series_to_str(series) )
    print_seperator(0)

# function to output monreport.dbsummary
def monreport_dbsummary(start_time=pd.Timestamp.min, end_time=pd.Timestamp.max, period=1, members=None):

    # get dataframe
    # collection_time | member | ...
    # 10:10             0
    #                   1
    # 10:20             0
    #                   1
    df = collection_to_df('MON_GET_DATABASE')

    # filter on members
    if members:
        df = df.loc[ df['MEMBER'].isin(members) ]

    # transform collection time column to datetime and filter on collection times
    df['COLLECTION_TIME'] = pd.to_datetime ( df['COLLECTION_TIME'], format=collection_time_format ).dt.floor('S')
    df = df.loc[ ( df['COLLECTION_TIME'] >= start_time ) & ( df['COLLECTION_TIME'] <= end_time ) ]
    collection_times = df.groupby('COLLECTION_TIME').count().index

    # if no collections found
    if len(df) == 0:
        print( "  No collection data available for collection times.")
        print( "  Try increasing scope by adjusting start_time, end_time, and period.")
        return

    # group df on collection time and sum across all members
    df = df.groupby('COLLECTION_TIME').sum()

    # fill in missing collections by reindexing
    # all leading values will equal 0
    # all trailing values will equal the values from the last collection
    df = df.reindex(collection_times, fill_value=0, method='ffill').reset_index()

    # diff across collection times
    # the first value will be diffed from 0 so it will equal itself
    # the last value will be diffed even though it doesn't make it to end of the interval
    df = df.diff(periods=period)[period::period]

    # create column for collection time diff in seconds
    df = df.assign(SECONDS_ELAPSED=df['COLLECTION_TIME'].dt.total_seconds())

    # print header
    print_header("MONREPORT.DBSUMMARY", collection_times, period, diff=True, outliers=True)

    print_seperator(2)

    # print common req metrics
    print_common_req_metrics(df)

    print_seperator(2)

# function to output monreport.connection
def monreport_connection(start_time=pd.Timestamp.min, end_time=pd.Timestamp.max, period=1, members=None, application_handles=None):

    # get dataframe
    # collection_time | application_handle | member | ...
    # 10:10             100                  1
    #                                        2
    #                   200                  1
    #                                        2
    # 10:20             100                  1
    #                                        2
    #                   200                  1
    #                                        2
    df = collection_to_df('MON_GET_CONNECTION')
    df['POOL_ASYNC_DATA_LBP_PAGES_FOUND'] = 0
    df['POOL_ASYNC_INDEX_LBP_PAGES_FOUND'] = 0
    df['POOL_ASYNC_XDA_LBP_PAGES_FOUND'] = 0
    df['POOL_ASYNC_COL_LBP_PAGES_FOUND'] = 0
    df['POOL_ASYNC_DATA_READS'] = 0
    df['POOL_ASYNC_INDEX_READS'] = 0
    df['POOL_ASYNC_XDA_READS'] = 0
    df['POOL_ASYNC_COL_READS'] = 0

    # filter on members
    if members:
        df = df.loc[ df['MEMBER'].isin(members) ]

    # filter on application handles
    if application_handles:
        df = df.loc[ df['APPLICATION_HANDLE'].isin(application_handles) ]

    # transform collection time column to datetime and filter on collection times
    df['COLLECTION_TIME'] = pd.to_datetime ( df['COLLECTION_TIME'], format=collection_time_format ).dt.floor('S')
    df = df.loc[ ( df['COLLECTION_TIME'] >= start_time ) & ( df['COLLECTION_TIME'] <= end_time ) ]
    collection_times = df.groupby('COLLECTION_TIME').count().index

    # if no collections found
    if len(df) == 0:
        print( "  No collection data available for collection times.")
        print( "  Try increasing scope by adjusting start_time, end_time, and period.")
        return

    # split df into multiple dfs based on connection
    dfs_by_conn = {}
    for conn, df in df.groupby(['APPLICATION_HANDLE', 'APPLICATION_NAME', 'APPLICATION_ID']):

        # group df on collection time and sum across all members
        df = df.groupby('COLLECTION_TIME').sum()

        # fill in missing collections by reindexing
        # all leading values will equal 0
        # all trailing values will equal the values from the last collection
        df = df.reindex(collection_times, fill_value=0, method='ffill').reset_index()

        # diff across collection times
        # the first value will be diffed from 0 so it will equal itself
        # the last value will be diffed even though it doesn't make it to end of the interval
        df = df.diff(periods=period)[period::period]

        # create column for collection time diff in seconds
        df = df.assign(SECONDS_ELAPSED=df['COLLECTION_TIME'].dt.total_seconds())

        dfs_by_conn[conn] = df

    # warn if too many connections when printing to terminal
    print_details = True
    if len(dfs_by_conn) > 3 and os.fstat(0) == os.fstat(1):
        print( "  There are %s connections." % len(dfs_by_conn))
        print( "  Details will be printed for each connection individually")
        print( "  resulting in a very large output.")
        print( "  You can shorten this by passing in specific application handles.")
        print_seperator(0)

        value = input("    Enter 1 to print summary of connections only or 2 to print everything: ")
        value = str(value)
        if not value.isdigit():
            print( "  Invalid input, exiting.")
            exit()
        elif int(value) == 1:
            print_details = False
        elif int(value) == 2:
            print_details = True
        else:
            print( "  Invalid input, exiting.")
            exit()

    # print header
    print_header("MONREPORT.CONNECTION", collection_times, period, diff=True, outliers=True)

    global label_chars

    print_seperator(2)

    # print summary of connections
    print( "Summary of connections" )
    print_seperator(1)

    for conn, df in dfs_by_conn.items():

        print_seperator(0)

        # print connection details
        print( "Connection details: Handle = %s, Name = %s, ID = %s" % (conn) )
        print_seperator(0)

        # if no collections found
        if len(df) == 0:
            print( "  No collection data available for collection times.")
            print( "  Try increasing scope by adjusting start_time, end_time, and period.")
            continue

        # print connection summary
        series = df['TOTAL_CPU_TIME']
        print( "  TOTAL_CPU_TIME".ljust(label_chars) + series_to_str(series) )
        series = df['TOTAL_ACT_TIME']
        print( "  TOTAL_ACT_TIME".ljust(label_chars) + series_to_str(series) )
        series = df['ACT_COMPLETED_TOTAL']
        print( "  ACT_COMPLETED_TOTAL".ljust(label_chars) + series_to_str(series) )
        series = df['TOTAL_WAIT_TIME']
        print( "  TOTAL_WAIT_TIME".ljust(label_chars) + series_to_str(series) )
        series = df['CLIENT_IDLE_WAIT_TIME']
        print( "  CLIENT_IDLE_WAIT_TIME".ljust(label_chars) + series_to_str(series) )

    print_seperator(2)

    if print_details:

        # print details for each connection
        print( "Details for each connection" )
        print_seperator(1)

        # print common req metrics for connections
        for conn, df in dfs_by_conn.items():

            print_seperator(0)

            # print connection details
            print( "Connection details: Handle = %s, Name = %s, ID = %s" % (conn) )
            print_seperator(1)

            # if no collections found
            if len(df) == 0:
                print( "  No collection data available for collection times.")
                print( "  Try increasing scope by adjusting start_time, end_time, and period.")
                continue

            # print connection common req metrics
            print_common_req_metrics(df)

        print_seperator(2)

# function to output monreport.pkgcache
def monreport_pkgcache(start_time=pd.Timestamp.min, end_time=pd.Timestamp.max, members=None):

    # get dataframe
    # collection_time | member | ... | stmt_text
    # 10:10             0              select * from A
    #                   1
    # 10:20             0
    #                   1
    # 10:10             0              select * from B
    #                   1
    # 10:20             0
    #                   1
    df = collection_to_df('MON_GET_PKG_CACHE_STMT')

    # store a mapping of executable ids and stmt text lob ids in a seperate df
    stmt_text_df = df[['EXECUTABLE_ID', 'STMT_TEXT']]
    stmt_text_df = stmt_text_df.groupby('EXECUTABLE_ID').max()

    # filter on members
    if members:
        df = df.loc[ df['MEMBER'].isin(members) ]

    # transform collection time column to datetime and filter on collection times
    df['COLLECTION_TIME'] = pd.to_datetime ( df['COLLECTION_TIME'], format=collection_time_format ).dt.floor('S')
    df = df.loc[ ( df['COLLECTION_TIME'] >= start_time ) & ( df['COLLECTION_TIME'] <= end_time ) ]
    collection_times = df.groupby('COLLECTION_TIME').count().index

    # if no collections found
    if len(df) == 0:
        print( "  No collection data available for collection times.")
        print( "  Try increasing scope by adjusting start_time and end_time.")
        return

    # group df on statement text then collection time and sum across all members
    df = df.groupby(["EXECUTABLE_ID", "COLLECTION_TIME"]).sum().reset_index()

    # group df on statement text and get the max values across all collection times
    df = df.groupby("EXECUTABLE_ID").max().reset_index()

    # join df to stmt text df
    df = df.join(stmt_text_df, on="EXECUTABLE_ID")

    # print header
    print_header("MONREPORT.PKGCACHE", collection_times)

    # truncate statement text if being outputted to terminal
    if os.fstat(0) == os.fstat(1):
        stmt_text_len = str_chars
    # use full statement text if being outputted to file
    else:
        stmt_text_len = -1

    # print Top 10 statements by TOTAL_CPU_TIME
    temp_df = df.sort_values("TOTAL_CPU_TIME", ascending=False)[:10]
    temp_df["STMT_TEXT"] = temp_df["STMT_TEXT"].apply(get_lob)
    print("Top 10 statements by TOTAL_CPU_TIME")
    print_seperator(1)
    print(temp_df.to_string(columns=["TOTAL_CPU_TIME", "COLLECTION_TIME", "STMT_TEXT"],
        header=["TOTAL_CPU_TIME", "PEAK TIME", "STMT_TEXT"],
        index=False, justify="left", col_space=20, max_colwidth=stmt_text_len))
    print_seperator(0)

    # print Top 10 statements by TOTAL_CPU TIME per exec
    df["TOTAL_CPU_TIME_PER_EXEC"] = df["TOTAL_CPU_TIME"] / df["NUM_EXECUTIONS"]
    temp_df = df.sort_values("TOTAL_CPU_TIME_PER_EXEC", ascending=False)[:10]
    temp_df["STMT_TEXT"] = temp_df["STMT_TEXT"].apply(get_lob)
    print("Top 10 statements by TOTAL_CPU TIME per exec")
    print_seperator(1)
    print(temp_df.to_string(columns=["TOTAL_CPU_TIME_PER_EXEC", "COLLECTION_TIME", "STMT_TEXT"],
        header=["TOTAL_CPU_TIME", "PEAK TIME", "STMT_TEXT"],
        index=False, justify="left", col_space=20, max_colwidth=stmt_text_len))
    print_seperator(0)

    # print Top 10 statements by TOTAL_ACT_WAIT_TIME
    temp_df = df.sort_values("TOTAL_ACT_WAIT_TIME", ascending=False)[:10]
    temp_df["STMT_TEXT"] = temp_df["STMT_TEXT"].apply(get_lob)
    print("Top 10 statements by TOTAL_ACT_WAIT_TIME")
    print_seperator(1)
    print(temp_df.to_string(columns=["TOTAL_ACT_WAIT_TIME", "LOCK_WAIT_TIME", "COLLECTION_TIME", "STMT_TEXT"],
        header=["TOTAL_ACT_WAIT_TIME", "LOCK_WAIT_TIME", "PEAK TIME", "STMT_TEXT"],
        index=False, justify="left", col_space=20, max_colwidth=stmt_text_len))
    print_seperator(0)

    # print Top 10 statements by TOTAL_ACT_WAIT_TIME per exec
    df["TOTAL_ACT_WAIT_TIME_PER_EXEC"] = df["TOTAL_ACT_WAIT_TIME"] / df["NUM_EXECUTIONS"]
    temp_df = df.sort_values("TOTAL_ACT_WAIT_TIME_PER_EXEC", ascending=False)[:10]
    temp_df["STMT_TEXT"] = temp_df["STMT_TEXT"].apply(get_lob)
    print("Top 10 statements by TOTAL_ACT_WAIT_TIME per exec")
    print_seperator(1)
    print(temp_df.to_string(columns=["TOTAL_ACT_WAIT_TIME_PER_EXEC", "LOCK_WAIT_TIME", "COLLECTION_TIME", "STMT_TEXT"],
        header=["TOTAL_ACT_WAIT_TIME", "LOCK_WAIT_TIME", "PEAK TIME", "STMT_TEXT"],
        index=False, justify="left", col_space=20, max_colwidth=stmt_text_len))
    print_seperator(0)

    # print Top 10 statements by ROWS_READ + ROWS_MODIFIED
    df["ROWS_READ_PLUS_ROWS_MODIFIED"] = df["ROWS_READ"] + df["ROWS_MODIFIED"]
    temp_df = df.sort_values("ROWS_READ_PLUS_ROWS_MODIFIED", ascending=False)[:10]
    temp_df["STMT_TEXT"] = temp_df["STMT_TEXT"].apply(get_lob)
    print("Top 10 statements by ROWS_READ + ROWS_MODIFIED")
    print_seperator(1)
    print(temp_df.to_string(columns=["ROWS_READ_PLUS_ROWS_MODIFIED", "COLLECTION_TIME", "STMT_TEXT"],
        header=["ROWS_READ+ROWS_MODIFIED", "PEAK TIME", "STMT_TEXT"],
        index=False, justify="left", col_space=20, max_colwidth=stmt_text_len))
    print_seperator(0)

    # print Top 10 statements by ROWS_READ + ROWS_MODIFIED per exec
    df["ROWS_READ_PLUS_ROWS_MODIFIED_PER_EXEC"] = df["ROWS_READ_PLUS_ROWS_MODIFIED"] / df["NUM_EXECUTIONS"]
    temp_df = df.sort_values("ROWS_READ_PLUS_ROWS_MODIFIED_PER_EXEC", ascending=False)[:10]
    temp_df["STMT_TEXT"] = temp_df["STMT_TEXT"].apply(get_lob)
    print("Top 10 statements by ROWS_READ + ROWS_MODIFIED per exec")
    print_seperator(1)
    print(temp_df.to_string(columns=["ROWS_READ_PLUS_ROWS_MODIFIED_PER_EXEC", "COLLECTION_TIME", "STMT_TEXT"],
        header=["ROWS_READ+ROWS_MODIFIED", "PEAK TIME", "STMT_TEXT"],
        index=False, justify="left", col_space=20, max_colwidth=stmt_text_len))
    print_seperator(0)

    # print Top 10 statements by number of executions
    temp_df = df.sort_values("NUM_EXECUTIONS", ascending=False)[:10]
    temp_df["STMT_TEXT"] = temp_df["STMT_TEXT"].apply(get_lob)
    print("Top 10 statements by number of executions")
    print_seperator(1)
    print(temp_df.to_string(columns=["NUM_EXECUTIONS", "COLLECTION_TIME", "STMT_TEXT"],
        header=["Executions", "PEAK TIME", "STMT_TEXT"],
        index=False, justify="left", col_space=20, max_colwidth=stmt_text_len))
    print_seperator(0)

    # print Top 10 statements by I/O wait time
    df["IO_WAIT_TIME"] = df["POOL_READ_TIME"] + df["POOL_WRITE_TIME"] + df["DIRECT_READ_TIME"] + df["DIRECT_WRITE_TIME"]
    temp_df = df.sort_values("IO_WAIT_TIME", ascending=False)[:10]
    temp_df["STMT_TEXT"] = temp_df["STMT_TEXT"].apply(get_lob)
    print("Top 10 statements by I/O wait time")
    print_seperator(1)
    print(temp_df.to_string(columns=["IO_WAIT_TIME", "COLLECTION_TIME", "STMT_TEXT"],
        header=["I/O wait time", "PEAK TIME", "STMT_TEXT"],
        index=False, justify="left", col_space=20, max_colwidth=stmt_text_len))
    print_seperator(0)

    # print Top 10 statements by I/O wait time per exec
    df["IO_WAIT_TIME_PER_EXEC"] = df["IO_WAIT_TIME"] / df["NUM_EXECUTIONS"]
    temp_df = df.sort_values("IO_WAIT_TIME_PER_EXEC", ascending=False)[:10]
    temp_df["STMT_TEXT"] = temp_df["STMT_TEXT"].apply(get_lob)
    print("Top 10 statements by I/O wait time per exec")
    print_seperator(1)
    print(temp_df.to_string(columns=["IO_WAIT_TIME_PER_EXEC", "COLLECTION_TIME", "STMT_TEXT"],
        header=["I/O wait time", "PEAK TIME", "STMT_TEXT"],
        index=False, justify="left", col_space=20, max_colwidth=stmt_text_len))
    print_seperator(0)

    print_seperator(2)

def main():

    # parse arguments
    description="Generate report similar to MONREPORT.DBSUMMARY"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('path', help='path where collection directories are stored')
    parser.add_argument('-r', '--report', default='dbsummary', choices=['dbsummary', 'connection', 'currentapps', 'currentsql', 'pkgcache', 'lockwait'],
                        help='name of report to be generated')
    parser.add_argument('-st', '--start_time', default=pd.Timestamp.min,
                        help='display collections after this time, format can be (YYYY-mm-dd HH:MM:SS) or copied from a collection (YYYY-mm-dd-HH-MM-SS.ffffff)')
    parser.add_argument('-et', '--end_time', default=pd.Timestamp.max,
                        help='display collections before this time, format can be (YYYY-mm-dd HH:MM:SS) or copied from a collection (YYYY-mm-dd-HH-MM-SS.ffffff)')
    parser.add_argument('-p', '--period', default=1, type=int,
                        help='display collections at a lesser frequency, for example an interval of 3 will show every third collection')
    parser.add_argument('-s', '--stats', action='store_true',
                        help='show min, max, mean, std for each series of values')
    parser.add_argument('-m', '--members', type=int, nargs='+',
                        help='filter certain reports by member')
    parser.add_argument('-ah', '--application_handles', type=int, nargs='+',
                        help='filter certain reports by application handle')

    args = parser.parse_args()

    # change directory to path
    os.chdir( args.path )

    global stats
    stats = args.stats

    # convert start and end times to datetime
    global collection_time_format
    try: # if time format like "YYYY-mm-dd HH:MM"
        args.start_time = pd.to_datetime( args.start_time )
        args.end_time = pd.to_datetime( args.end_time )
    except: # if time format copied from collections
        args.start_time = pd.to_datetime( args.start_time, format=collection_time_format )
        args.end_time = pd.to_datetime( args.end_time, format=collection_time_format )

    # generate report
    if args.report == 'dbsummary':
        monreport_dbsummary(args.start_time, args.end_time, args.period, args.members)
    elif args.report == 'connection':
        monreport_connection(args.start_time, args.end_time, args.period, args.members, args.application_handles)
    elif args.report == 'pkgcache':
        monreport_pkgcache(args.start_time, args.end_time, args.members)
    else:
        print("Incorrect report, run with -h for help")
        exit()

if __name__ == "__main__":
    main()