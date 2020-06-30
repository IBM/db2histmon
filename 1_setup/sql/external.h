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
// Core Functions:                          //
// path_access                              //
// path_chmod                               //
// path_get_type                            //
// path_get_size                            //
// copy_file                                //
// clob_to_file                             //
// make_directory                           //
// remove_directory                         //
// move_directory                           //
// sizeof_directory                         //
//                                          //
// SQL Wrapping Functions:                  //
// sql_path_exists                          //
// sql_path_readable_writable               //
// sql_copy_file                            //
// sql_clob_to_file                         //
// sql_make_directory                       //
// sql_remove_directory                     //
// sql_move_directory                       //
// sql_sizeof_directory                     //
// sql_is_windows                           //
// sql_system_call                          //
//                                          //
//////////////////////////////////////////////


#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <sys/stat.h>
#include <string.h>

#include <sqludf.h>

#if defined DB2NT
    #include <windows.h>
#else
    #include <unistd.h>
    #include <dirent.h>
#endif

#if defined DB2NT
    #define BIT_BUCKET  "NUL"
    #define OS_PATH_SEP        '\\'
    #define OS_PATH_SEP_STR    "\\"
    #define OS_PATH_DELIM      ';'
    #define OS_PATH_DELIM_STR  ";"
    #define OS_RAW_NT_DEV_PREFIX "\\\\.\\"
#else
    #define BIT_BUCKET  "/dev/null"
    #define OS_PATH_SEP        '/'
    #define OS_PATH_SEP_STR    "/"
    #define OS_PATH_DELIM      ':'
    #define OS_PATH_DELIM_STR  ":"
#endif

#if defined DB2NT
    #define OS_PATH_TYPE_MASK _S_IFMT
    #define OS_PATH_DIR       _S_IFDIR
    #define OS_PATH_REG       _S_IFREG
    #define OS_PATH_LNK       0
    #define OS_PATH_F_OK      00
    #define OS_PATH_R_OK      04
    #define OS_PATH_W_OK      02
    #define OS_PATH_X_OK      99
    #define OS_FILE_PERM_UR   _S_IREAD
    #define OS_FILE_PERM_UW   _S_IWRITE
    #define OS_FILE_PERM_UX   _S_IEXEC
    #define OS_PATH_PERM_GR   0
    #define OS_PATH_PERM_GW   0
    #define OS_PATH_PERM_GX   0
    #define OS_PATH_PERM_OR   0
    #define OS_PATH_PERM_OW   0
    #define OS_PATH_PERM_OX   0
#else
    #define OS_PATH_TYPE_MASK S_IFMT
    #define OS_PATH_DIR       S_IFDIR
    #define OS_PATH_REG       S_IFREG
    #define OS_PATH_LNK       S_IFLNK
    #define OS_PATH_F_OK      F_OK
    #define OS_PATH_R_OK      R_OK
    #define OS_PATH_W_OK      W_OK
    #define OS_PATH_X_OK      X_OK
    #define OS_PATH_PERM_UR   S_IRUSR
    #define OS_PATH_PERM_UW   S_IWUSR
    #define OS_PATH_PERM_UX   S_IXUSR
    #define OS_PATH_PERM_GR   S_IRGRP
    #define OS_PATH_PERM_GW   S_IWGRP
    #define OS_PATH_PERM_GX   S_IXGRP
    #define OS_PATH_PERM_OR   S_IROTH
    #define OS_PATH_PERM_OW   S_IWOTH
    #define OS_PATH_PERM_OX   S_IXOTH
#endif

#define OS_PERM_DEFAULT 0777

#define OS_MAX_PATH_LEN ( 256 )
#define FILE_IO_BUFFER_SIZE ( 4096 )

#if defined(__cplusplus)
extern "C" {
#endif

//////////////////////////////////////////////
//              Core Functions              //
// perform filesystem tasks using libraries //
// to work on Windows and Linux             //
//////////////////////////////////////////////

// uses access/_access to check path permissions
// returns 0 if path is accessible in mode, or (-1 * __LINE__) if error
int path_access ( const char * path , const int mode ) ;

// uses chmod/_chmod to change path permissions
// returns 0 if path is changed to mode, or (-1 * __LINE__) if error
int path_chmod ( const char * path, const int mode ) ;

// uses stat64/_stat64 to get path type
// returns path type, or (-1 * __LINE__) if error
int path_get_type ( const char * path ) ;

// uses stat64/_stat64 to get path size
// returns path size in bytes, or (-1 * __LINE__) if error
long long int path_get_size ( const char * path ) ;

// writes or appends from source path to target path using fread/fwrite
int copy_file ( const char * source_path, const char * target_path, const char * mode ) ;

// writes or appends from clob to path using fwrite
int clob_to_file ( const char * path, const char * mode, const SQLUDF_CLOB * in_clob ) ;

// makes directory using mkdir/CreateDirectory
int make_directory ( const char * path ) ;

// recursively removes directory using unlink/rmdir/DeleteFile/RemoveDirectory
int remove_directory ( const char * path ) ;

// moves directory using rename
int move_directory ( const char * source_path, const char * target_path ) ;

// recursively gets size of directory
long long int sizeof_directory ( const char * path ) ;

//////////////////////////////////////////////
//           SQL Wrapper Functions          //
// wrap around core functions to interface  //
// with sql procedures                      //
//////////////////////////////////////////////

// verifies path exists
// sets retcode to 0 on success, (-1 * __LINE__) on error
void SQL_API_FN sql_path_exists (
    SQLUDF_VARCHAR * path,
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * path_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS ) ;

// tests if path exists and is readable/writable
// if not, tries to make it readable/writable
// sets retcode to 0 on success, (-1 * __LINE__) on error
void SQL_API_FN sql_path_readable_writable (
    SQLUDF_VARCHAR * path,
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * path_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS ) ;

// writes if mode="w" or appends if mode="a"
// from source_path to target_path
// sets retcode to 0 on success, (-1 * __LINE__) on error
void SQL_API_FN sql_copy_file (
    SQLUDF_VARCHAR * source_path,
    SQLUDF_VARCHAR * target_path,
    SQLUDF_CHAR    * mode,
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * source_path_ind,
    SQLUDF_NULLIND * target_path_ind,
    SQLUDF_NULLIND * mode_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS ) ;

// writes if mode="w" or appends if mode="a"
// from in_clob to path
// sets retcode to 0 on success, (-1 * __LINE__) on error
void SQL_API_FN sql_clob_to_file (
    SQLUDF_VARCHAR * path,
    SQLUDF_CHAR    * mode,
    SQLUDF_CLOB    * in_clob,
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * path_ind,
    SQLUDF_NULLIND * mode_ind,
    SQLUDF_NULLIND * in_clob_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS ) ;

// makes directory
// sets retcode to 0 on success, (-1 * __LINE__) on error
void SQL_API_FN sql_make_directory (
    SQLUDF_VARCHAR * path,
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * path_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS ) ;

// removes directory
// sets retcode to 0 on success, (-1 * __LINE__) on error
void SQL_API_FN sql_remove_directory (
    SQLUDF_VARCHAR * path,
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * path_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS ) ;

// moves directory
// sets retcode to 0 on success, (-1 * __LINE__) on error
void SQL_API_FN sql_move_directory (
    SQLUDF_VARCHAR * source_path,
    SQLUDF_VARCHAR * target_path,
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * source_path_ind,
    SQLUDF_NULLIND * target_path_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS ) ;

// makes directory
// sets retcode to 0 on success, (-1 * __LINE__) on error
void SQL_API_FN sql_sizeof_directory (
    SQLUDF_VARCHAR * path,
    SQLUDF_BIGINT  * retcode,
    SQLUDF_NULLIND * path_ind,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS ) ;

// sets retcode to 1 if windows, 0 otherwise
void SQL_API_FN sql_is_windows (
    SQLUDF_INTEGER * retcode,
    SQLUDF_NULLIND * retcode_ind,
    SQLUDF_TRAIL_ARGS ) ;

// executes command in system function
// sets retcode to return value of system function
void SQL_API_FN sql_system_call (
    SQLUDF_VARCHAR *command,
    SQLUDF_INTEGER *retcode,
    SQLUDF_NULLIND *command_ind,
    SQLUDF_NULLIND *retcode_ind,
    SQLUDF_TRAIL_ARGS ) ;


#if defined(__cplusplus)
}
#endif
