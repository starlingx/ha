//
// Copyright (c) 2014,2023 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#include "fm_api_wrapper.h"

#include <pthread.h>

#include "sm_debug.h"
#include "sm_util_types.h"

static pthread_mutex_t fm_api_mutex;

SmErrorT fm_mutex_initialize ( void )
{
    return sm_mutex_initialize(&fm_api_mutex, false);
}

SmErrorT fm_mutex_finalize ( void )
{
    return sm_mutex_finalize(&fm_api_mutex);
}

// ****************************************************************************
// FM Wrapper - FM Set Fault
// =========================
EFmErrorT fm_set_fault_wrapper( const SFmAlarmDataT* alarm, fm_uuid_t* uuid )
{
    EFmErrorT fm_error;

    if( 0 != pthread_mutex_lock( &fm_api_mutex ) )
    {
        DPRINTFE( "Failed to capture mutex." );
        return( FM_ERR_NOCONNECT );
    }

    fm_error = fm_set_fault( alarm, uuid );

    if( 0 != pthread_mutex_unlock( &fm_api_mutex ) )
    {
        DPRINTFE( "Failed to release mutex." );
    }

    return( fm_error );
}
// ****************************************************************************

// ****************************************************************************
// FM Wrapper - FM Clear Fault
// ===========================
EFmErrorT fm_clear_fault_wrapper( AlarmFilter* filter )
{
    EFmErrorT fm_error;

    if( 0 != pthread_mutex_lock( &fm_api_mutex ) )
    {
        DPRINTFE( "Failed to capture mutex." );
        return( FM_ERR_NOCONNECT );
    }

    fm_error = fm_clear_fault( filter );

    if( 0 != pthread_mutex_unlock( &fm_api_mutex ) )
    {
        DPRINTFE( "Failed to release mutex." );
    }

    return( fm_error );
}
// ****************************************************************************

// ****************************************************************************
// FM Wrapper - FM Clear All
// =========================
EFmErrorT fm_clear_all_wrapper( fm_ent_inst_t* inst_id )
{
    EFmErrorT fm_error;

    if( 0 != pthread_mutex_lock( &fm_api_mutex ) )
    {
        DPRINTFE( "Failed to capture mutex." );
        return( FM_ERR_NOCONNECT );
    }

    fm_error = fm_clear_all( inst_id );

    if( 0 != pthread_mutex_unlock( &fm_api_mutex ) )
    {
        DPRINTFE( "Failed to release mutex." );
    }

    return( fm_error );
}
// ****************************************************************************

// ****************************************************************************
// FM Wrapper - FM Get Fault
// =========================
EFmErrorT fm_get_fault_wrapper( AlarmFilter* filter, SFmAlarmDataT* alarm )
{
    EFmErrorT fm_error;

    if( 0 != pthread_mutex_lock( &fm_api_mutex ) )
    {
        DPRINTFE( "Failed to capture mutex." );
        return( FM_ERR_NOCONNECT );
    }

    fm_error = fm_get_fault( filter, alarm );

    if( 0 != pthread_mutex_unlock( &fm_api_mutex ) )
    {
        DPRINTFE( "Failed to release mutex." );
    }

    return( fm_error );
}
// ****************************************************************************

// ****************************************************************************
// FM Wrapper - FM Get Faults
// ==========================
EFmErrorT fm_get_faults_wrapper( fm_ent_inst_t* inst_id, SFmAlarmDataT* alarm,
    unsigned int* max_alarms_to_get )
{
    EFmErrorT fm_error;

    if( 0 != pthread_mutex_lock( &fm_api_mutex ) )
    {
        DPRINTFE( "Failed to capture mutex." );
        return( FM_ERR_NOCONNECT );
    }

    fm_error = fm_get_faults( inst_id, alarm, max_alarms_to_get );

    if( 0 != pthread_mutex_unlock( &fm_api_mutex ) )
    {
        DPRINTFE( "Failed to release mutex." );
    }

    return( fm_error );
}
// ****************************************************************************

// ****************************************************************************
// FM Wrapper - FM Get Faults By Id
// ================================
EFmErrorT fm_get_faults_by_id_wrapper( fm_alarm_id* alarm_id,
    SFmAlarmDataT* alarm, unsigned int* max_alarms_to_get )
{
    EFmErrorT fm_error;

    if( 0 != pthread_mutex_lock( &fm_api_mutex ) )
    {
        DPRINTFE( "Failed to capture mutex." );
        return( FM_ERR_NOCONNECT );
    }

    fm_error = fm_get_faults_by_id( alarm_id, alarm, max_alarms_to_get );

    if( 0 != pthread_mutex_unlock( &fm_api_mutex ) )
    {
        DPRINTFE( "Failed to release mutex." );
    }

    return( fm_error );
}
// ****************************************************************************

