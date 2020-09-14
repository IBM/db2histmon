--------------------------------------------------------------------------------
-- (c) Copyright IBM Corp. 2020 All rights reserved.

-- The following sample of source code ("Sample") is owned by International
-- Business Machines Corporation or one of its subsidiaries ("IBM") and is
-- copyrighted and licensed, not sold. You may use, copy, modify, and
-- distribute the Sample in any form without payment to IBM, for the purpose of
-- assisting you in the development of your applications.

-- The Sample code is provided to you on an "AS IS" basis, without warranty of
-- any kind. IBM HEREBY EXPRESSLY DISCLAIMS ALL WARRANTIES, EITHER EXPRESS OR
-- IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
-- MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. Some jurisdictions do
-- not allow for the exclusion or limitation of implied warranties, so the above
-- limitations or exclusions may not apply to you. IBM shall not be liable for
-- any damages you suffer as a result of using, copying, modifying or
-- distributing the Sample, even if IBM has been advised of the possibility of
-- such damages.
--------------------------------------------------------------------------------


set schema IBMHIST ; @


-- procedure to collect data from sys and sql functions
create or replace procedure IBMHIST.PROC_COLLECT (
    in db_name varchar(64), -- name of database
    in collection_name varchar(64) -- name of task
)
language SQL
begin

    -- declare variables
    declare client_applname               varchar(70) ;
    declare is_windows                    int ;
    declare class                         varchar(3) ;
    declare command                       varchar(32672) ;
    declare header                        clob ;
    declare void_time                     timestamp       default '0001-01-01-00.00.00.00000' ;
    declare sch_time, prev_time           timestamp ;
    declare yr                            varchar(4) ;
    declare mn, dy, hr, mi                varchar(2) ;
    declare time_chg                      varchar(7)      default '' ;
    declare p_sep                         char ;
    declare task_details_path             varchar(512) ;
    declare coll_path, lob_path           varchar(512) ;
    declare coll_size                     bigint ;
    declare coll_status                   varchar(7) ;
    declare file_type                     varchar(3) ;
    declare file_path, tmp_path           varchar(512) ;

    declare err_msg                       varchar(2048)   default '' ;
    declare vSQLCODE, SQLCODE, retcode    int             default 0 ;
    declare vSQLSTATE, SQLSTATE           char(5)         default '00000' ;

    -- exception handler
    declare continue handler for SQLEXCEPTION, SQLWARNING, NOT FOUND
    begin
        select SQLCODE, SQLSTATE into vSQLCODE, vSQLSTATE from SYSIBM.SYSDUMMY1 ;
        -- except attemped primary key violation (-803) as tasks will concurrently update tables
        -- except warning during export (3107) such as truncating lob warning
        if ( vSQLCODE = -803 or vSQLCODE = 3107 ) then
            set vSQLCODE = 0 ;
            set vSQLSTATE = '00000' ;
        end if ;
    end ;

    -- set client_applname
    set client_applname = 'IBMHIST_' || collection_name ;
    call SYSPROC.WLM_SET_CLIENT_INFO ( NULL, NULL, client_applname, NULL, NULL ) ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to set client_applname' ;
        goto exit ;
    end if ;

    -- get platform and set path character accordingly
    call IBMHIST.IS_WINDOWS ( is_windows ) ;
    if ( is_windows = 1 ) then
        set p_sep = '\' ;
    else
        set p_sep = '/' ;
    end if ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to get platform' ;
        goto exit ;
    end if ;

    -- get command type, command, and header
    select class, command, header into class, command, header
        from IBMHIST.TAB_TASKS
        where coll_name = collection_name ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to get command type, command, and header from IBMHIST.TAB_TASKS' ;
        goto exit ;
    end if ;

    -- set scheduled time of current collection to beginning of current minute
    set sch_time = TRUNC_TIMESTAMP ( current timestamp , 'MI' ) ;
    set yr = LPAD ( YEAR ( sch_time ), 4, '0' ) ;
    set mn = LPAD ( MONTH ( sch_time ), 2, '0' ) ;
    set dy = LPAD ( DAY ( sch_time ), 2, '0' ) ;
    set hr = LPAD ( HOUR ( sch_time ), 2, '0' ) ;
    set mi = LPAD ( MINUTE ( sch_time ), 2, '0' ) ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to parse current time' ;
        goto exit ;
    end if ;

    -- determine if time change occured since last collection
    select COALESCE ( MAX ( time ), void_time ) into prev_time
        from IBMHIST.TAB_DIRS ;

    if ( prev_time > sch_time ) then
        set time_chg = '_tm_chg' ;
    end if ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to get determine if time change occured' ;
        goto exit ;
    end if ;

    -- get data collection path
    select value into coll_path
        from IBMHIST.TAB_CONFIG
        where config_name = 'COLL_PATH' ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to get data collection path from IBMHIST.TAB_CONFIG' ;
        goto exit ;
    end if ;

    -- test if data collection path is writable
    call IBMHIST.PATH_READABLE_WRITABLE ( coll_path, retcode ) ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to write to data collection path: ' || coll_path || ', external.C line number: ' || retcode ;
        goto exit ;
    end if ;

    -- create coll_path/IBMHIST_db_name directory if it does not exist
    set coll_path = coll_path || p_sep || 'IBMHIST_' || db_name ;
    call IBMHIST.MAKE_DIRECTORY ( coll_path, retcode ) ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to create data collection directory: ' || coll_path || ', external.C line number: ' || retcode ;
        goto exit ;
    end if ;

    -- create coll_path/IBMHIST_db_name/db_name_yrmndyhr(_tm_chg) directory if it does not exist
    set coll_path = coll_path || p_sep || db_name || '_' || yr || mn || dy || hr || time_chg ;
    call IBMHIST.MAKE_DIRECTORY ( coll_path, retcode ) ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to create data collection directory: ' || coll_path || ', external.C line number: ' || retcode ;
        goto exit ;
    end if ;

    -- create coll_path/IBMHIST_db_name/db_name_yrmndyhr(_tm_chg)/lob directory if it does not exist
    set lob_path = coll_path || p_sep || 'lob' ;
    call IBMHIST.MAKE_DIRECTORY ( lob_path, retcode ) ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to create data lob directory: ' || lob_path || ', external.C line number: ' || retcode ;
        goto exit ;
    end if ;

    -- get task_details.json path
    select value into task_details_path
        from IBMHIST.TAB_CONFIG
        where config_name = 'TASK_DETAILS_PATH' ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to get task_details.json path from IBMHIST.TAB_CONFIG' ;
        goto exit ;
    end if ;

    -- copy task_details.json file to data collection path
    call IBMHIST.COPY_FILE ( task_details_path, coll_path || p_sep || 'task_details_copy.json', 'w', retcode ) ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to copy task_details.json from: ' || task_details_path || ' to: ' || coll_path || ', external.C line number: ' || retcode ;
        goto exit ;
    end if ;

    -- set file_path to coll_path/IBMHIST_db_name/db_name_yrmndyhr(_tm_chg)/collection_name_yrmndyhrmm.del
    set file_type = 'del' ;
    set file_path = coll_path || p_sep || collection_name || '_' || yr || mn || dy || hr || mi || '.' || file_type ;
    set tmp_path = file_path || '.tmp' ;

    -- write header to file
    call IBMHIST.CLOB_TO_FILE ( file_path, 'w', header, retcode ) ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to write header to: ' || file_path || ', external.C line number: ' || retcode ;
        goto exit ;
    end if ;

    -- execute command and export data to temp file
    if  ( class = 'SQL' ) then

        call SYSPROC.ADMIN_CMD ( ' export to ' || tmp_path || ' of ' || file_type || ' lobs to ' || lob_path || ' ' || command ) ;

        if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
            set err_msg = 'Failed to execute command and export to: ' || tmp_path ;
            goto exit ;
        end if ;

    elseif ( class = 'SYS' ) then

        call IBMHIST.SYSTEM_CALL ( command || ' >> ' || tmp_path , retcode ) ;

        if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
            set err_msg = 'Failed to execute command and export to: ' || tmp_path || ', system return code: ' || retcode ;
            goto exit ;
        end if ;

    end if;

    -- append data to header
    call IBMHIST.COPY_FILE ( tmp_path, file_path, 'a', retcode ) ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to append data: ' || tmp_path || ' to header: ' || file_path || ', external.C line number: ' || retcode ;
        goto exit ;
    end if ;

    -- remove temp file
    call IBMHIST.REMOVE_DIRECTORY( tmp_path, retcode ) ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to remove temp: ' || tmp_path || ', external.C line number: ' || retcode ;
        goto exit ;
    end if ;

    -- update IBMHIST.TAB_DIRS
    call IBMHIST.SIZEOF_DIRECTORY( coll_path, coll_size ) ;
    set coll_status = 'COLL' ;

    if exists (select * from IBMHIST.TAB_DIRS where path = coll_path)
    then
        update IBMHIST.TAB_DIRS
            set size = coll_size, status = coll_status, time = sch_time
            where path = coll_path;
    else
        insert into IBMHIST.TAB_DIRS
            values(coll_path, coll_size, coll_status, sch_time) ;
    end if ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to update IBMHIST.TAB_DIRS' ;
        goto exit ;
    end if ;

exit :

    -- if error detected, log error into IBMHIST.TAB_ERRS
    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 or err_msg != '' ) then
        insert into IBMHIST.TAB_ERRS
            values( current timestamp, 'PROC_COLLECT', collection_name, vSQLCODE, vSQLSTATE, err_msg ) ;
        return -1 ;
    end if;

    return 0 ;

end @


grant execute on procedure IBMHIST.PROC_COLLECT to PUBLIC @