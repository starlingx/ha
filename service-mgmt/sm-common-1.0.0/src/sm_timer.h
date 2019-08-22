//
// Copyright (c) 2014 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
// The following module is thread safe.
//
#ifndef __SM_TIMER_H__
#define __SM_TIMER_H__

#include <stdint.h>
#include <stdio.h>
#include <stdbool.h>

#include "sm_types.h"

#ifdef __cplusplus
extern "C" {
#endif

#define SM_TIMER_ID_INVALID -1 

typedef int64_t SmTimerIdT;

typedef bool (*SmTimerCallbackT) (SmTimerIdT timer_id, int64_t user_data );

// ****************************************************************************
// Timer - Register
// ================
extern SmErrorT _sm_timer_register( const char name[], unsigned int ms,
    SmTimerCallbackT callback, int64_t user_data, SmTimerIdT* timer_id,
    const char* func, const char* file, int line);
// ****************************************************************************

// ****************************************************************************
// Timer - Deregister
// ==================
extern SmErrorT _sm_timer_deregister( SmTimerIdT timer_id,
    const char* func, const char* file, int line );
// ****************************************************************************

#define sm_timer_register( name, ms, callback, user_data, timer_id) \
    _sm_timer_register( name, ms, callback, user_data, timer_id, __FUNCTION__, __FILE__, __LINE__ )

#define sm_timer_deregister( timer_id ) \
    _sm_timer_deregister( timer_id, __FUNCTION__, __FILE__, __LINE__ )

// ****************************************************************************
// Timer - Scheduling On Time
// ==========================
extern bool sm_timer_scheduling_on_time( void );
// ****************************************************************************

// ****************************************************************************
// Timer - Scheduling On Time In Period
// ====================================
extern bool sm_timer_scheduling_on_time_in_period( unsigned int period_in_ms );
// ****************************************************************************

// ****************************************************************************
// Timer - Dump Data
// =================
extern void sm_timer_dump_data( FILE* log );
// ****************************************************************************

// ****************************************************************************
// Timer - Initialize
// ==================
extern SmErrorT sm_timer_initialize( unsigned int tick_timer_in_ms );
// ****************************************************************************

// ****************************************************************************
// Timer - Finalize
// ================
extern SmErrorT sm_timer_finalize( void );
// ****************************************************************************

#ifdef __cplusplus
}
#endif

#endif // __SM_TIMER_H__
