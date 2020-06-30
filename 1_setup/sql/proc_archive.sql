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


-- procedure to archive past data directories and remove old archivals directories
create or replace procedure IBMHIST.PROC_ARCHIVE (
    in db_name varchar(64) -- name of database
)
language SQL
begin

    -- declare variables
    declare client_applname               varchar(70) ;
    declare is_windows                    int ;
    declare cur_time                      timestamp ;
    declare yr                            varchar(4) ;
    declare mn, dy, hr, mi                varchar(2) ;
    declare time_chg                      varchar(7)      default '' ;
    declare p_sep                         char ;
    declare cur_path, cur_name            varchar(512) ;
    declare max_size, tot_size            bigint ;
    declare base_arch_path, arch_path     varchar(512) ;
    declare arch_size                     bigint ;
    declare arch_status                   varchar(4) ;
    declare base_arch_cmd, arch_cmd       varchar(512) ;
    declare base_arch_ext, arch_ext       varchar(512) ;

    declare err_msg                       varchar(2048)   default '' ;
    declare vSQLCODE, SQLCODE, retcode    int             default 0 ;
    declare vSQLSTATE, SQLSTATE           char(5)         default '00000' ;

    -- cursor for past data collection directories
    declare coll_cur cursor for
        select path from IBMHIST.TAB_DIRS
        where status = 'COLL' and time < cur_time
        order by time asc ;

    -- cursor for past data archival directories
    declare arch_cur cursor for
        select path from IBMHIST.TAB_DIRS
        where status = 'ARCH' and time < cur_time
        order by time asc ;

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
    set client_applname = 'IBMHIST_CLEANUP' ;
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

    -- set time of current directory to beginning of current hour
    set cur_time  = TRUNC_TIMESTAMP ( current timestamp , 'HH' ) ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to parse current time' ;
        goto exit ;
    end if ;

    -- get base data archival path
    select value into base_arch_path
        from IBMHIST.TAB_CONFIG
        where config_name = 'ARCH_PATH' ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to get base data archival path from IBMHIST.TAB_CONFIG' ;
        goto exit ;
    end if ;

    -- test if base data archival path is writable
    call IBMHIST.PATH_READABLE_WRITABLE ( base_arch_path, retcode ) ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to write to base data archival path: ' || base_arch_path || ', external.C line number: ' || retcode ;
        goto exit ;
    end if ;

    -- create base_arch_path/IBMHIST_db_name_archive directory if it does not exist
    set base_arch_path = base_arch_path || p_sep || 'IBMHIST_' || db_name || '_archive' ;
    call IBMHIST.MAKE_DIRECTORY ( base_arch_path, retcode ) ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to create data archival directory: ' || base_arch_path || ', external.C line number: ' || retcode ;
        goto exit ;
    end if ;

    -- get archival command and archival extension
    select value into base_arch_cmd
        from IBMHIST.TAB_CONFIG
        where config_name = 'ARCH_CMD' ;
    select value into base_arch_ext
        from IBMHIST.TAB_CONFIG
        where config_name = 'ARCH_EXT' ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to get archival command or archival extension from IBMHIST.TAB_CONFIG' ;
        goto exit ;
    end if ;

    -- loop through past data collection directories in IBMHIST.TAB_DIRS and archive them
    open coll_cur ;
    fetch from coll_cur into cur_path ;
    while ( vSQLCODE = 0 and vSQLSTATE = '00000' )
    do

        -- reset parameters
        set arch_path = base_arch_path ;
        set arch_cmd = base_arch_cmd ;
        set arch_ext = base_arch_ext ;

        -- check if current data collection path exists
        call IBMHIST.PATH_EXISTS ( cur_path, retcode ) ;

        if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
            set err_msg = 'Failed to find data collection: ' || cur_path || ', external.C line number: ' || retcode ;
            goto exit ;
        end if ;

        -- set data archival path
        set cur_name = RIGHT ( cur_path, LENGTH ( cur_path ) - LOCATE_IN_STRING ( cur_path , p_sep, -1 ) ) ;
        set arch_path = arch_path || p_sep || cur_name || arch_ext ;

        if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
            set err_msg = 'Failed to set data archival path' ;
            goto exit ;
        end if ;

        -- archive
        set arch_cmd = REPLACE ( arch_cmd, '_src_', cur_path ) ;
        set arch_cmd = REPLACE ( arch_cmd, '_dest_', arch_path ) ;
        call IBMHIST.SYSTEM_CALL ( arch_cmd , retcode ) ;

        if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
            set err_msg = 'Failed to archive: ' || cur_path || ' to: ' || arch_path || ', system return code: ' || retcode ;
            goto exit ;
        end if ;

        -- check if data archival path exists
        call IBMHIST.PATH_EXISTS ( arch_path, retcode ) ;

        if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
            set err_msg = 'Failed to find data archival: ' || arch_path || ', external.C line number: ' || retcode ;
            goto exit ;
        end if ;

        -- remove current data collection path
        call IBMHIST.REMOVE_DIRECTORY ( cur_path, retcode ) ;

        if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
            set err_msg = 'Failed to remove data collection:' || cur_path || ', external.C line number: ' || retcode ;
            goto exit ;
        end if ;

        -- update IBMHIST.TAB_DIRS
        call IBMHIST.SIZEOF_DIRECTORY ( arch_path, arch_size ) ;
        set arch_status = 'ARCH' ;

        update IBMHIST.TAB_DIRS u
            set u.path = arch_path, u.size = arch_size, u.status = arch_status
            where u.path = cur_path ;

        if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
            set err_msg = 'Failed to update IBMHIST.TAB_DIRS' ;
            goto exit ;
        end if ;

        fetch from coll_cur into cur_path ;
    end while ;
    close coll_cur ;

    set vSQLCODE = 0 ;
    set vSQLSTATE = '00000' ;

    -- get max size
    select value into max_size
        from IBMHIST.TAB_CONFIG
        where config_name = 'MAX_SIZE' ;

    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
        set err_msg = 'Failed to get max size from IBMHIST.TAB_CONFIG' ;
        goto exit ;
    end if ;

    -- loop through past data archival directories in IBMHIST.TAB_DIRS and delete them if necessary
    open arch_cur ;
    fetch from arch_cur into cur_path ;
    while ( vSQLCODE = 0 and vSQLSTATE = '00000' )
    do

        -- get total size
        select SUM ( size ) into tot_size
            from IBMHIST.TAB_DIRS ;

        if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
            set err_msg = 'Failed to find get total size from IBMHIST.TAB_DIRS' ;
            goto exit ;
        end if ;

        -- if total size exceeds max size, delete current data archival
        if ( tot_size > max_size )
        then

            -- check if current data archival path exists
            call IBMHIST.PATH_EXISTS ( cur_path, retcode ) ;

            if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
                set err_msg = 'Failed to find data archival: ' || cur_path || ', external.C line number: ' || retcode ;
                goto exit ;
            end if ;

            -- remove current data archival path
            call IBMHIST.REMOVE_DIRECTORY ( cur_path, retcode ) ;

            if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
                set err_msg = 'Failed to remove data archival: ' || cur_path || ', external.C line number: ' || retcode ;
                goto exit ;
            end if ;

            -- delete from IBMHIST.TAB_DIRS
            delete from  IBMHIST.TAB_DIRS u
                where u.path = cur_path ;

            if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 ) then
                set err_msg = 'Failed to delete from IBMHIST.TAB_DIRS' ;
                goto exit ;
            end if ;

        end if ;

        fetch from arch_cur into cur_path ;
    end while ;
    close arch_cur ;

    set vSQLCODE = 0 ;
    set vSQLSTATE = '00000' ;

exit :

    -- if error detected, log error into IBMHIST.TAB_ERRS
    if ( vSQLCODE < 0 or vSQLSTATE != '00000' or retcode < 0 or err_msg != '' ) then
        insert into IBMHIST.TAB_ERRS
            values( current timestamp, 'PROC_ARCHIVE', 'ARCHIVE', vSQLCODE, vSQLSTATE, err_msg ) ;
        return -1 ;
    end if;

    return 0 ;

end @


grant execute on procedure IBMHIST.PROC_ARCHIVE to PUBLIC @