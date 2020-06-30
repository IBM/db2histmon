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


-- table of configurations such as COLL_PATH, ARCH_PATH, MAX_SIZE, ARCH_CMD, ARCH_EXT, TASK_DETAILS_PATH, etc
create table IBMHIST.TAB_CONFIG (
        config_name   varchar(64)    not null, -- name of configuration
        value         varchar(512)   not null, -- value of configuration
        description   varchar(512),            -- brief description of configuration
        primary key (config_name)
) ; @