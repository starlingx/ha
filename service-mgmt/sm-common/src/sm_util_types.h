//
// Copyright (c) 2018,2023 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#ifndef __SM_UTIL_TYPES_H__
#define __SM_UTIL_TYPES_H__

#include <stdbool.h>
#include <pthread.h>
#include "sm_types.h"

class mutex_holder
{
    private:
        pthread_mutex_t* m_mutex;
    public:
        mutex_holder(pthread_mutex_t* mutex);
        virtual ~mutex_holder();
};

// ****************************************************************************
// initialize mutex
// ==============
SmErrorT sm_mutex_initialize ( pthread_mutex_t* mutex, bool mutex_recursive );
// ****************************************************************************

// ****************************************************************************
// destroy mutex
// ==============
SmErrorT sm_mutex_finalize ( pthread_mutex_t* mutex );
// ****************************************************************************

#endif //__SM_UTIL_TYPES_H__