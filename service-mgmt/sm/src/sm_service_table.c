//
// Copyright (c) 2014-2018, 2026 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#include "sm_service_table.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <errno.h>

#include "sm_limits.h"
#include "sm_types.h"
#include "sm_debug.h"
#include "sm_list.h"
#include "sm_db.h"
#include "sm_db_foreach.h"
#include "sm_db_services.h"
#include "sm_db_service_instances.h"
#include "sm_service_enable.h"
#include "sm_service_disable.h"
#include "sm_service_go_active.h"
#include "sm_service_go_standby.h"
#include "sm_service_audit.h"
#include "sm_service_group_table.h"
#include "sm_service_group_member_table.h"
#include "sm_util_types.h"

static SmListT* _services = NULL;
static SmDbHandleT* _sm_db_handle = NULL;
// Mutex protecting the in-memory service list from concurrent access
// between the main event loop and the API dispatch thread.
static pthread_mutex_t _service_table_mutex;

static SmErrorT sm_service_table_add( void* user_data[], void* record );

// ****************************************************************************
// Service Table - clear failure state
// returns true if service is in a failure state
// ====================
bool sm_service_clear_failure_state(SmServiceT* service)
{
    SmErrorT error;
    bool prev_failure_condition;
    prev_failure_condition =
        service->recover ||
        service->action_fail_count > 0 ||
        service->transition_fail_count > 0 ||
        service->status == SM_SERVICE_STATUS_FAILED ||
        service->condition == SM_SERVICE_CONDITION_RECOVERY_FAILURE ||
        service->condition == SM_SERVICE_CONDITION_ACTION_FAILURE ||
        service->condition == SM_SERVICE_CONDITION_FATAL_FAILURE;
    if( prev_failure_condition )
    {
        service->recover = false;
        service->action_fail_count = 0;
        service->transition_fail_count = 0;
        service->status = SM_SERVICE_STATUS_NONE;
        service->condition = SM_SERVICE_CONDITION_NONE;

        error = sm_service_table_persist( service );
        if( SM_OKAY != error )
        {
            DPRINTFE( "Failed to persist service (%s) data, error=%s.",
                      service->name, sm_error_str(error) );
        }

        DPRINTFI( "Cleared previous failure condition for service (%s) "
                  "in % state.", service->name, sm_service_state_str(service->state) );

    }

    return prev_failure_condition;
}

// ****************************************************************************
// Service Table - Read (internal, caller must hold _service_table_mutex)
// =====================================================================
static SmServiceT* sm_service_table_read_unlocked( char service_name[] )
{
    SmListT* entry = NULL;
    SmListEntryDataPtrT entry_data;
    SmServiceT* service;

    SM_LIST_FOREACH( _services, entry, entry_data )
    {
        service = (SmServiceT*) entry_data;

        if( 0 == strcmp( service_name, service->name ) )
        {
            return( service );
        }
    }

    return( NULL );
}
// ****************************************************************************

// ****************************************************************************
// Service Table - Read
// ====================
SmServiceT* sm_service_table_read( char service_name[] )
{
    SmServiceT* service;
    int trylock_result;

    // trylock+log pattern: detect mutex contention without blocking on
    // the fast path. If contention is detected, log it then block.
    trylock_result = pthread_mutex_trylock( &_service_table_mutex );
    if( EBUSY == trylock_result )
    {
        DPRINTFI( "Mutex contention: sm_service_table_read(%s) "
                  "waiting for lock.", service_name );
        if( 0 != pthread_mutex_lock( &_service_table_mutex ) )
        {
            DPRINTFE( "Failed to capture service table mutex." );
            abort();
        }
    }
    else if( 0 != trylock_result )
    {
        DPRINTFE( "Failed to capture service table mutex." );
        abort();
    }

    service = sm_service_table_read_unlocked( service_name );

    if( 0 != pthread_mutex_unlock( &_service_table_mutex ) )
    {
        DPRINTFE( "Failed to release service table mutex." );
        abort();
    }

    return( service );
}
// ****************************************************************************

// ****************************************************************************
// Service Table - Read By Identifier
// ==================================
SmServiceT* sm_service_table_read_by_id( int64_t service_id )
{
    SmListT* entry = NULL;
    SmListEntryDataPtrT entry_data;
    SmServiceT* service;
    SmServiceT* result = NULL;

    if( 0 != pthread_mutex_lock( &_service_table_mutex ) )
    {
        DPRINTFE( "Failed to capture service table mutex." );
        abort();
    }

    SM_LIST_FOREACH( _services, entry, entry_data )
    {
        service = (SmServiceT*) entry_data;

        if( service_id == service->id )
        {
            result = service;
            break;
        }
    }

    if( 0 != pthread_mutex_unlock( &_service_table_mutex ) )
    {
        DPRINTFE( "Failed to release service table mutex." );
        abort();
    }

    return( result );
}
// ****************************************************************************

// ****************************************************************************
// Service Table - Read By Pid
// ===========================
SmServiceT* sm_service_table_read_by_pid( int pid )
{
    SmListT* entry = NULL;
    SmListEntryDataPtrT entry_data;
    SmServiceT* service;
    SmServiceT* result = NULL;

    if( 0 != pthread_mutex_lock( &_service_table_mutex ) )
    {
        DPRINTFE( "Failed to capture service table mutex." );
        abort();
    }

    SM_LIST_FOREACH( _services, entry, entry_data )
    {
        service = (SmServiceT*) entry_data;

        if( pid == service->pid )
        {
            result = service;
            break;
        }
    }

    if( 0 != pthread_mutex_unlock( &_service_table_mutex ) )
    {
        DPRINTFE( "Failed to release service table mutex." );
        abort();
    }

    return( result );
}
// ****************************************************************************

// ****************************************************************************
// Service Table - Read By Action Pid
// ==================================
SmServiceT* sm_service_table_read_by_action_pid( int pid )
{
    SmListT* entry = NULL;
    SmListEntryDataPtrT entry_data;
    SmServiceT* service;
    SmServiceT* result = NULL;

    if( 0 != pthread_mutex_lock( &_service_table_mutex ) )
    {
        DPRINTFE( "Failed to capture service table mutex." );
        abort();
    }

    SM_LIST_FOREACH( _services, entry, entry_data )
    {
        service = (SmServiceT*) entry_data;

        if( pid == service->action_pid )
        {
            result = service;
            break;
        }
    }

    if( 0 != pthread_mutex_unlock( &_service_table_mutex ) )
    {
        DPRINTFE( "Failed to release service table mutex." );
        abort();
    }

    return( result );
}
// ****************************************************************************

// ****************************************************************************
// Service Table - For Each
// ========================
void sm_service_table_foreach( void* user_data[],
    SmServiceTableForEachCallbackT callback )
{
    SmListT* entry = NULL;
    SmListEntryDataPtrT entry_data;
    int trylock_result;

    trylock_result = pthread_mutex_trylock( &_service_table_mutex );
    if( EBUSY == trylock_result )
    {
        DPRINTFI( "Mutex contention: sm_service_table_foreach waiting for lock." );
        if( 0 != pthread_mutex_lock( &_service_table_mutex ) )
        {
            DPRINTFE( "Failed to capture service table mutex." );
            abort();
        }
    }
    else if( 0 != trylock_result )
    {
        DPRINTFE( "Failed to capture service table mutex." );
        abort();
    }

    SM_LIST_FOREACH( _services, entry, entry_data )
    {
        callback( user_data, (SmServiceT*) entry_data );
    }

    if( 0 != pthread_mutex_unlock( &_service_table_mutex ) )
    {
        DPRINTFE( "Failed to release service table mutex." );
        abort();
    }
}
// ****************************************************************************

// ****************************************************************************
// Service Table - Add
// ===================
static SmErrorT sm_service_table_add( void* user_data[], void* record )
{
    SmServiceT* service;
    SmDbServiceT* db_service = (SmDbServiceT*) record;
    SmDbServiceInstanceT db_service_instance;
    SmErrorT error;
    int *count = NULL;
    if(user_data)
    {
        count = (int*)user_data[0];
        (*count) ++;
    }

    error = sm_db_service_instances_read( _sm_db_handle, db_service->name,
                                          &db_service_instance );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to read instance for service (%s), error=%s.",
                  db_service->name, sm_error_str( error ) );
        return( error );
    }

    service = sm_service_table_read_unlocked( db_service->name );
    if( NULL == service )
    {
        service = (SmServiceT*) malloc( sizeof(SmServiceT) );
        if( NULL == service )
        {
            DPRINTFE( "Failed to allocate service table entry." );
            return( SM_FAILED );
        }

        memset( service, 0, sizeof(SmServiceT) );

        service->id = db_service->id;
        snprintf( service->name, sizeof(service->name), "%s",
                  db_service->name );
        snprintf( service->instance_name, sizeof(service->instance_name),
                  "%s", db_service_instance.instance_name );
        snprintf( service->instance_params, sizeof(service->instance_params),
                  "%s", db_service_instance.instance_params );
        service->desired_state = db_service->desired_state;
        service->state = db_service->state;
        service->status = db_service->status;
        service->condition = db_service->condition;
        service->recover = false;
        service->clear_fatal_condition = false;
        service->max_failures = db_service->max_failures;
        service->fail_count = 0;
        service->fail_countdown = db_service->fail_countdown;
        service->fail_countdown_interval_in_ms
            = db_service->fail_countdown_interval_in_ms;
        service->fail_countdown_timer_id = SM_TIMER_ID_INVALID;
        service->audit_timer_id = SM_TIMER_ID_INVALID;
        service->action_running = SM_SERVICE_ACTION_NONE;
        service->action_pid = -1;
        service->action_timer_id = SM_TIMER_ID_INVALID;
        service->action_attempts = 0;
        service->action_state_timer_id = SM_TIMER_ID_INVALID;
        service->pid = -1;
        snprintf( service->pid_file, sizeof(service->pid_file), "%s",
                  db_service->pid_file );
        service->pid_file_audit_timer_id = SM_TIMER_ID_INVALID;
        service->action_fail_count = 0;
        service->max_action_failures = db_service->max_action_failures;
        service->transition_fail_count = 0;
        service->max_transition_failures = db_service->max_transition_failures;

        error = sm_service_go_active_exists( service,
                                        &service->go_active_action_exists );
        if( SM_OKAY != error )
        {
            DPRINTFE( "Failed to determine if go-active action for "
                      "service (%s) exists, error=%s.", service->name,
                      sm_error_str( error ) );
            free( service );
            return( error );
        }

        error = sm_service_go_standby_exists( service,
                                        &service->go_standby_action_exists );
        if( SM_OKAY != error )
        {
            DPRINTFE( "Failed to determine if go-standby action for service "
                      "(%s) exists, error=%s.", service->name,
                      sm_error_str( error ) );
            free( service );
            return( error );
        }

        error = sm_service_enable_exists( service,
                                        &service->enable_action_exists );
        if( SM_OKAY != error )
        {
            DPRINTFE( "Failed to determine if enable action for service "
                      "(%s) exists, error=%s.", service->name,
                      sm_error_str( error ) );
            free( service );
            return( error );
        }

        error = sm_service_disable_exists( service,
                                        &service->disable_action_exists );
        if( SM_OKAY != error )
        {
            DPRINTFE( "Failed to determine if disable action for service "
                      "(%s) exists, error=%s.", service->name,
                      sm_error_str( error ) );
            free( service );
            return( error );
        }

        error = sm_service_audit_enabled_exists( service,
                                        &service->audit_enabled_exists );
        if( SM_OKAY != error )
        {
            DPRINTFE( "Failed to determine if audit enabled action for "
                      "service (%s) exists, error=%s.", service->name,
                      sm_error_str( error ) );
            free( service );
            return( error );
        }

        error = sm_service_audit_disabled_exists( service,
                                        &service->audit_disabled_exists );
        if( SM_OKAY != error )
        {
            DPRINTFE( "Failed to determine if audit disabled action for "
                      "service (%s) exists, error=%s.", service->name,
                      sm_error_str( error ) );
            free( service );
            return( error );
        }

        service->disable_check_dependency = true;
        service->disable_skip_dependent = false;

        SM_LIST_PREPEND( _services, (SmListEntryDataPtrT) service );

    } else {
        service->id = db_service->id;
        snprintf( service->instance_name, sizeof(service->instance_name),
                  "%s", db_service_instance.instance_name );
        snprintf( service->instance_params, sizeof(service->instance_params),
                  "%s", db_service_instance.instance_params );
        service->max_failures = db_service->max_failures;
        service->fail_countdown = db_service->fail_countdown;
        service->fail_countdown_interval_in_ms
            = db_service->fail_countdown_interval_in_ms;
        service->max_action_failures = db_service->max_action_failures;
        service->max_transition_failures = db_service->max_transition_failures;
        snprintf( service->pid_file, sizeof(service->pid_file), "%s",
                  db_service->pid_file );
    }
    service->provisioned = db_service->provisioned;
    return( SM_OKAY );
}
// ****************************************************************************

SmErrorT sm_service_provision(char service_name[])
{
    SmErrorT error;
    SmDbServiceT db_service;
    SmServiceT* service;
    int trylock_result;

    // Mutex-protected provision: read + add must be atomic to prevent
    // duplicate entries from concurrent provision requests.
    trylock_result = pthread_mutex_trylock( &_service_table_mutex );
    if( EBUSY == trylock_result )
    {
        DPRINTFI( "Mutex contention: sm_service_provision(%s) "
                  "waiting for lock.", service_name );
        if( 0 != pthread_mutex_lock( &_service_table_mutex ) )
        {
            DPRINTFE( "Failed to capture service table mutex." );
            abort();
        }
    }
    else if( 0 != trylock_result )
    {
        DPRINTFE( "Failed to capture service table mutex." );
        abort();
    }

    service = sm_service_table_read_unlocked(service_name);
    if(NULL != service)
    {
        if( 0 != pthread_mutex_unlock( &_service_table_mutex ) )
        {
            DPRINTFE( "Failed to release service table mutex." );
            abort();
        }
        return SM_OKAY;
    }

    error = sm_db_services_read( _sm_db_handle, service_name, &db_service );
    if(SM_OKAY != error)
    {
        if( 0 != pthread_mutex_unlock( &_service_table_mutex ) )
        {
            DPRINTFE( "Failed to release service table mutex." );
            abort();
        }
        return error;
    }

    error = sm_service_table_add(NULL, &db_service);
    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to provision service %s, error %s", service_name, sm_error_str(error));
        if( 0 != pthread_mutex_unlock( &_service_table_mutex ) )
        {
            DPRINTFE( "Failed to release service table mutex." );
            abort();
        }
        return SM_FAILED;
    }

    service = sm_service_table_read_unlocked(service_name);
    if(NULL == service)
    {
        DPRINTFE("Service %s not found.", service_name);
        if( 0 != pthread_mutex_unlock( &_service_table_mutex ) )
        {
            DPRINTFE( "Failed to release service table mutex." );
            abort();
        }
        return SM_FAILED;
    }

    if( 0 != pthread_mutex_unlock( &_service_table_mutex ) )
    {
        DPRINTFE( "Failed to release service table mutex." );
        abort();
    }

    return SM_OKAY;
}


SmErrorT sm_service_deprovision(char service_name[])
{
    SmServiceT* service;
    int trylock_result;

    // Mutex-protected deprovision: read + remove + free must be atomic
    // to prevent use-after-free from concurrent readers.
    trylock_result = pthread_mutex_trylock( &_service_table_mutex );
    if( EBUSY == trylock_result )
    {
        DPRINTFI( "Mutex contention: sm_service_deprovision(%s) "
                  "waiting for lock.", service_name );
        if( 0 != pthread_mutex_lock( &_service_table_mutex ) )
        {
            DPRINTFE( "Failed to capture service table mutex." );
            abort();
        }
    }
    else if( 0 != trylock_result )
    {
        DPRINTFE( "Failed to capture service table mutex." );
        abort();
    }

    service = sm_service_table_read_unlocked(service_name);
    if(NULL == service)
    {
        DPRINTFI("Service %s not found in provisioned list. Already deprovisioned?", service_name);
        if( 0 != pthread_mutex_unlock( &_service_table_mutex ) )
        {
            DPRINTFE( "Failed to release service table mutex." );
            abort();
        }
        return SM_OKAY;
    }

    SM_LIST_REMOVE( _services, (SmListEntryDataPtrT) service );
    free(service);

    if( 0 != pthread_mutex_unlock( &_service_table_mutex ) )
    {
        DPRINTFE( "Failed to release service table mutex." );
        abort();
    }

    return SM_OKAY;
}

// ****************************************************************************
// Service Table - Load
// ====================
SmErrorT sm_service_table_load( void )
{
    char db_query[SM_DB_QUERY_STATEMENT_MAX_CHAR];
    SmDbServiceT service;
    SmErrorT error;
    int count = 0;
    void* user_data[] = {&count};

    if( NULL != _services )
    {
        SM_LIST_CLEANUP_ALL( _services );
        _services = NULL;
    }

    snprintf( db_query, sizeof(db_query), "%s = 'yes'",
              SM_SERVICES_TABLE_COLUMN_PROVISIONED );

    error = sm_db_foreach( SM_DATABASE_NAME, SM_SERVICES_TABLE_NAME,
                           db_query, &service, sm_db_services_convert,
                           sm_service_table_add, user_data );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to loop over services in database, error=%s.",
                  sm_error_str( error ) );
        return( error );
    }

    DPRINTFI("load %d services", count);

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Table - Persist
// =======================
SmErrorT sm_service_table_persist( SmServiceT* service )
{
    SmDbServiceT db_service;
    SmErrorT error;

    memset( &db_service, 0, sizeof(db_service) );

    db_service.id = service->id;
    db_service.provisioned = service->provisioned;
    snprintf( db_service.name, sizeof(db_service.name), "%s", service->name );
    db_service.desired_state = service->desired_state;
    db_service.state = service->state;
    db_service.status = service->status;
    db_service.condition = service->condition;
    db_service.max_failures = service->max_failures;
    db_service.fail_countdown = service->fail_countdown;
    db_service.fail_countdown_interval_in_ms
        = service->fail_countdown_interval_in_ms;
    db_service.max_action_failures = service->max_action_failures;
    db_service.max_transition_failures = service->max_transition_failures;
    snprintf( db_service.pid_file, sizeof(db_service.pid_file), "%s",
              service->pid_file );

    error = sm_db_services_update( _sm_db_handle, &db_service );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to update database, error=%s.",
                  sm_error_str( error ) );
        return( error );
    }

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service - Loop service members
// ===============================
static void _sm_loop_service_group_members( void* user_data[],
    SmServiceGroupMemberT* service_group_member )
{
    SmServiceT* service;
    service = sm_service_table_read_unlocked( service_group_member->service_name );
    if( NULL == service )
    {
        DPRINTFE( "Could not find service (%s) of "
                  "service group (%s).",
                  service_group_member->service_name,
                  service_group_member->name);
        return;
    }

    snprintf(service->group_name, sizeof(service->group_name), "%s", service_group_member->name);
}
// ****************************************************************************

// ****************************************************************************
// Service Table - Loop service groups
// =================================================
static void _sm_loop_service_groups(
    void* user_data[], SmServiceGroupT* service_group )
{
    sm_service_group_member_table_foreach_member( service_group->name,
                NULL, _sm_loop_service_group_members );
}
// ****************************************************************************

// ****************************************************************************
// Service Table - Initialize
// ==========================
SmErrorT sm_service_table_initialize( void )
{
    SmErrorT error;

    _services = NULL;

    error = sm_mutex_initialize(&_service_table_mutex, true);
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to initialize service table mutex, error=%s.",
                  sm_error_str( error ) );
        return( error );
    }

    error = sm_db_connect( SM_DATABASE_NAME, &_sm_db_handle );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to connect to database (%s), error=%s.",
                  SM_DATABASE_NAME, sm_error_str( error ) );
        return( error );
    }

    error = sm_service_table_load();
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to load services from database, error=%s.",
                  sm_error_str( error ) );
        return( error );
    }

    sm_service_group_table_foreach( NULL, _sm_loop_service_groups );

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Table - Finalize
// ========================
SmErrorT sm_service_table_finalize( void )
{
    SmErrorT error;

    SM_LIST_CLEANUP_ALL( _services );

    if( NULL != _sm_db_handle )
    {
        error = sm_db_disconnect( _sm_db_handle );
        if( SM_OKAY != error )
        {
            DPRINTFE( "Failed to disconnect from database (%s), error=%s.",
                      SM_DATABASE_NAME, sm_error_str( error ) );
        }

        _sm_db_handle = NULL;
    }

    error = sm_mutex_finalize(&_service_table_mutex);
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to finalize service table mutex, error=%s.",
                  sm_error_str( error ) );
    }

    return( SM_OKAY );
}
// ****************************************************************************
