//
// Copyright (c) 2018,2023 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#include <pthread.h>
#include <stdlib.h>
#include "sm_util_types.h"
#include "sm_debug.h"

SmErrorT sm_mutex_initialize ( pthread_mutex_t* mutex, bool mutex_recursive )
{
    SmErrorT error = SM_OKAY;
    pthread_mutexattr_t attr;
    if(mutex)
    {
        pthread_mutexattr_init(&attr);
        if(mutex_recursive)
        {
            pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE);
        }
        pthread_mutexattr_setprotocol( &attr, PTHREAD_PRIO_INHERIT);
        int res = pthread_mutex_init(mutex, &attr);
        if( res != 0 )
        {
            DPRINTFE("Failed to initialize mutex, error %d", res);
            error = SM_FAILED;
        }
    }
    else
    {
        DPRINTFE("Failed to initialize mutex, NULL ptr");
        error = SM_FAILED;
    }
    return error;
}

SmErrorT sm_mutex_finalize ( pthread_mutex_t* mutex )
{
    SmErrorT error = SM_OKAY;
    if(mutex)
    {
        int res = pthread_mutex_destroy(mutex);
        if( res != 0 )
        {
            DPRINTFE("Failed to destroy mutex, error %d", res);
            error = SM_FAILED;
        }
    }
    else
    {
        DPRINTFE("Failed to destroy mutex, NULL ptr");
        error = SM_FAILED;
    }
    return error;
}

mutex_holder::mutex_holder(pthread_mutex_t* mutex)
{
    this->m_mutex = mutex;
    if( 0 != pthread_mutex_lock( this->m_mutex ) )
    {
        DPRINTFE("Critical error, failed to obtain the mutex. Quit...");
        abort();
    }
}

mutex_holder::~mutex_holder()
{
    if( 0 != pthread_mutex_unlock( this->m_mutex ) )
    {
        DPRINTFE( "Failed to release mutex." );
    }
}
