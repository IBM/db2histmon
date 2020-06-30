################################################################################
# (c) Copyright IBM Corp. 2020 All rights reserved.

# The following sample of source code ("Sample") is owned by International
# Business Machines Corporation or one of its subsidiaries ("IBM") and is
# copyrighted and licensed, not sold. You may use, copy, modify, and
# distribute the Sample in any form without payment to IBM, for the purpose of
# assisting you in the development of your applications.

# The Sample code is provided to you on an "AS IS" basis, without warranty of
# any kind. IBM HEREBY EXPRESSLY DISCLAIMS ALL WARRANTIES, EITHER EXPRESS OR
# IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. Some jurisdictions do
# not allow for the exclusion or limitation of implied warranties, so the above
# limitations or exclusions may not apply to you. IBM shall not be liable for
# any damages you suffer as a result of using, copying, modifying or
# distributing the Sample, even if IBM has been advised of the possibility of
# such damages.
################################################################################


import argparse
import os, sys, stat, datetime
import shutil, subprocess
import json
import ibm_db

# function to execute sql file
def exec_sql_file(conn, path):

    print("        Executing %s ..." % path)

    # read file
    with open(path) as sql_file:
        commands = sql_file.read()
    # split file into seperate commands using @ as a delimiter
    commands = commands.split("@")
    # strip whitespace and remove empty commands
    commands = [command.strip() for command in commands if command.strip()]

    # execute each command
    for command in commands:
        try:
            ibm_db.exec_immediate(conn, command)
        except:
            if "statement is blank or empty" not in ibm_db.stmt_errormsg():
                print("        Failure executing statement: '%s' ..." % command.replace('\n', ' ')[:100])
                print(ibm_db.stmt_errormsg())
                exit()

# function to setup IBMHIST schema and register all table and procedure objects
def setup_IBMHIST(conn, bldrtn_path):

    print("Setting up IBMHIST schema and its objects ...")

    # create and set schema to IBMHIST
    print("    Creating IBMHIST schema ...")
    ibm_db.exec_immediate(conn, "CREATE SCHEMA IBMHIST")
    print("    Setting schema to IBMHIST ...")
    ibm_db.exec_immediate(conn, "SET CURRENT SCHEMA IBMHIST")

    # change directory to ./sql, and keep track of files
    os.chdir("sql")
    orig_files = os.listdir('.')

    # build and register external functions
    print("    Registering external functions ...")

    # copy bldrtn script to sql directory
    print("        Copying bldrtn script from '%s' to sql/ ..." % bldrtn_path )
    assert os.path.exists(bldrtn_path), "bldrtn script does not exist at: %s" % bldrtn_path
    shutil.copyfile(bldrtn_path, "bldrtn.bat") if os.name == 'nt' else shutil.copyfile(bldrtn_path, "bldrtn")
    os.chmod("bldrtn.bat", stat.S_IRWXU) if os.name == 'nt' else os.chmod("bldrtn", stat.S_IRWXU)

    # build external functions
    print("        Building external functions ...")
    subprocess.check_call("bldrtn.bat external", shell=True) if os.name == 'nt' else subprocess.check_call("bldrtn external", shell=True)
    exec_sql_file(conn, "external.sql")

    # register tables
    print("    Registering tables ...")
    exec_sql_file(conn, "tab_config.sql")
    exec_sql_file(conn, "tab_errs.sql")
    exec_sql_file(conn, "tab_tasks.sql")
    exec_sql_file(conn, "tab_dirs.sql")

    # register procedures
    print("    Registering procedures ...")
    exec_sql_file(conn, "proc_collect.sql")
    exec_sql_file(conn, "proc_archive.sql")

    # remove additional files created during setup and change directory back
    print("    Removing additional files created during setup ...")
    additional_files = [ f for f in os.listdir('.') if f not in orig_files ]
    for f in additional_files:
        os.remove(f)
    os.chdir('..')

# function drop old IBMHIST schema and its objects
def drop_IBMHIST(conn):

    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM SYSCAT.SCHEMATA WHERE SCHEMANAME = 'IBMHIST'")
    if ibm_db.fetch_assoc(stmt):

        print("Dropping IBMHIST schema and its objects ...")

        # calling ADMIN_DROP_SCHEMA to drop IBMHIST schema and all its objects
        # errors will be outputted to IBMHIST_ERR_SCHEMA.IBMHIST_ERR_TAB
        sql = "CALL SYSPROC.ADMIN_DROP_SCHEMA ('IBMHIST', NULL, ?, ?)"
        param = "IBMHIST_ERR_SCHEMA", "IBMHIST_ERR_TAB"
        stmt = ibm_db.prepare(conn, sql)
        ibm_db.execute(stmt, param)

        # check if any errors were produced when using ADMIN_DROP_SCHEMA
        # see if IBMHIST_ERR_SCHEMA.IBMHIST_ERR_TAB was created and drop IBMHIST_ERR_SCHEMA, IBMHIST_ERR_TAB
        stmt = ibm_db.exec_immediate(conn, "SELECT * FROM SYSCAT.TABLES WHERE TABSCHEMA = 'IBMHIST_ERR_SCHEMA' AND TABNAME = 'IBMHIST_ERR_TAB'")
        if ibm_db.fetch_assoc(stmt):
            stmt = ibm_db.exec_immediate(conn, "SELECT * FROM IBMHIST_ERR_SCHEMA.IBMHIST_ERR_TAB")
            error = ibm_db.fetch_assoc(stmt)
            print("Error: could not drop schema IBMHIST, error: %s" % error )
            ibm_db.exec_immediate(conn, "DROP TABLE IBMHIST_ERR_SCHEMA.IBMHIST_ERR_TAB")
            ibm_db.exec_immediate(conn, "DROP SCHEMA IBMHIST_ERR_SCHEMA RESTRICT")
            exit()

# function to test arguments and set configurations in IBMHIST.TAB_CONFIG
def config_IBMHIST(conn, coll_path, arch_path, max_size, arch_cmd, arch_ext):

    print("Configuring IBMHIST settings ...")

    # delete from IBMHIST.TAB_CONFIG
    print("    Deleting configurations from IBMHIST.TAB_CONFIG ...")
    ibm_db.exec_immediate(conn, "DELETE FROM IBMHIST.TAB_CONFIG")

    # rename current collection directory to avoid name conflicts
    stmt = ibm_db.exec_immediate(conn, "SELECT PATH FROM IBMHIST.TAB_DIRS WHERE STATUS = 'COLL'")
    while ibm_db.fetch_row(stmt):

        # get orig path
        orig_path = ibm_db.result(stmt, "PATH")

        # get new path by appending current minute and current second
        new_path = orig_path + '_old' + str(datetime.datetime.now().minute) + str(datetime.datetime.now().second)

        # rename
        print("    Renaming collection directory '%s' to '%s' ..." % (orig_path, new_path) )
        shutil.move(orig_path, new_path)

        # update IBMHIST.TAB_DIRS
        ibm_db.exec_immediate(conn, "UPDATE IBMHIST.TAB_DIRS SET PATH = '%s' WHERE PATH = '%s'" % (new_path, orig_path) )

    # add data collection path configuration
    print("    Setting COLL_PATH to '%s' ..." % (coll_path) )
    assert os.path.exists(coll_path), "Data collection path: %s does not exist" % (coll_path)
    stmt, ret_coll_path, retcode = ibm_db.callproc(conn, 'IBMHIST.PATH_READABLE_WRITABLE', (coll_path, 0))
    assert retcode is 0 or retcode is None, "Data collection path: %s does not provide fenced external functions read/write access" % (coll_path)
    ibm_db.exec_immediate(conn, "INSERT INTO IBMHIST.TAB_CONFIG VALUES ( 'COLL_PATH', '%s', 'DIRECTORY PATH OF DATA COLLECTION') " % (coll_path) )

    # add data archival path configuration
    print("    Setting ARCH_PATH to '%s' ..." % (arch_path) )
    assert os.path.exists(arch_path), "Data archival path: %s does not exist" % (arch_path)
    stmt, ret_arch_path, retcode = ibm_db.callproc(conn, 'IBMHIST.PATH_READABLE_WRITABLE', (arch_path, 0))
    assert retcode is 0 or retcode is None, "Data archival path: %s does not provide fenced external functions read/write access" % (arch_path)
    ibm_db.exec_immediate(conn, "INSERT INTO IBMHIST.TAB_CONFIG VALUES ( 'ARCH_PATH', '%s', 'DIRECTORY PATH OF DATA ARCHIVAL') " % (arch_path) )

    # add max size configuration
    print("    Setting MAX_SIZE to '%s' bytes ..." % (max_size) )
    assert str.isdigit(max_size), "Max size: %s is not an integer" % (max_size)
    ibm_db.exec_immediate(conn, "INSERT INTO IBMHIST.TAB_CONFIG VALUES ( 'MAX_SIZE', '%s', 'MAX SIZE IN BYTES OF COLLECTION AND ARCHIVAL') " % (max_size) )

    # add archival command and archival extension
    print("    Setting ARCH_CMD to '%s' and ARCH_EXT to '%s' ..." % (arch_cmd, arch_ext) )
    # test archival functionality by archiving sql folder
    src, dest = "sql", "arch_test" + arch_ext
    arch_cmd_test = arch_cmd.replace("_src_", src).replace("_dest_", dest)
    if os.path.exists(dest):
        os.remove(dest)
    subprocess.check_call(arch_cmd_test, shell=True)
    assert os.path.exists(dest), "Data archival command: %s failed, could not find archival %s " % (arch_cmd, dest)
    os.remove(dest)
    ibm_db.exec_immediate(conn, "INSERT INTO IBMHIST.TAB_CONFIG VALUES ( 'ARCH_CMD', '%s', 'COMMAND USED TO ARCHIVE HOURLY DIRECTORIES') " % arch_cmd )
    ibm_db.exec_immediate(conn, "INSERT INTO IBMHIST.TAB_CONFIG VALUES ( 'ARCH_EXT', '%s', 'EXTENSION OF ARCHIVE HOURLY DIRECTORIES') " % arch_ext )

    # add task_details.json path configuration
    task_details_path = os.path.realpath("task_details.json")
    print("    Setting TASK_DETAILS_PATH to '%s' ..." % (task_details_path) )
    ibm_db.exec_immediate(conn, "INSERT INTO IBMHIST.TAB_CONFIG VALUES ( 'TASK_DETAILS_PATH', '%s', 'LOCATION OF task_details.json FILE') " % task_details_path )

# function to test basic functionality of IBMHIST.PROC_COLLECT and IBMHIST.PROC_ARCHIVE
def test_IBMHIST(conn, database):

    print("Testing IBMHIST functionality ...")

    # test IBMHIST.PROC_COLLECT with a dummy SQL task
    print("    Testing IBMHIST.PROC_COLLECT with a dummy SQL task ...")
    # create dummy SQL task
    ibm_db.exec_immediate(conn, "INSERT INTO IBMHIST.TAB_TASKS VALUES ( 'DUMMY_SQL_TASK', 'SQL', 'SELECT ''DUMMY_DATA'' FROM SYSIBM.SYSDUMMY1', 'DUMMY_HEADER\n')")
    # call IBMHIST.PROC_COLLECT on dummy SQL task
    ibm_db.exec_immediate(conn, "CALL IBMHIST.PROC_COLLECT('%s', 'DUMMY_SQL_TASK')" % (database) )
    # check IBMHIST.TAB_ERRS for errors
    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM IBMHIST.TAB_ERRS")
    errs = ibm_db.fetch_assoc(stmt)
    assert not errs, "Errors were produced calling IBMHIST.PROC_COLLECT on a dummy SQL task: %s" % errs
    # check IBMHIST.TAB_DIRS for directory
    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM IBMHIST.TAB_DIRS WHERE STATUS = 'COLL'")
    coll_dir = ibm_db.fetch_assoc(stmt)
    assert coll_dir, "Collection directory was not found in IBMHIST.TAB_DIRS after calling IBMHIST.PROC_COLLECT"
    # ensure collection directory and collection file exists
    assert os.path.exists(coll_dir['PATH']), "Collection directory was not found after calling IBMHIST.PROC_COLLECT: %s" % coll_dir['PATH']
    coll_file = [f for f in os.listdir(coll_dir['PATH']) if 'DUMMY_SQL_TASK' in f]
    assert coll_file, "Collection file was not found after calling IBMHIST.PROC_COLLECT: %s" % os.path.join(coll_dir['PATH'], 'DUMMY_SQL_TASK_timestamp.del')
    # read collection file and ensure header and data is correct
    coll_file = os.path.join(coll_dir['PATH'], coll_file[0])
    with open(coll_file) as f:
        lines = f.readlines()
        assert "DUMMY_HEADER" in lines[0], "Header not found in collection file %s after calling IBMHIST.PROC_COLLECT on a dummy SQL task" % coll_file
        assert "DUMMY_DATA" in lines[1], "Data not found in collection file %s after calling IBMHIST.PROC_COLLECT on a dummy SQL task" % coll_file

    # test IBMHIST.PROC_COLLECT with a dummy SYS task
    print("    Testing IBMHIST.PROC_COLLECT with a dummy SYS task ...")
    # create dummy SYS task
    ibm_db.exec_immediate(conn, "INSERT INTO IBMHIST.TAB_TASKS VALUES ( 'DUMMY_SYS_TASK', 'SYS', 'echo DUMMY_DATA', 'DUMMY_HEADER\n')")
    # call IBMHIST.PROC_COLLECT on dummy SYS task
    ibm_db.exec_immediate(conn, "CALL IBMHIST.PROC_COLLECT('%s', 'DUMMY_SYS_TASK')" % (database) )
    # check IBMHIST.TAB_ERRS for errors
    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM IBMHIST.TAB_ERRS")
    errs = ibm_db.fetch_assoc(stmt)
    assert not errs, "Errors were produced calling IBMHIST.PROC_COLLECT on a dummy SYS task: %s" % errs
    # check IBMHIST.TAB_DIRS for directory
    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM IBMHIST.TAB_DIRS WHERE STATUS = 'COLL'")
    coll_dir = ibm_db.fetch_assoc(stmt)
    assert coll_dir, "Collection directory was not found in IBMHIST.TAB_DIRS after calling IBMHIST.PROC_COLLECT"
    # ensure collection directory and collection file exists
    assert os.path.exists(coll_dir['PATH']), "Collection directory was not found after calling IBMHIST.PROC_COLLECT: %s" % coll_dir['PATH']
    coll_file = [f for f in os.listdir(coll_dir['PATH']) if 'DUMMY_SYS_TASK' in f]
    assert coll_file, "Collection file was not found after calling IBMHIST.PROC_COLLECT: %s" % os.path.join(coll_dir['PATH'], 'DUMMY_SYS_TASK_timestamp.del')
    # read collection file and ensure header and data is correct
    coll_file = os.path.join(coll_dir['PATH'], coll_file[0])
    with open(coll_file) as f:
        lines = f.readlines()
        assert "DUMMY_HEADER" in lines[0], "Header not found in collection file %s after calling IBMHIST.PROC_COLLECT on a dummy SYS task" % coll_file
        assert "DUMMY_DATA" in lines[1], "Data not found in collection file %s after calling IBMHIST.PROC_COLLECT on a dummy SYS task" % coll_file

    # test IBMHIST.PROC_ARCHIVE to archive collection directories
    print("    Testing IBMHIST.PROC_ARCHIVE to archive collection directories ...")
    # set time to 1 hour behind in IBMHIST.TAB_DIRS so collection directories are archived
    ibm_db.exec_immediate(conn, "UPDATE IBMHIST.TAB_DIRS SET TIME = TIME - 1 HOURS")
    # call IBMHIST.PROC_ARCHIVE
    ibm_db.exec_immediate(conn, "CALL IBMHIST.PROC_ARCHIVE('%s')" % (database) )
    # check IBMHIST.TAB_ERRS for errors
    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM IBMHIST.TAB_ERRS")
    errs = ibm_db.fetch_assoc(stmt)
    assert not errs, "Errors were produced calling IBMHIST.PROC_ARCHIVE to archive collection directories: %s" % errs
    # check IBMHIST.TAB_DIRS for directory
    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM IBMHIST.TAB_DIRS WHERE STATUS = 'ARCH'")
    arch_dir = ibm_db.fetch_assoc(stmt)
    assert arch_dir, "Archival directory was not found in IBMHIST.TAB_DIRS after calling IBMHIST.PROC_ARCHIVE"
    # ensure archival directory exists and collection directory no longer exists
    assert os.path.exists(arch_dir['PATH']), "Archival directory was not found after calling IBMHIST.PROC_ARCHIVE: %s" % arch_dir['PATH']
    assert not os.path.exists(coll_dir['PATH']), "Collection directory was not deleted after calling IBMHIST.PROC_ARCHIVE: %s" % coll_dir['PATH']

    # test IBMHIST.PROC_ARCHIVE to delete archival directories once a max size has been reached
    print("    Testing IBMHIST.PROC_ARCHIVE to delete archival directories once max size is reached ...")
    # set max size to max int value in IBMHIST.TAB_DIRS so archival directories are deleted
    ibm_db.exec_immediate(conn, "UPDATE IBMHIST.TAB_DIRS SET SIZE = 9223372036854775807")
    # call IBMHIST.PROC_ARCHIVE
    ibm_db.exec_immediate(conn, "CALL IBMHIST.PROC_ARCHIVE('%s')" % (database) )
    # check IBMHIST.TAB_ERRS for errors
    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM IBMHIST.TAB_ERRS")
    errs = ibm_db.fetch_assoc(stmt)
    assert not errs, "Errors were produced calling IBMHIST.PROC_ARCHIVE to delete archival directories: %s" % errs
    # check IBMHIST.TAB_DIRS for directory
    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM IBMHIST.TAB_DIRS WHERE STATUS = 'ARCH'")
    del_dir = ibm_db.fetch_assoc(stmt)
    assert not del_dir, "Archival directory was not deleted from IBMHIST.TAB_DIRS after calling IBMHIST.PROC_ARCHIVE to delete archival directories"
    # ensure archival directory no longer exists
    assert not os.path.exists(arch_dir['PATH']), "Archival directory was not deleted after calling IBMHIST.PROC_ARCHIVE to delete: %s" % arch_dir['PATH']

# determine if Windows/Unix, pureScale, HADR environment
def get_env(conn, database):

    print("Determining environment ...")
    env = {}

    # determine if Windows or Unix
    print("    Determining if Windows or Unix ...")
    if os.name == 'nt':
        env['WINDOWS'], env['UNIX'] = True, False
        print("        Windows detected ...")
    else:
        env['WINDOWS'], env['UNIX'] = False, True
        print("        Unix detected ...")

    # determine pureScale environment
    print("    Determining if pureScale ...")
    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM TABLE ( MON_GET_CF ( NULL ) )")
    if ibm_db.fetch_assoc(stmt):
        env['PURESCALE'] = True
        print("        pureScale detected ...")
    else:
        env['PURESCALE'] = False
        print("        pureScale not detected ...")

    # determine HADR environment
    print("    Determining if HADR ...")
    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM TABLE ( MON_GET_HADR ( -2 ) )")
    if ibm_db.fetch_assoc(stmt):
        env['HADR'] = True
        print("         HADR detected ...")
    else:
        env['HADR'] = False
        print("        HADR not detected ...")

    return env

# function to schedule collection tasks from task_details.json file and archive task
def schedule_tasks(conn, database, in_coll_lvl, env):

    print("Scheduling tasks ...")

    # enable Admin Task Scheduler
    print("    Setting Admin Task Scheduler registry variable ...")
    subprocess.check_call("db2set DB2_ATS_ENABLE=YES", shell=True)

    # load task_details.json file
    print("    Reading from task_details.json file ...")
    with open('task_details.json') as json_file:
        tasks = json.load(json_file)

    # insert tasks into IBMHIST.TAB_TASKS and schedule with Admin Task Scheduler
    for task in tasks:

        # get paramaters
        collection_name = task['collection_name']
        collection_freq = task['collection_freq']
        collection_class = task['collection_class']
        collection_command = task['collection_command']
        coll_lvl = int(task['collection_level'])
        collection_condition = task['collection_condition']

        # check collection_level constraint
        if in_coll_lvl and coll_lvl > in_coll_lvl:
            continue

        # check collection_condition constraint
        skip_task = False
        for condition, fulfilled in env.items():
            if condition in collection_condition and fulfilled is False:
                skip_task = True
        if skip_task:
            continue

        print("    Scheduling task: %s" % (collection_name) )

        # check command and generate header
        if collection_class == "SQL":
            # try sql command
            try:
                stmt = ibm_db.exec_immediate(conn, collection_command)
            except Exception as e:
                print("        Skipping due to error: %s" % e )
                continue
            # generate header for sql command as comma seperated field names
            header = [ ibm_db.field_name(stmt, i) for i in range(ibm_db.num_fields(stmt)) ]
            header = ",".join(header) + '\n'
        elif collection_class == "SYS":
            # try sys command
            try:
                devnull = open(os.devnull, 'w')
                subprocess.check_call(collection_command, shell=True, stdout=devnull, stderr=devnull)
            except Exception as e:
                print("        Skipping due to error: %s" % e )
                continue
            # generate header for sys command as collection name
            header = collection_name + '\n'

        # insert task into IBMHIST.TAB_TASKS
        ibm_db.exec_immediate(conn, "INSERT INTO IBMHIST.TAB_TASKS VALUES ('%s', '%s', '%s', '%s') " % (collection_name, collection_class, collection_command, header) )

        # schedule IBMHIST.PROC_COLLECT (database, collection_name) task
        ibm_db.exec_immediate(conn, "CALL SYSPROC.ADMIN_TASK_ADD ( '%s', NULL, NULL, NULL, '%s', 'IBMHIST', 'PROC_COLLECT', 'values (''%s'', ''%s'')', NULL, 'IBMHIST Collection' )" % (collection_name, collection_freq, database, collection_name) )

    # schedule archive task
    print("    Scheduling task: ARCHIVE")
    # schedule IBMHIST.PROC_ARCHIVE (database) task
    ibm_db.exec_immediate(conn, "CALL SYSPROC.ADMIN_TASK_ADD ( 'ARCHIVE', NULL, NULL, NULL, '*/10 * * * *', 'IBMHIST', 'PROC_ARCHIVE', 'values (''%s'')', NULL, 'IBMHIST Archival' )" % (database) )

    # collection will begin in approximately 5 minutes
    print("    Collection will begin in approximately 5 minutes ...")

# function to unschedule old tasks
def unschedule_tasks(conn):

    print("Unscheduling tasks ...")

    # unschedule tasks from Admin Task Scheduler
    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM SYSCAT.TABLES WHERE TABSCHEMA = 'SYSTOOLS' AND TABNAME = 'ADMIN_TASK_LIST'")
    if ibm_db.fetch_assoc(stmt):

        # get all tasks belonging to schema IBMHIST
        stmt = ibm_db.exec_immediate(conn, "SELECT NAME FROM SYSTOOLS.ADMIN_TASK_LIST WHERE PROCEDURE_SCHEMA = 'IBMHIST'")
        while ibm_db.fetch_row(stmt):

            # get name
            collection_name = ibm_db.result(stmt, "NAME")

            # unschedule task
            ibm_db.exec_immediate(conn, "CALL SYSPROC.ADMIN_TASK_REMOVE( '%s', NULL )" % (collection_name) )

    # delete tasks from IBMHIST.TAB_TASKS
    stmt = ibm_db.exec_immediate(conn, "SELECT * FROM SYSCAT.TABLES WHERE TABSCHEMA = 'IBMHIST' AND TABNAME = 'TAB_TASKS'")
    if ibm_db.fetch_assoc(stmt):

        ibm_db.exec_immediate(conn, "DELETE FROM IBMHIST.TAB_TASKS")

def main():

    # get diagpath
    cfgs = subprocess.check_output("db2 get dbm cfg", shell=True).decode('ascii').splitlines()
    diagpath = [cfg.split('=')[1].strip() for cfg in cfgs if "Diagnostic data directory path" in cfg][0]

    # parse arguments
    description="Setup IBMHIST monitoring program. View README for more information."
    parser = argparse.ArgumentParser(description=description)

    # database arguments
    parser.add_argument('database', help='name of database')
    parser.add_argument('-un', '--username', metavar='', default='',
                        help='username used to connect to database, default is that of current user')
    parser.add_argument('-pw', '--password', metavar='', default='',
                        help='password used to connect to database, default is that of current user')

    # flags
    parser.add_argument('-c', '--cleanup', metavar='', action='store_const', const=True, default=False,
                        help='will drop the IBMHIST schema and all of its objects, and unschedule its tasks')
    parser.add_argument('-uc', '--update_config_only', metavar='', action='store_const', const=True, default=False,
                        help='will update config values to passed in arguments or reset to defaults for those not explicitly specified')
    parser.add_argument('-ut', '--update_tasks_only', metavar='', action='store_const', const=True, default=False,
                        help='will unschedule all old tasks and reschedule to match with the task_details.json file')

    # path of bldrtn file
    parser.add_argument('-bp', '--bldrtn_path', metavar='',
                        default= "C:\\Program Files\\IBM\\SQLLIB\\samples\\cpp\\bldrtn.bat" if os.name == 'nt'
                            else os.path.expanduser("~/sqllib/samples/cpp/bldrtn"),
                        help="specify path for bldrtn script if it is not automatically found, default: %(default)s")

    # collection/archival paths and max size
    parser.add_argument('-cp', '--coll_path', metavar='', default= os.path.abspath(diagpath),
                        help='directory path of data collection, default: %(default)s')
    parser.add_argument('-ap', '--arch_path', metavar='', default= os.path.abspath(diagpath),
                        help='directory path of data archival, default: %(default)s')
    parser.add_argument('-ms', '--max_size', metavar='', type=int, default= 1073741824,
                        help='max size in bytes of collection and archival, default: %(default)s')

    # archival command and extension
    parser.add_argument('-acmd', '--arch_cmd', metavar='',
                        default= 'powershell -command "Compress-Archive" -Path _src_ -DestinationPath _dest_' if os.name == 'nt'
                            else 'tar -caf _dest_ _src_',
                        help='command used to archive hourly folders with "_src_" and "_dest_" placeholders, default: %(default)s')
    parser.add_argument('-aext', '--arch_ext', metavar='',
                        default= '.zip' if os.name == 'nt'
                            else '.tar.gz',
                        help='extension of archived hourly folders beginning with ".", default: %(default)s')

    # collection level of tasks
    parser.add_argument('-lvl', '--coll_lvl', metavar='', type=int,
                        help='scope of tasks to schedule (1 will only schedule key tasks, 2 will schedule more), all tasks scheduled if unspecified')

    # parse and transform arguments
    args = parser.parse_args()
    args.database = args.database.upper()
    args.bldrtn_path = os.path.abspath(args.bldrtn_path)
    args.coll_path, args.arch_path, args.max_size = os.path.abspath(args.coll_path),  os.path.abspath(args.arch_path), str(args.max_size)

    # try to connect to database
    print("Connecting to database: %s" % args.database)
    conn = ibm_db.connect(args.database, args.username, args.password)

    # create tablespace SYSTOOLSPACE
    stmt = ibm_db.exec_immediate(conn, "SELECT TBSPACE FROM SYSCAT.TABLESPACES WHERE TBSPACE = 'SYSTOOLSPACE'")
    if not ibm_db.fetch_assoc(stmt):
        print("Creating tablespace SYSTOOLSPACE ...")
        ibm_db.exec_immediate(conn, "CREATE TABLESPACE SYSTOOLSPACE IN IBMCATGROUP MANAGED BY AUTOMATIC STORAGE EXTENTSIZE 4")

    if args.cleanup:

        # unschedule old tasks
        unschedule_tasks(conn)

        # drop old IBMHIST schema and its objects
        drop_IBMHIST(conn)

    elif args.update_config_only:

        # test arguments and set configurations in IBMHIST.TAB_CONFIG
        config_IBMHIST(conn, args.coll_path, args.arch_path, args.max_size, args.arch_cmd, args.arch_ext)

    elif args.update_tasks_only:

        # determine if Windows/Unix, pureScale, HADR environment
        env = get_env(conn, args.database)

        # unschedule old tasks
        unschedule_tasks(conn)

        # schedule collection tasks from task_details.json file and archive task
        schedule_tasks(conn, args.database, args.coll_lvl, env)

    else:

        # determine if Windows/Unix, pureScale, HADR environment
        env = get_env(conn, args.database)

        # unschedule old tasks
        unschedule_tasks(conn)

        # drop old IBMHIST schema and its objects
        drop_IBMHIST(conn)

        # setup IBMHIST schema and register all table and procedure objects
        setup_IBMHIST(conn, args.bldrtn_path)

        # test arguments and set configurations in IBMHIST.TAB_CONFIG
        config_IBMHIST(conn, args.coll_path, args.arch_path, args.max_size, args.arch_cmd, args.arch_ext)

        # test basic functionality of IBMHIST.PROC_COLLECT and IBMHIST.PROC_ARCHIVE
        test_IBMHIST(conn, args.database)

        # schedule collection tasks from task_details.json file and archive task
        schedule_tasks(conn, args.database, args.coll_lvl, env)

    # close connection
    print("Closing connection ...")
    ibm_db.close(conn)

    print("Done")

if __name__ == "__main__":
    main()