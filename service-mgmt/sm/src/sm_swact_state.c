// Copyright (c) 2017,2023 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#include "sm_swact_state.h"
#include "pthread.h"
#include "sm_debug.h"
#include "sm_util_types.h"

volatile SmSwactStateT _swact_state = SM_SWACT_STATE_NONE;
static pthread_mutex_t swact_state_mutex;

SmErrorT sm_swact_state_mutex_initialize ( void )
{
    return sm_mutex_initialize(&swact_state_mutex, false);
}

SmErrorT sm_swact_state_mutex_finalize ( void )
{
    return sm_mutex_finalize(&swact_state_mutex);
}

// ****************************************************************************
// Swact State - Swact State Setter
// ============================================
void sm_set_swact_state(SmSwactStateT state)
{
    // The state is set by sm main thread and task affining thread.
    pthread_mutex_lock(&swact_state_mutex);
     _swact_state = state;
    pthread_mutex_unlock(&swact_state_mutex);
}

// ****************************************************************************
// Swact State - Swact State Getter
// ============================================
SmSwactStateT sm_get_swact_state( void )
{
    return _swact_state;
}
