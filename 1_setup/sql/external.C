////////////////////////////////////////////////////////////////////////////////
// (c) Copyright IBM Corp. 2020 All rights reserved.

// The following sample of source code ("Sample") is owned by International
// Business Machines Corporation or one of its subsidiaries ("IBM") and is
// copyrighted and licensed, not sold. You may use, copy, modify, and
// distribute the Sample in any form without payment to IBM, for the purpose of
// assisting you in the development of your applications.

// The Sample code is provided to you on an "AS IS" basis, without warranty of
// any kind. IBM HEREBY EXPRESSLY DISCLAIMS ALL WARRANTIES, EITHER EXPRESS OR
// IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
// MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. Some jurisdictions do
// not allow for the exclusion or limitation of implied warranties, so the above
// limitations or exclusions may not apply to you. IBM shall not be liable for
// any damages you suffer as a result of using, copying, modifying or
// distributing the Sample, even if IBM has been advised of the possibility of
// such damages.
////////////////////////////////////////////////////////////////////////////////


//////////////////////////////////////////////
// C++ functions used by IBMHIST utility    //
// to perform operating system tasks        //
//                                          //
// see header file for more information     //
//                                          //
//////////////////////////////////////////////


#include "external.h"

#if defined(__cplusplus)
extern "C" {
#endif


//////////////////////////////////////////////
//              Core Functions              //
//////////////////////////////////////////////


int path_access ( const char * path , const int mode )
{
#if defined DB2NT
    if ( _access ( path, mode ) != 0 )
#else
    if ( access ( path, mode ) != 0 )
#endif
    {
        return -1 * __LINE__;
    }

    return 0 ;
}


int path_chmod ( const char * path, const int mode )
{
#if defined DB2NT
    if ( _chmod ( path, mode ) != 0 )
#else
    if ( chmod ( path, mode ) != 0 )
#endif
    {
        return -1 * __LINE__;
    }

    return 0 ;
}


int path_get_type ( const char * path )
{
#if defined DB2NT
    struct _stat64 buf ;
    if ( _stat64 ( path, &buf ) != 0 )
#else
    struct stat64 buf ;
    if ( stat64 ( path, &buf ) != 0 )
#endif
    {
        return -1 * __LINE__ ;
    }

    return buf.st_mode & OS_PATH_TYPE_MASK ;
}


long long int path_get_size ( const char * path )
{
#if defined DB2NT
    struct _stat64 buf ;
    if ( _stat64 ( path, &buf ) != 0 )
#else
    struct stat64 buf ;
    if ( stat64 ( path, &buf ) != 0 )
#endif
    {
        return -1 * __LINE__ ;
    }

    return buf.st_size ;
}


int copy_file ( const char * source_path, const char * target_path, const char * mode )
{
    if ( mode[0] != 'a' && mode[0] != 'w' )
    {
        return -1 * __LINE__ ;
    }

    // tests if paths exist and have or can get required permissions
    if ( path_access ( source_path, OS_PATH_R_OK ) != 0 )
    {
        if ( path_chmod ( source_path, OS_PERM_DEFAULT ) != 0 )
        {
            return -1 * __LINE__ ;
        }
    }
    if ( path_access ( target_path, OS_PATH_F_OK ) == 0 && path_access ( target_path, OS_PATH_W_OK ) != 0 )
    {
        if ( path_chmod ( target_path, OS_PERM_DEFAULT ) != 0 )
        {
            return -1 * __LINE__ ;
        }
    }

    FILE * source_file = NULL ;
    FILE * target_file = NULL ;
    char buf[ FILE_IO_BUFFER_SIZE ] = { 0 } ;
    int  readBytes   = 0 ;
    int  writeBytes  = 0 ;

    // open files
    if ( ( source_file = fopen ( source_path, "r") ) == NULL )
    {
        return -1 * __LINE__ ;
    }
    if ( ( target_file = fopen ( target_path, mode ) ) == NULL )
    {
        return -1 * __LINE__ ;
    }

    while ( ! feof ( source_file ) )
    {

        // read from source file
        do
        {
            readBytes = fread ( buf, sizeof(char), sizeof(buf), source_file ) ;
        } while ( readBytes < 0 ) ;

        if ( readBytes < 0 )
        {
            return -1 * __LINE__ ;
        }
        else if ( readBytes > 0 )
        {
            // write to target file
            do
            {
                writeBytes = fwrite ( buf, sizeof(char), readBytes, target_file ) ;
            } while ( writeBytes < 0 ) ;

            if ( ( writeBytes < 0 ) || ( writeBytes != readBytes ) )
            {
                return -1 * __LINE__ ;
            }
        }

    }

    // close files
    if ( fclose ( source_file ) != 0 )
    {
        return -1 * __LINE__ ;
    }
    if ( fclose ( target_file ) != 0 )
    {
        return -1 * __LINE__ ;
    }

    return 0 ;
}


int clob_to_file ( const char * path, const char * mode, const SQLUDF_CLOB * in_clob )
{
    if ( mode[0] != 'a' && mode[0] != 'w' )
    {
        return -1 * __LINE__ ;
    }

    // tests if path exists and has or can get required permissions
    if ( path_access ( path, OS_PATH_F_OK ) == 0 && path_access ( path, OS_PATH_W_OK ) != 0 )
    {
        if ( path_chmod ( path, OS_PERM_DEFAULT ) != 0 )
        {
            return -1 * __LINE__ ;
        }
    }

    FILE * file = NULL ;
    char buf[ FILE_IO_BUFFER_SIZE ] = { 0 } ;

    // open file
    if ( ( file = fopen ( path, mode ) ) == NULL )
    {
        return -1 * __LINE__ ;
    }

    // write clob to file
    if ( fwrite ( in_clob->data, sizeof(char), in_clob->length, file ) < ( in_clob->length ) )
    {
        return -1 * __LINE__ ;
    }

    // close file
    if ( fclose ( file ) != 0 )
    {
        return -1 * __LINE__ ;
    }

    return 0 ;
}


int make_directory ( const char * path )
{

#if defined DB2NT

    // make directory if it does not already exists
    if ( CreateDirectory ( path, NULL ) == 0 )
    {
        if ( GetLastError () != ERROR_ALREADY_EXISTS )
        {
            return -1 * __LINE__ ;
        }
    }

#else

    // make directory if it does not already exists
    if ( mkdir ( path, OS_PERM_DEFAULT ) != 0 )
    {
        if ( errno != EEXIST )
        {
            return -1 * __LINE__ ;
        }
    }

#endif

    // change permissions
    if ( path_chmod ( path, OS_PERM_DEFAULT ) != 0 )
    {
        return -1 * __LINE__ ;
    }

    return 0 ;
}


int remove_directory ( const char * path )
{

#if defined DB2NT

    // if directory, will need to remove subelements recursively
    if ( path_get_type ( path ) == OS_PATH_DIR )
    {
        int retcode = 0 ;
        char search_path [ OS_MAX_PATH_LEN ] ;
        char sub_path [ OS_MAX_PATH_LEN ] ;
        HANDLE sub_handle ;
        WIN32_FIND_DATA sub_info ;

        // open directory
        sprintf( search_path, "%s%c*", path, OS_PATH_SEP ) ;
        if ( ( sub_handle = FindFirstFile ( search_path, &sub_info ) ) == INVALID_HANDLE_VALUE )
        {
            return -1 * __LINE__ ;
        }

        // remove subelements recursively
        do
        {
            if (  strcmp ( sub_info.cFileName, "." ) != 0 && strcmp ( sub_info.cFileName, ".." ) != 0 )
            {
                sprintf( sub_path, "%s%c%s", path, OS_PATH_SEP, sub_info.cFileName ) ;
                retcode = remove_directory ( sub_path ) ;
                if ( retcode < 0 )
                {
                    return retcode ;
                }
            }
        } while ( FindNextFile ( sub_handle, &sub_info ) ) ;

        // close directory
        if ( FindClose( sub_handle ) == 0 )
        {
            return -1 * __LINE__ ;
        }

        // can now remove directory since subelements removed
        if ( RemoveDirectory ( path ) == 0 )
        {
            return -1 * __LINE__ ;
        }
    }

    // if file, can remove it directly
    else if ( path_get_type ( path ) == OS_PATH_REG )
    {
        if ( DeleteFile ( path ) == 0 )
        {
            return -1 * __LINE__ ;
        }
    }

#else

    // if directory, will need to remove subelements recursively
    if ( path_get_type ( path ) == OS_PATH_DIR )
    {
        int retcode = 0 ;
        char sub_path [ OS_MAX_PATH_LEN ] ;
        DIR * dir = NULL ;
        struct dirent * sub_entry = NULL ;

        // open directory
        if ( ( dir = opendir ( path ) ) == NULL )
        {
            return -1 * __LINE__ ;
        }

        // remove subelements recursively
        while ( ( sub_entry = readdir ( dir ) ) != NULL )
        {
            if (  strcmp ( sub_entry->d_name, "." ) != 0 && strcmp ( sub_entry->d_name, ".." ) != 0 )
            {
                snprintf( sub_path, sizeof( sub_path ), "%s%c%s", path, OS_PATH_SEP, sub_entry->d_name ) ;
                retcode = remove_directory ( sub_path ) ;
                if (  retcode < 0 )
                {
                    return retcode ;
                }
            }
        }

        // close directory
        if ( closedir ( dir ) != 0 )
        {
            return -1 * __LINE__ ;
        }

        // can now remove directory since subelements removed
        if ( rmdir ( path ) != 0 )
        {
            return -1 * __LINE__ ;
        }
    }

    // if file, can remove it directly
    else if ( path_get_type ( path ) == OS_PATH_REG )
    {
        if ( unlink ( path ) != 0 )
        {
            return -1 * __LINE__ ;
        }
    }

#endif

    return 0 ;
}


int move_directory ( const char * source_path, const char * target_path )
{
    if ( rename ( source_path, target_path ) != 0 )
    {
        return -1 * __LINE__ ;
    }

    return 0 ;
}


long long int sizeof_directory ( const char * path )
{

long long int size = 0 ;
long long int retcode = 0 ;

#if defined DB2NT

    // if directory, will need to accumulate size recursively
    if ( path_get_type ( path ) == OS_PATH_DIR )
    {
        char search_path [ OS_MAX_PATH_LEN ] ;
        char sub_path [ OS_MAX_PATH_LEN ] ;
        HANDLE sub_handle ;
        WIN32_FIND_DATA sub_info ;

        // open directory
        sprintf( search_path, "%s%c*", path, OS_PATH_SEP ) ;
        if ( ( sub_handle = FindFirstFile ( search_path, &sub_info ) ) == INVALID_HANDLE_VALUE )
        {
            return -1 * __LINE__ ;
        }

        // accumulate size of subelements recursively
        do
        {
            if (  strcmp ( sub_info.cFileName, "." ) != 0 && strcmp ( sub_info.cFileName, ".." ) != 0 )
            {
                sprintf( sub_path, "%s%c%s", path, OS_PATH_SEP, sub_info.cFileName ) ;
                retcode = sizeof_directory ( sub_path ) ;
                if ( retcode < 0 )
                {
                    return retcode ;
                }
                else
                {
                    size += retcode ;
                }
            }
        } while ( FindNextFile ( sub_handle, &sub_info ) ) ;

        // close directory
        if ( FindClose( sub_handle ) == 0 )
        {
            return -1 * __LINE__ ;
        }
    }

    // accumulate size of current element
    retcode = path_get_size ( path ) ;
    if ( retcode < 0 )
    {
        return -1 * __LINE__ ;
    }
    else
    {
        size += retcode ;
    }

#else

    // if directory, will need to accumulate size recursively
    if ( path_get_type ( path ) == OS_PATH_DIR )
    {
        char sub_path [ OS_MAX_PATH_LEN ] ;
        DIR * dir = NULL ;
        struct dirent * sub_entry = NULL ;

        // open directory
        if ( ( dir = opendir ( path ) ) == NULL )
        {
            return -1 * __LINE__ ;
        }

        // accumulate size of subelements recursively
        while ( ( sub_entry = readdir ( dir ) ) != NULL )
        {
            if (  strcmp ( sub_entry->d_name, "." ) != 0 && strcmp ( sub_entry->d_name, ".." ) != 0 )
            {
                snprintf( sub_path, sizeof( sub_path ), "%s%c%s", path, OS_PATH_SEP, sub_entry->d_name ) ;
                retcode = sizeof_directory ( sub_path ) ;
                if ( retcode < 0 )
                {
                    return retcode ;
                }
                else
                {
                    size += retcode ;
                }
            }
        }

        // close directory
        if ( closedir ( dir ) != 0 )
        {
            return -1 * __LINE__ ;
        }
    }

    // accumulate size of current element
    retcode = path_get_size ( path ) ;
    if ( retcode < 0 )
    {
        return retcode ;
    }
    else
    {
        size += retcode ;
    }

#endif

    return size ;
}


//////////////////////////////////////////////
//           SQL Wrapper Functions          //
//////////////////////////////////////////////


void SQL_API_FN sql_path_exists (
    SQLUDF_VARCHAR * path,
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * path_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS )
{
    if ( SQLUDF_NULL ( path_ind ) )
    {
        * retcode_ind = -1 * __LINE__ ;
        return;
    }

    * retcode = path_access ( path, OS_PATH_F_OK ) ;
    * retcode_ind = 0 ;

    return ;
}

void SQL_API_FN sql_path_readable_writable (
    SQLUDF_VARCHAR * path,
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * path_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS )
{
    if ( SQLUDF_NULL ( path_ind ) )
    {
        * retcode_ind = -1 * __LINE__ ;
        return;
    }

    * retcode = path_access ( path, OS_PATH_R_OK | OS_PATH_W_OK ) ;
    * retcode_ind = 0 ;

    return ;
}

void SQL_API_FN sql_copy_file (
    SQLUDF_VARCHAR * source_path,
    SQLUDF_VARCHAR * target_path,
    SQLUDF_CHAR    * mode,
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * source_path_ind,
    SQLUDF_NULLIND * target_path_ind,
    SQLUDF_NULLIND * mode_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS )
{
    if ( SQLUDF_NULL ( source_path_ind ) || SQLUDF_NULL ( target_path_ind ) )
    {
        * retcode_ind = -1 * __LINE__ ;
        return;
    }

    * retcode = copy_file ( source_path, target_path, mode ) ;
    * retcode_ind = 0 ;

    return ;
}


void SQL_API_FN sql_clob_to_file (
    SQLUDF_VARCHAR * path,
    SQLUDF_CHAR    * mode,
    SQLUDF_CLOB    * in_clob,
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * path_ind,
    SQLUDF_NULLIND * mode_ind,
    SQLUDF_NULLIND * in_clob_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS )
{
    if ( SQLUDF_NULL ( path_ind ) || SQLUDF_NULL ( mode_ind ) || SQLUDF_NULL ( in_clob_ind ) )
    {
        * retcode_ind = -1 * __LINE__ ;
        return ;
    }

    * retcode = clob_to_file ( path, mode, in_clob ) ;
    * retcode_ind = 0 ;

    return ;
}


void SQL_API_FN sql_make_directory (
    SQLUDF_VARCHAR * path,
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * path_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS )
{
    if ( SQLUDF_NULL ( path_ind ) )
    {
        * retcode_ind = -1 * __LINE__ ;
        return ;
    }

    * retcode = make_directory ( path ) ;
    * retcode_ind = 0 ;

    return ;
}


void SQL_API_FN sql_remove_directory (
    SQLUDF_VARCHAR * path,
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * path_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS )
{
    if ( SQLUDF_NULL ( path_ind ) )
    {
        * retcode_ind = -1 * __LINE__ ;
        return;
    }

    * retcode = remove_directory ( path ) ;
    * retcode_ind = 0 ;

    return ;
}


void SQL_API_FN sql_move_directory (
    SQLUDF_VARCHAR * source_path,
    SQLUDF_VARCHAR * target_path,
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * source_path_ind,
    SQLUDF_NULLIND * target_path_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS )
{
    if ( SQLUDF_NULL ( source_path_ind ) || SQLUDF_NULL ( target_path_ind ) )
    {
        * retcode_ind = -1 * __LINE__ ;
        return;
    }

    * retcode = move_directory ( source_path, target_path ) ;
    * retcode_ind = 0 ;

    return ;
}


void SQL_API_FN sql_sizeof_directory (
    SQLUDF_VARCHAR * path,
    SQLUDF_BIGINT  * retcode,
    SQLUDF_NULLIND * path_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS )
{
    if ( SQLUDF_NULL ( path_ind ) )
    {
        * retcode_ind = -1 * __LINE__ ;
        return;
    }

    * retcode = sizeof_directory ( path ) ;
    * retcode_ind = 0 ;

    return ;
}


void SQL_API_FN sql_is_windows (
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS )
{
#if defined DB2NT
    * retcode = 1 ;
#else
    * retcode = 0 ;
#endif
    * retcode_ind = 0 ;

    return ;
}


void SQL_API_FN sql_system_call (
    SQLUDF_VARCHAR *command,
    SQLUDF_INTEGER *retcode,
    SQLUDF_NULLIND *command_ind,
    SQLUDF_NULLIND *retcode_ind,
    SQLUDF_TRAIL_ARGS )
{
    if ( SQLUDF_NULL ( command_ind ) )
    {
        *retcode_ind = -1 * __LINE__ ;
        return ;
    }

    * retcode = system ( command ) ;
    // if error occured, ensure negative retcode
    if ( * retcode > 0 )
        * retcode = * retcode * -1 ;
    * retcode_ind = 0 ;

    return ;
}


#if defined(__cplusplus)
}
#endif