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


set schema IBMHIST @


-- This file registers all the SQL wrapping functions
-- specified in external.h and external.C to Db2
-- see header file for more information


create or replace procedure IBMHIST.PATH_EXISTS (
    in path varchar(256),
    out retcode int
)
language c
no sql
parameter style sql
external name 'external!sql_path_exists' @
grant execute on procedure IBMHIST.PATH_EXISTS to PUBLIC @


create or replace procedure IBMHIST.PATH_READABLE_WRITABLE (
    in path varchar(256),
    out retcode int
)
language c
no sql
parameter style sql
external name 'external!sql_path_readable_writable' @
grant execute on procedure IBMHIST.PATH_READABLE_WRITABLE to PUBLIC @


create or replace procedure IBMHIST.COPY_FILE (
    in source_path varchar(256),
    in target_path varchar(256),
    in mode char,
    out retcode int
)
language c
no sql
parameter style sql
external name 'external!sql_copy_file' @
grant execute on procedure IBMHIST.COPY_FILE to PUBLIC @


create or replace procedure IBMHIST.CLOB_TO_FILE (
    in path varchar(256),
    in mode char,
    in in_clob clob,
    out retcode int
)
language c
no sql
parameter style sql
external name 'external!sql_clob_to_file' @
grant execute on procedure IBMHIST.CLOB_TO_FILE to PUBLIC @


create or replace procedure IBMHIST.MAKE_DIRECTORY (
    in path varchar(256),
    out retcode int
)
language c
no sql
parameter style sql
external name 'external!sql_make_directory' @
grant execute on procedure IBMHIST.MAKE_DIRECTORY to PUBLIC @


create or replace procedure IBMHIST.REMOVE_DIRECTORY (
    in path varchar(256),
    out retcode int
)
language c
no sql
parameter style sql
external name 'external!sql_remove_directory' @
grant execute on procedure IBMHIST.REMOVE_DIRECTORY to PUBLIC @


create or replace procedure IBMHIST.MOVE_DIRECTORY (
    in source_path varchar(256),
    in target_path varchar(256),
    out retcode int
)
language c
no sql
parameter style sql
external name 'external!sql_move_directory' @
grant execute on procedure IBMHIST.MOVE_DIRECTORY to PUBLIC @


create or replace procedure IBMHIST.SIZEOF_DIRECTORY (
    in path varchar(256),
    out retcode bigint
)
language c
no sql
parameter style sql
external name 'external!sql_sizeof_directory' @
grant execute on procedure IBMHIST.SIZEOF_DIRECTORY to PUBLIC @


create or replace procedure IBMHIST.IS_WINDOWS (
    out retcode int
)
language c
no sql
parameter style sql
external name 'external!sql_is_windows' @
grant execute on procedure IBMHIST.IS_WINDOWS to PUBLIC @


create or replace procedure IBMHIST.SYSTEM_CALL (
    in command varchar(32672),
    out retcode int
)
language c
no sql
parameter style sql
external name 'external!sql_system_call' @
grant execute on procedure IBMHIST.SYSTEM_CALL to PUBLIC @