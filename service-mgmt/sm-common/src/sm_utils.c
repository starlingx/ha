//
// Copyright (c) 2014 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#include "sm_utils.h"

#include "sm_types.h"
#include "sm_debug.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <signal.h>
#include <sys/stat.h>

// ****************************************************************************
// Utils - Process Running
// =======================
bool sm_utils_process_running( const char* pid_filename )
{
    FILE *fp;
    int result;
    bool running = true;

    fp = fopen( pid_filename, "r" );
    if( NULL == fp )
    {
        running = false;
    } else {
        int pid;

        fscanf( fp, "%d", &pid );
        if( pid != getpid() )
        {
            result = kill( pid, 0 );
            if(( 0 > result )&&( ESRCH == errno ))
            {
                running = false;
            }
        }
        fclose( fp );
    }

    return( running );
}
// ****************************************************************************

// ****************************************************************************
// Utils - Set Pid File
// ====================
bool sm_utils_set_pid_file( const char* pid_filename )
{
    FILE *fp = fopen( pid_filename, "w" );
    if( NULL != fp )
    {
        fprintf( fp, "%i\n", (int) getpid() );
        fclose( fp );
        return( true );
    } 
    return( false );
}
// ****************************************************************************

// ****************************************************************************
// Utils - Boot Complete
// =====================
bool sm_utils_boot_complete( void )
{
    if( 0 > access( SM_BOOT_COMPLETE_FILENAME,  F_OK ) )
    {
        return( false );
    }

    return( true );
}
// ****************************************************************************

// ****************************************************************************
// Utils - Set Boot Complete
// =========================
SmErrorT sm_utils_set_boot_complete( void )
{
    int fd = open( SM_BOOT_COMPLETE_FILENAME, O_RDWR | O_CREAT, 
                   S_IRUSR | S_IRGRP | S_IROTH | O_CLOEXEC );
    if( 0 > fd )
    {
        DPRINTFE( "Failed to set boot complete, error=%s.", strerror(errno) );
        return( SM_FAILED );
    }

    close( fd );
    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Utils - Indicate Degraded
// =========================
SmErrorT sm_utils_indicate_degraded( void )
{
    int fd = open( SM_INDICATE_DEGRADED_FILENAME, O_RDWR | O_CREAT,
                   S_IRUSR | S_IRGRP | S_IROTH | O_CLOEXEC );
    if( 0 > fd )
    {
        DPRINTFE( "Failed to indicate degraded, error=%s.", strerror(errno) );
        return( SM_FAILED );
    }

    close( fd );
    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Utils - Clear Degraded
// ======================
SmErrorT sm_utils_clear_degraded( void )
{
    unlink( SM_INDICATE_DEGRADED_FILENAME );
    return( SM_OKAY );
}
// ****************************************************************************
