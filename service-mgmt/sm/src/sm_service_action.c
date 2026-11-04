//
// Copyright (c) 2014, 2026 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#include "sm_service_action.h"

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/resource.h>

#include "sm_types.h"
#include "sm_debug.h"
#include "sm_sha512.h"
#include "sm_service_action_table.h"
#include "sm_service_action_result_table.h"

#define SM_SERVICE_ACTION_VALIDATE_TIMER_IN_MS              60000

// A composed systemd template instance unit name ("<base>@<instance>.service")
// can be longer than PLUGIN_NAME alone, since the instance token comes from
// the much larger PLUGIN_PARAMETERS field. Size the composition buffer with
// headroom for the '@', ".service" suffix, and a reasonable instance token.
#define SM_SERVICE_ACTION_SYSD_UNIT_NAME_MAX_CHAR \
    (SM_SERVICE_ACTION_PLUGIN_NAME_MAX_CHAR + 40)

// Forward declarations
static bool sm_service_action_get_systemd_unit_path( char unit_file[],
    char path[], size_t path_size );

static bool sm_service_action_systemd_template_instance(
    const char plugin_name[], const char instance[], char unit[],
    size_t unit_size );

// ****************************************************************************
// Service Action - Validate
// =========================
/**
 * @brief Recompute the plugin file hash and detect if the plugin changed on
 *        disk since the last validation. Best-effort and rate-limited by
 *        SM_SERVICE_ACTION_VALIDATE_TIMER_IN_MS; does nothing if too little
 *        time has elapsed or the plugin file cannot be read.
 *
 * @param[in,out] action_data  Action whose plugin is validated; its stored
 *                             hash and last-validate timestamp are updated.
 */
static void sm_service_action_validate( SmServiceActionDataT* action_data )
{
    int bytes;
    FILE* fp;
    long ms_expired;
    unsigned char data[2048];
    SmSha512HashT hash;
    SmSha512ContextT context;
    char plugin_exec[SM_SERVICE_ACTION_PLUGIN_EXEC_MAX_CHAR];

    ms_expired = sm_time_get_elapsed_ms( &(action_data->last_hash_validate) );
    if( ms_expired < SM_SERVICE_ACTION_VALIDATE_TIMER_IN_MS  )
    {
        DPRINTFD( "Not enough time has elapsed, since last validate." );
        return;
    }

    sm_time_get( &(action_data->last_hash_validate) );

    if( 0 == strcmp( SM_SERVICE_ACTION_PLUGIN_TYPE_LSB_SCRIPT,
                     action_data->plugin_type ) )
    {
        snprintf( plugin_exec, sizeof(plugin_exec), "%s/%s",
                  SM_SERVICE_ACTION_PLUGIN_TYPE_LSB_DIR,
                  action_data->plugin_name );

    } else if( 0 == strcmp( SM_SERVICE_ACTION_PLUGIN_TYPE_OCF_SCRIPT,
                            action_data->plugin_type ) )
    {
        snprintf( plugin_exec, sizeof(plugin_exec), "%s/%s/%s",
                  SM_SERVICE_ACTION_PLUGIN_TYPE_OCF_PLUGIN_DIR,
                  action_data->plugin_class, action_data->plugin_name );
    } else if( ( 0 == strcmp( SM_SERVICE_ACTION_PLUGIN_TYPE_SYSD_SCRIPT,
                     action_data->plugin_type ) ) ||
               ( 0 == strcmp( SM_SERVICE_ACTION_PLUGIN_TYPE_SYSD_TEMPLATE,
                     action_data->plugin_type ) ) )
    {
        // Gets the on-disk unit file pathname
        (void) sm_service_action_get_systemd_unit_path(
                   action_data->plugin_name, plugin_exec,
                   sizeof(plugin_exec) );
    } else {
        snprintf( plugin_exec, sizeof(plugin_exec), "%s",
                  action_data->plugin_name );
    }

    fp = fopen( plugin_exec, "rb" );
    if( NULL == fp )
    {
        DPRINTFE( "Failed to open file (%s).", plugin_exec );
        return;
    }

    sm_sha512_initialize( &context );

    while( 0 != (bytes = fread( data, 1, 2048, fp )) )
    {
        sm_sha512_update( &context, data, bytes );
    }

    sm_sha512_finalize( &context, &hash );

    if( 0 != memcmp( &(action_data->hash.bytes[0]), &(hash.bytes[0]),
                     SM_SHA512_HASH_SIZE ) )
    {
        char was_hash_str[SM_SHA512_HASH_STR_SIZE];
        char now_hash_str[SM_SHA512_HASH_STR_SIZE];

        sm_sha512_hash_str( was_hash_str, &(action_data->hash) );
        sm_sha512_hash_str( now_hash_str, &hash );

        DPRINTFI( "Plugin (%s) has been changed, was=%s, now=%s.",
                  plugin_exec, was_hash_str, now_hash_str );

        memcpy( &(action_data->hash), &hash, sizeof(hash) );
    }

    fclose( fp );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Exist
// ======================
/**
 * @brief Check whether the given action is defined for the service.
 *
 * @param[in] service_name  Service name.
 * @param[in] action        Action to look up.
 *
 * @return SM_OKAY if the action exists; SM_NOT_FOUND otherwise.
 */
SmErrorT sm_service_action_exist( char service_name[], SmServiceActionT action )
{
    SmServiceActionDataT* action_data;

    action_data = sm_service_action_table_read( service_name, action );
    if( NULL == action_data )
    {
        DPRINTFD( "Service (%s) action (%s) does not exist.", service_name,
                  sm_service_action_str( action ) );
        return( SM_NOT_FOUND );
    }

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Interval
// =========================
/**
 * @brief Get the audit interval for the given action, in milliseconds.
 *
 * @param[in]  service_name    Service name.
 * @param[in]  action          Action to look up.
 * @param[out] interval_in_ms  Interval in milliseconds (0 if not found).
 *
 * @return SM_OKAY if the action exists; SM_NOT_FOUND otherwise.
 */
SmErrorT sm_service_action_interval( char service_name[],
    SmServiceActionT action, int* interval_in_ms )
{
    SmServiceActionDataT* action_data;

    *interval_in_ms = 0;

    action_data = sm_service_action_table_read( service_name, action );
    if( NULL == action_data )
    {
        DPRINTFD( "Service (%s) action (%s) does not exist.", service_name,
                  sm_service_action_str( action ) );
        return( SM_NOT_FOUND );
    }

    *interval_in_ms = action_data->interval_in_secs * 1000;

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Maximum Retries
// ================================
/**
 * @brief Get the configured retry limits for the given action.
 *
 * @param[in]  service_name         Service name.
 * @param[in]  action               Action to look up.
 * @param[out] max_failure_retries  Max retries on failure (0 if not found).
 * @param[out] max_timeout_retries  Max retries on timeout (0 if not found).
 * @param[out] max_total_retries    Max total retries (0 if not found).
 *
 * @return SM_OKAY if the action exists; SM_NOT_FOUND otherwise.
 */
SmErrorT sm_service_action_max_retries( char service_name[],
    SmServiceActionT action, int* max_failure_retries,
    int* max_timeout_retries, int* max_total_retries )
{
    SmServiceActionDataT* action_data;

    *max_failure_retries = 0;
    *max_timeout_retries = 0;
    *max_total_retries = 0;

    action_data = sm_service_action_table_read( service_name, action );
    if( NULL == action_data )
    {
        DPRINTFD( "Service (%s) action (%s) does not exist.", service_name,
                  sm_service_action_str( action ) );
        return( SM_NOT_FOUND );
    }

    *max_failure_retries = action_data->max_failure_retries;
    *max_timeout_retries = action_data->max_timeout_retries;
    *max_total_retries   = action_data->max_total_retries;

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Plugin Result
// ==============================
/**
 * @brief Map a plugin result to an action result via the result table,
 *        trying progressively broader keys: exact exit code, then "other"
 *        exit code, then "default" plugin command, then "default" command with
 *        "other" exit code.
 *
 * @param[in]  service_name      Service name (for logging).
 * @param[in]  action            Action (for logging).
 * @param[in]  plugin_type       Plugin type key.
 * @param[in]  plugin_name       Plugin name key.
 * @param[in]  plugin_command    Plugin command key.
 * @param[in]  plugin_exit_code  Plugin exit code key.
 * @param[out] action_result     Matched result-table entry, if found.
 *
 * @return SM_OKAY if a matching entry was found; SM_NOT_FOUND otherwise.
 */
static SmErrorT sm_service_action_plugin_result( char service_name[],
    SmServiceActionT action, char plugin_type[], char plugin_name[],
    char plugin_command[], char plugin_exit_code[],
    SmServiceActionResultDataT** action_result )
{
    char plugin_command_default[] = "default";
    char plugin_exit_code_other[] = "other";

    // Map the plugin result to an action result with the given data.
    *action_result = sm_service_action_result_table_read( plugin_type,
                        plugin_name, plugin_command, plugin_exit_code );
    if( NULL != *action_result )
    {
        DPRINTFD( "Read service (%s) action (%s) plugin (%s, %s, %s, %s) data.",
                  service_name, sm_service_action_str( action ), plugin_type,
                  plugin_name, plugin_command, plugin_exit_code );
        return( SM_OKAY );
    }

    // Map the plugin result to an action result with the plugin exit
    // code set to "other".
    *action_result = sm_service_action_result_table_read( plugin_type,
                        plugin_name, plugin_command, plugin_exit_code_other );
    if( NULL != *action_result )
    {
        DPRINTFD( "Read service (%s) action (%s) plugin (%s, %s, %s, other) "
                  "data.", service_name, sm_service_action_str( action ),
                  plugin_type, plugin_name, plugin_command );
        return( SM_OKAY );
    }

    // Map the plugin result to an action result with the plugin command
    // set to "default".
    *action_result = sm_service_action_result_table_read( plugin_type,
                        plugin_name, plugin_command_default, plugin_exit_code );
    if( NULL != *action_result )
    {
        DPRINTFD( "Read service (%s) action (%s) plugin (%s, %s, default, %s) "
                  "data.", service_name, sm_service_action_str( action ),
                  plugin_type, plugin_name, plugin_exit_code );
        return( SM_OKAY );
    }

    // Map the plugin result to an action result with the plugin
    // command set to "default" and the plugin exit code set to "other".
    *action_result = sm_service_action_result_table_read( plugin_type,
                        plugin_name, plugin_command_default, 
                        plugin_exit_code_other );
    if( NULL != *action_result )
    {
        DPRINTFD( "Read service (%s) action (%s) plugin "
                  "(%s, %s, default, other) data.", service_name,
                  sm_service_action_str( action ), plugin_type, plugin_name );
        return( SM_OKAY );
    }

    return( SM_NOT_FOUND );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Result
// =======================
/**
 * @brief Translate a plugin exit code into the action result and resulting
 *        service state/status/condition, using the result table (with a
 *        fallback to the "default" plugin name). Special exit codes map to
 *        "plugin-failure"/"plugin-timeout" keys.
 *
 * @param[in]  exit_code          Plugin exit code (or a special SM code).
 * @param[in]  service_name       Service name.
 * @param[in]  action             Action that was run.
 * @param[out] action_result      Resulting action result.
 * @param[out] service_state      Resulting service state.
 * @param[out] service_status     Resulting service status.
 * @param[out] service_condition  Resulting service condition.
 * @param[out] reason_text        Reason text (currently cleared to empty).
 *
 * @return SM_OKAY on success; SM_NOT_FOUND if the action is unknown; an error
 *         code on lookup failure.
 */
SmErrorT sm_service_action_result( int exit_code, char service_name[],
    SmServiceActionT action, SmServiceActionResultT* action_result,
    SmServiceStateT* service_state, SmServiceStatusT* service_status,
    SmServiceConditionT* service_condition, char reason_text[] )
{
    char plugin_name_default[] = "default";
    char plugin_exit_code[SM_SERVICE_ACTION_PLUGIN_EXIT_CODE_MAX_CHAR];
    SmServiceActionDataT* action_data;
    SmServiceActionResultDataT* result;
    SmErrorT error;

    reason_text[0] = '\0';

    if( SM_SERVICE_ACTION_PLUGIN_FAILURE == exit_code )
    {
        snprintf( plugin_exit_code, sizeof(plugin_exit_code), 
                  "plugin-failure" );

    } else if( SM_SERVICE_ACTION_PLUGIN_TIMEOUT == exit_code ) {
        snprintf( plugin_exit_code, sizeof(plugin_exit_code), 
                  "plugin-timeout" );
    } else {
        snprintf( plugin_exit_code, sizeof(plugin_exit_code),
                  "%i", exit_code );
    }

    *action_result = SM_SERVICE_ACTION_RESULT_UNKNOWN;
    *service_state = SM_SERVICE_STATE_UNKNOWN;
    *service_status = SM_SERVICE_STATUS_UNKNOWN;
    *service_condition = SM_SERVICE_CONDITION_UNKNOWN;

    action_data = sm_service_action_table_read( service_name, action );
    if( NULL == action_data )
    {
        DPRINTFD( "Service (%s) action (%s) does not exist.", service_name,
                  sm_service_action_str( action ) );
        return( SM_NOT_FOUND );
    }

    error = sm_service_action_plugin_result( service_name, action,
                action_data->plugin_type, action_data->plugin_name,
                action_data->plugin_command, plugin_exit_code, &result );
    if( SM_OKAY == error )
    {
        *action_result = result->action_result;
        *service_state = result->service_state;
        *service_status = result->service_status;
        *service_condition = result->service_condition;
        return( SM_OKAY );

    } else if(( SM_OKAY != error )&&( SM_NOT_FOUND != error )) {
        DPRINTFE( "Failed to read service (%s) action (%s) plugin result "
                  "data, error=%s.", service_name, 
                  sm_service_action_str( action ), sm_error_str( error ) );
        return( error );
    }

    error = sm_service_action_plugin_result( service_name, action,
                action_data->plugin_type, plugin_name_default,
                action_data->plugin_command, plugin_exit_code, &result );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to read service (%s) action (%s) plugin result "
                  "data, error=%s.", service_name, 
                  sm_service_action_str( action ), sm_error_str( error ) );
        return( error );
    }

    *action_result = result->action_result;
    *service_state = result->service_state;
    *service_status = result->service_status;
    *service_condition = result->service_condition;

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Abort
// ======================
/**
 * @brief Abort a running action by killing its process group (falling back to
 *        the single pid). A process group is used so child processes (sleep,
 *        drbdadm) are also terminated.
 *
 * @param[in] service_name  Service name (for logging).
 * @param[in] process_id    Pid of the action process to abort.
 *
 * @return SM_OKAY if the process was killed or already gone; SM_FAILED on an
 *         invalid pid or kill error.
 */
SmErrorT sm_service_action_abort( char service_name[], int process_id )
{
//
//TODO: Verify the process we are about to abort is the process we expect.
//
    if( -1 == process_id )
    {
        DPRINTFE( "Trying to abort a process (%i) for service (%s), "
                  "but pid is invalid.", process_id, service_name );
        return( SM_FAILED );
    }

    if( process_id == (int) getpid() )
    {
        DPRINTFE( "Trying to abort a process (%i) for service (%s), "
                  "but pid is self.", process_id, service_name );
        return( SM_FAILED );
    }

    DPRINTFI( "Aborting service (%s) with kill signal, pid=%i.",
              service_name, process_id );

    // Kill the entire process group to ensure child processes (sleep,
    // drbdadm) are also terminated.  The child calls setpgid(0,0) so
    // its PGID equals its PID.
    if( 0 > kill( -process_id, SIGKILL ) )
    {
        if( ESRCH == errno )
        {
            DPRINTFD( "Service (%s) action process group not running, "
                      "trying single pid.", service_name );
            // Fallback: try killing just the leader process in case the
            // process group no longer exists but the process does.
            if( 0 > kill( process_id, SIGKILL ) )
            {
                if( ESRCH == errno )
                {
                    DPRINTFD( "Service (%s) action not running.",
                              service_name );
                    return( SM_OKAY );
                } else {
                    DPRINTFE( "Failed to send kill signal to service (%s), "
                              "error=%s.", service_name, strerror( errno ) );
                    return( SM_FAILED );
                }
            }
        } else {
            DPRINTFE( "Failed to send kill signal to service (%s) process "
                      "group, error=%s.", service_name, strerror( errno ) );
            return( SM_FAILED );
        }
    }

    DPRINTFD( "Kill signal sent to service (%s).", service_name );

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Setup Instance Environment Variables
// =====================================================
/**
 * @brief Set the per-instance environment variables for the plugin, including
 *        the OCF_RA_VERSION_* variables and OCF_RESKEY_* parameters parsed
 *        from the instance parameters (key=value list).
 *
 * @param[in] instance_name    Instance name.
 * @param[in] instance_params  Instance parameters ("key=value" list).
 * @param[in] action_data      Action being run (plugin type/params).
 *
 * @return SM_OKAY on success; SM_FAILED if an environment variable could not
 *         be set.
 */
static SmErrorT sm_service_action_setup_instance_env_vars( char instance_name[],
    char instance_params[], SmServiceActionDataT* action_data )
{
    char looking_for = '=';
    char key_storage[SM_SERVICE_INSTANCE_PARAMS_MAX_CHAR+32];
    char value_storage[SM_SERVICE_INSTANCE_PARAMS_MAX_CHAR+32];
    char* key = NULL;
    char* value = NULL;
    char* param = NULL;

    if( 0 == strcmp( SM_SERVICE_ACTION_PLUGIN_TYPE_OCF_SCRIPT,
                     action_data->plugin_type ) )
    {
        if( 0 > setenv( "OCF_RA_VERSION_MAJOR", 
                        SM_SERVICE_ACTION_PLUGIN_TYPE_OCF_VERSION, 1 ) )
        {
            DPRINTFE( "Failed to set environment variable "
                      "(OCF_RA_VERSION_MAJOR), error=%s.", strerror( errno ) );
            goto ERROR;
        }

        if( 0 > setenv( "OCF_RA_VERSION_MINOR", 
                        SM_SERVICE_ACTION_PLUGIN_TYPE_OCF_REVISION, 1 ) )
        {
            DPRINTFE( "Failed to set environment variable "
                      "(OCF_RA_VERSION_MINOR), error=%s.", strerror( errno ) );
            goto ERROR;
        }

        if( 0 > setenv( "OCF_ROOT",
                        SM_SERVICE_ACTION_PLUGIN_TYPE_OCF_DIR, 1 ) )
        {
            DPRINTFE( "Failed to set environment variable "
                      "(OCF_ROOT), error=%s.", strerror( errno ) );
            goto ERROR;
        }

        if( 0 > setenv( "OCF_RESOURCE_INSTANCE", instance_name, 1 ) )
        {
            DPRINTFE( "Failed to set environment variable "
                      "(OCF_RESOURCE_INSTANCE), error=%s.", strerror( errno ) );
            goto ERROR;
        }

        if( 0 > setenv( "OCF_RESOURCE_TYPE",
                        action_data->plugin_name, 1 ) )
        {
            DPRINTFE( "Failed to set environment variable "
                      "(OCF_RESOURCE_TYPE), error=%s.", strerror( errno ) );
            goto ERROR;
        }
    }

    param = &(value_storage[sizeof(value_storage)-1]);
    *param = '\0'; --param;

    int char_i;
    for( char_i=strlen(instance_params)-1; 0 <= char_i; --char_i )
    {
        if( looking_for == instance_params[char_i] )
        {
            if( ',' == looking_for )
            {
                key = param+1;

                if( 0 == strcmp( SM_SERVICE_ACTION_PLUGIN_TYPE_OCF_SCRIPT,
                                 action_data->plugin_type ) )
                {
                    key -= strlen("OCF_RESKEY_");
                    memcpy( key, "OCF_RESKEY_", strlen("OCF_RESKEY_") );
                }

                DPRINTFD( "%s set environment: %s=%s", instance_name, key,
                          value );

                if( 0 > setenv( key, value, 1 ) )
                {
                    DPRINTFE( "Failed to set environment variable (%s=%s), "
                              "error=%s.", key, value, strerror( errno ) );
                    goto ERROR;
                }
           
                key = NULL;
                value = NULL;
                param = &(value_storage[sizeof(value_storage)-1]);
                *param = '\0'; --param;
                looking_for = '=';

            } else {
                key = NULL;
                value = param+1;
                param = &(key_storage[sizeof(key_storage)-1]);
                *param = '\0'; --param;
                looking_for = ',';
            }
        } else {
            *param = instance_params[char_i];
            --param;
        }
    }

    if( NULL != value )
    {
        key = param+1;

        if( 0 == strcmp( SM_SERVICE_ACTION_PLUGIN_TYPE_OCF_SCRIPT,
                         action_data->plugin_type ) )
        {
            key -= strlen("OCF_RESKEY_");
            memcpy( key, "OCF_RESKEY_", strlen("OCF_RESKEY_") );
        }

        DPRINTFD( "%s set environment: %s=%s", instance_name, key,
                  value );

        if( 0 > setenv( key, value, 1 ) )
        {
            DPRINTFE( "Failed to set environment variable (%s=%s), "
                      "error=%s.", key, value, strerror( errno ) );
            goto ERROR;
        }
    }

    return( SM_OKAY );

ERROR:
    return( SM_FAILED );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Setup Plugin Environment Variables
// ===================================================
/**
 * @brief Set the plugin-level environment variables derived from the action's
 *        plugin parameters.
 *
 * @param[in] action_data  Action being run (plugin parameters).
 *
 * @return SM_OKAY on success; SM_FAILED if an environment variable could not
 *         be set.
 */
static SmErrorT sm_service_action_setup_plugin_env_vars(
    SmServiceActionDataT* action_data )
{
    char looking_for = '=';
    char key_storage[SM_SERVICE_ACTION_PLUGIN_PARAMS_MAX_CHAR+32];
    char value_storage[SM_SERVICE_ACTION_PLUGIN_PARAMS_MAX_CHAR+32];
    char* key = NULL;
    char* value = NULL;
    char* param = NULL;

    if( 0 == strcmp( SM_SERVICE_ACTION_PLUGIN_TYPE_LSB_SCRIPT,
                     action_data->plugin_type ) )
    {
        if( 0 > setenv( "SYSTEMCTL_SKIP_REDIRECT", "1", 1 ) )
        {
            DPRINTFE( "Failed to set environment variable "
                      "(SYSTEMCTL_SKIP_REDIRECT), error=%s.",
                      strerror( errno ) );
            goto ERROR;
        }

    } else if( 0 == strcmp( SM_SERVICE_ACTION_PLUGIN_TYPE_OCF_SCRIPT,
                            action_data->plugin_type ) )
    {
        if( 0 > setenv( "HA_LOGFACILITY", "daemon", 1 ) )
        {
            DPRINTFE( "Failed to set environment variable (HA_LOGFACILITY), "
                      "error=%s.", strerror( errno ) );
            goto ERROR;
        }
    }

    param = &(value_storage[sizeof(value_storage)-1]);
    *param = '\0'; --param;

    int char_i;
    for( char_i=strlen(action_data->plugin_params)-1; 0 <= char_i; --char_i )
    {
        if( looking_for == action_data->plugin_params[char_i] )
        {
            if( ',' == looking_for )
            {
                key = param+1;

                if( 0 == strcmp( SM_SERVICE_ACTION_PLUGIN_TYPE_OCF_SCRIPT,
                                 action_data->plugin_type ) )
                {
                    key -= strlen("OCF_RESKEY_CRM_meta_");
                    memcpy( key, "OCF_RESKEY_CRM_meta_",
                            strlen("OCF_RESKEY_CRM_meta_") );
                }

                DPRINTFD( "%s set environment: %s=%s", 
                          action_data->service_name, key, value );

                if( 0 > setenv( key, value, 1 ) )
                {
                    DPRINTFE( "Failed to set environment variable (%s=%s), "
                              "error=%s.", key, value, strerror( errno ) );
                    goto ERROR;
                }

                param = &(value_storage[sizeof(value_storage)-1]);
                *param = '\0'; --param;
                looking_for = '=';

            } else {
                value = param+1;
                param = &(key_storage[sizeof(key_storage)-1]);
                *param = '\0'; --param;
                looking_for = ',';
            }
        } else {
            *param = action_data->plugin_params[char_i];
            --param;
        }
    }

    if( NULL != value )
    {
        key = param+1;

        if( 0 == strcmp( SM_SERVICE_ACTION_PLUGIN_TYPE_OCF_SCRIPT,
                         action_data->plugin_type ) )
        {
            key -= strlen("OCF_RESKEY_CRM_meta_");
            memcpy( key, "OCF_RESKEY_CRM_meta_", strlen("OCF_RESKEY_CRM_meta_") );
        }

        DPRINTFD( "%s set environment: %s=%s", action_data->service_name,
                  key, value );

        if( 0 > setenv( key, value, 1 ) )
        {
            DPRINTFE( "Failed to set environment variable (%s=%s), "
                      "error=%s.", key, value, strerror( errno ) );
            goto ERROR;
        }
    }

    return( SM_OKAY );

ERROR:
    return( SM_FAILED );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Setup Environment
// ==================================
/**
 * @brief Set up the full plugin environment before exec: both the per-instance
 *        and plugin-level environment variables.
 *
 * @param[in] instance_name    Instance name.
 * @param[in] instance_params  Instance parameters ("key=value" list).
 * @param[in] action_data      Action being run.
 *
 * @return SM_OKAY on success; an error code otherwise.
 */
static SmErrorT sm_service_action_setup_env( char instance_name[],
    char instance_params[], SmServiceActionDataT* action_data )
{
    SmErrorT error;

    error = sm_service_action_setup_instance_env_vars( instance_name,
                                            instance_params, action_data );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to set instance environment variables for service "
                  "(%s) action (%s), error=%s.", action_data->service_name,
                  sm_service_action_str( action_data->action ),
                  sm_error_str( error ) );
        return( error );
    }

    error = sm_service_action_setup_plugin_env_vars( action_data );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to set plugin environment variables for service "
                  "(%s) action (%s), error=%s.", action_data->service_name,
                  sm_service_action_str( action_data->action ),
                  sm_error_str( error ) );
        return( error );
    }

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Is Systemd Template
// =====================================
/**
 * @brief Test whether the service is managed as a systemd template-instance
 *        unit (sysd-template).
 *
 * @param[in] action_data  Action to test.
 *
 * @return true if the plugin type is a systemd template; false otherwise.
 */
static bool is_systemd_template( SmServiceActionDataT* action_data )
{
    return( 0 == strncmp( SM_SERVICE_ACTION_PLUGIN_TYPE_SYSD_TEMPLATE,
                          action_data->plugin_type,
                          strlen( SM_SERVICE_ACTION_PLUGIN_TYPE_SYSD_TEMPLATE ) ) );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Is Systemd
// ===========================
/**
 * @brief Test whether the service is driven via "systemctl". True for both
 *        plain systemd units (sysd-service) and template-instance units
 *        (sysd-template).
 *
 * @param[in] action_data  Action to test.
 *
 * @return true if the plugin type is a systemd unit or template; false
 *         otherwise.
 */
static bool is_systemd( SmServiceActionDataT* action_data )
{
    return( ( 0 == strncmp( SM_SERVICE_ACTION_PLUGIN_TYPE_SYSD_SCRIPT,
                            action_data->plugin_type,
                            strlen( SM_SERVICE_ACTION_PLUGIN_TYPE_SYSD_SCRIPT ) ) ) ||
            ( 0 == strncmp( SM_SERVICE_ACTION_PLUGIN_TYPE_SYSD_TEMPLATE,
                            action_data->plugin_type,
                            strlen( SM_SERVICE_ACTION_PLUGIN_TYPE_SYSD_TEMPLATE ) ) ) );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Compose Systemd Template Instance Unit Name
// ============================================================
/**
 * @brief Compose the instance unit name to be passed to "systemctl"
 *        (e.g. "systemctl status paramdemo@one.service").
 *
 * @param[in]  plugin_name  Template unit file name (e.g. "paramdemo@.service").
 * @param[in]  instance     Bare instance token (e.g. "one").
 * @param[out] unit         Composed instance unit name
 *                          (e.g. "paramdemo@one.service").
 * @param[in]  unit_size    Size in bytes of the "unit" buffer
 *                          (e.g. sizeof(unit)).
 *
 * @return true on success; false if the composed name does not fit in "unit"
 *         (truncated). On truncation "unit" holds the truncated string.
 */
static bool sm_service_action_systemd_template_instance(
    const char plugin_name[], const char instance[], char unit[],
    size_t unit_size )
{
    char base[SM_SERVICE_ACTION_PLUGIN_NAME_MAX_CHAR];
    snprintf( base, sizeof(base), "%s", plugin_name );

    // Truncate at the '@' to get the template base ("foo@.service" -> "foo").
    char* at = strchr( base, '@' );
    if( NULL != at )
    {
        *at = '\0';
    }

    int needed = snprintf( unit, unit_size, "%s@%s.service", base, instance );
    if( ( needed < 0 ) || ( (size_t) needed >= unit_size ) )
    {
        return( false );
    }
    return( true );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Existence Check For Systemd Service File
// ====================================================
/**
 * @brief Locate a systemd unit file, checking the writable override directory
 *        (/etc/systemd/system) first, then the packaged location
 *        (/usr/lib/systemd/system). Supports template unit files.
 *
 * @param[in]  unit_file  Unit file name to look for.
 * @param[out] path       Resolved path (set to the packaged location if not
 *                        found in either directory).
 * @param[in]  path_size  Size in bytes of the "path" buffer.
 *
 * @return true if the unit file exists in one of the two directories; false
 *         otherwise (both locations are logged).
 */
static bool sm_service_action_get_systemd_unit_path( char unit_file[],
    char path[], size_t path_size )
{
    snprintf( path, path_size, "%s/%s",
              SM_SERVICE_ACTION_PLUGIN_TYPE_SYSD_ETC_DIR, unit_file );
    if( 0 == access( path, F_OK ) )
    {
        return( true );
    }

    snprintf( path, path_size, "%s/%s",
              SM_SERVICE_ACTION_PLUGIN_TYPE_SYSD_DIR, unit_file );
    if( 0 == access( path, F_OK ) )
    {
        return( true );
    }

    DPRINTFE( "Systemd unit file (%s) not found in %s or %s.",
              unit_file,
              SM_SERVICE_ACTION_PLUGIN_TYPE_SYSD_ETC_DIR,
              SM_SERVICE_ACTION_PLUGIN_TYPE_SYSD_DIR );
    return( false );
}
// ****************************************************************************

// This table maps the plug-in command specified in the SM
// database table SM_SERVICE_ACTIONS for the service
// with the external  call to the "systemctl" command.
static const char* sm_systemd_cmd_map[][2] =
{
    { "start",   "start"  },
    { "standby", "start"  },
    { "active",  "start"  },
    { "stop",    "stop"   },
    { "status",  "status" },
 };

// ****************************************************************************
// Service Action - Get service action from plugin command
// =================================================
/**
 * @brief Map an SM plugin command (e.g. "start"/"stop"/"status") to its
 *        "systemctl" verb using sm_systemd_cmd_map.
 *
 * @param[in]  service_name    Service name (for logging).
 * @param[in]  plugin_command  SM plugin command to map.
 * @param[out] systemctl_cmd   Mapped systemctl verb (empty if unmapped).
 *
 * @return SM_OKAY if the command was mapped; SM_FAILED otherwise.
 */
static SmErrorT sm_service_action_get_systemd_cmd( char service_name[],
    char plugin_command[], char systemctl_cmd[] )
{
    unsigned int i;

    systemctl_cmd[0] = '\0';

    for( i = 0; i < sizeof(sm_systemd_cmd_map) / sizeof(sm_systemd_cmd_map[0]); ++i )
    {
        if( 0 == strcmp( plugin_command, sm_systemd_cmd_map[i][0] ) )
        {
            snprintf( systemctl_cmd, SM_SERVICE_ACTION_PLUGIN_COMMAND_MAX_CHAR,
                      "%s", sm_systemd_cmd_map[i][1] );
            break;
        }
    }

    if( '\0' == systemctl_cmd[0] )
    {
        DPRINTFE( "Unrecognized plugin_command (%s) for service (%s).",
                  plugin_command, service_name );
        return( SM_FAILED );
    }

    return( SM_OKAY );
}
// ****************************************************************************


// ****************************************************************************
// Service Action - Resolve Plugin Exec Path
// =========================================
/**
 * @brief Resolve the on-disk path/target used to run the action, based on
 *        plugin type, and apply any type-specific pre-exec gates:
 *          - LSB:    "<lsb_dir>/<plugin_name>"
 *          - OCF:    "<ocf_plugin_dir>/<plugin_class>/<plugin_name>"
 *          - systemd (plain or template): the unit file must exist in one of
 *            the two unit directories; a template additionally requires a
 *            non-empty instance token (PLUGIN_PARAMETERS).
 *          - anything else: invalid plugin type.
 *
 * @param[in]  action_data  Action to resolve (plugin type/name/class/params).
 * @param[out] plugin_exec  Resolved exec path or systemd unit file path.
 * @param[in]  exec_size    Size in bytes of the "plugin_exec" buffer.
 *
 * @return SM_OKAY on success (with "plugin_exec" set to the resolved path);
 *         an error code otherwise.
 */
static SmErrorT sm_service_action_resolve_exec(
    SmServiceActionDataT* action_data, char plugin_exec[], size_t exec_size )
{
    if( 0 == strcmp( SM_SERVICE_ACTION_PLUGIN_TYPE_LSB_SCRIPT,
                     action_data->plugin_type ) )
    {
        snprintf( plugin_exec, exec_size, "%s/%s",
                  SM_SERVICE_ACTION_PLUGIN_TYPE_LSB_DIR,
                  action_data->plugin_name );
        return( SM_OKAY );
    }

    if( 0 == strcmp( SM_SERVICE_ACTION_PLUGIN_TYPE_OCF_SCRIPT,
                     action_data->plugin_type ) )
    {
        snprintf( plugin_exec, exec_size, "%s/%s/%s",
                  SM_SERVICE_ACTION_PLUGIN_TYPE_OCF_PLUGIN_DIR,
                  action_data->plugin_class, action_data->plugin_name );
        return( SM_OKAY );
    }

    if( is_systemd( action_data ) )
    {
        // Existence check for Systemd service file
        if( !sm_service_action_get_systemd_unit_path(
                action_data->plugin_name, plugin_exec, exec_size ) )
        {
            DPRINTFE( "Service (%s) systemd unit (%s) not found.",
                      action_data->service_name, action_data->plugin_name );
            return( SM_FAILED );
        }

        // A template unit needs an instance token (from PLUGIN_PARAMETERS)
        // to form "<base>@<instance>.service". Reject an empty value here
        // rather than exec an invalid unit name.
        if( is_systemd_template( action_data ) &&
            ( '\0' == action_data->plugin_params[0] ) )
        {
            DPRINTFE( "Service (%s) systemd template unit (%s) has no "
                      "instance (PLUGIN_PARAMETERS is empty).",
                      action_data->service_name, action_data->plugin_name );
            return( SM_FAILED );
        }
        return( SM_OKAY );
    }

    snprintf( plugin_exec, exec_size, "%s", action_data->plugin_name );
    DPRINTFE( "Invalid Plug In Type. Plug In Name = %s Plug In Type = %s "
              "Svc Name = %s", action_data->plugin_name,
              action_data->plugin_type, action_data->service_name );
    return( SM_FAILED );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Validate Plugin File
// ======================================
/**
 * @brief Validate the resolved plugin file prior to exec. LSB and OCF scripts
 *        are exec'd directly, so they must exist and be executable
 *        (F_OK | X_OK). Systemd units are passed to "systemctl" (not exec'd)
 *        and do not require the executable bit. In all cases the file must
 *        exist and be non-empty.
 *
 * @param[in] action_data  Action being validated (used for type and logging).
 * @param[in] plugin_exec  Resolved plugin path to validate.
 *
 * @return SM_OKAY if the plugin file is valid; an error code otherwise.
 */
static SmErrorT sm_service_action_validate_plugin_file(
    SmServiceActionDataT* action_data, const char plugin_exec[] )
{
    struct stat stat_data;

    if( !is_systemd( action_data ) )
    {
        if( 0 > access( plugin_exec, F_OK | X_OK ) )
        {
            DPRINTFE( "Service (%s) plugin (%s) access failed, error=%s.",
                      action_data->service_name, plugin_exec,
                      strerror( errno ) );
            return( SM_FAILED );
        }
    }

    if( 0 > stat( plugin_exec, &stat_data ) )
    {
        DPRINTFE( "Service (%s) plugin (%s) stat failed, error=%s.",
                  action_data->service_name, plugin_exec, strerror( errno ) );
        return( SM_FAILED );
    }

    if( 0 >= stat_data.st_size )
    {
        DPRINTFE( "Service (%s) plugin (%s) has zero size.",
                  action_data->service_name, action_data->plugin_name );
        return( SM_FAILED );
    }

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Child Prepare
// ==============================
/**
 * @brief Set up the forked child process before exec: new process group, close
 *        all inherited file descriptors, reopen stdin/stdout/stderr to
 *        /dev/null, and raise scheduling priority. On any hard failure the
 *        child exits directly with SM_SERVICE_ACTION_PLUGIN_FAILURE (this
 *        function runs only in the child).
 *
 * @param[in] action_data  Action being run (used for logging only).
 */
static void sm_service_action_child_prepare(
    SmServiceActionDataT* action_data )
{
    struct rlimit file_limits;
    unsigned int fd_i;
    int result;

    if( 0 > setpgid( 0, 0 ) )
    {
        DPRINTFE( "Failed to set process group id for service (%s), "
                  "error=%s.", action_data->service_name, strerror( errno ) );
        exit( SM_SERVICE_ACTION_PLUGIN_FAILURE );
    }

    if( 0 > getrlimit( RLIMIT_NOFILE, &file_limits ) )
    {
        DPRINTFE( "Failed to get file limits for service (%s), error=%s.",
                  action_data->service_name, strerror( errno ) );
        exit( SM_SERVICE_ACTION_PLUGIN_FAILURE );
    }

    for( fd_i = 0; fd_i < file_limits.rlim_cur; ++fd_i )
    {
        close( fd_i );
    }

    if( 0 > open( "/dev/null", O_RDONLY ) )
    {
        DPRINTFE( "Failed to open stdin to /dev/null for service (%s), "
                  "error=%s.", action_data->service_name, strerror( errno ) );
    }

    if( 0 > open( "/dev/null", O_WRONLY ) )
    {
        DPRINTFE( "Failed to open stdout to /dev/null for service (%s), "
                  "error=%s.", action_data->service_name, strerror( errno ) );
    }

    if( 0 > open( "/dev/null", O_WRONLY ) )
    {
        DPRINTFE( "Failed to open stderr to /dev/null for service (%s), "
                  "error=%s.", action_data->service_name, strerror( errno ) );
    }

    result = setpriority( PRIO_PROCESS, getpid(), -1 );
    if( 0 > result )
    {
        DPRINTFE( "Failed to set priority of process, error=%s.",
                  strerror( errno ) );
        exit( SM_SERVICE_ACTION_PLUGIN_FAILURE );
    }
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Child Exec Systemd
// ===================================
/**
 * @brief Exec "systemctl <cmd> <unit>" in the child. Composes the unit name: a
 *        plain unit (sysd-service) uses PLUGIN_NAME as-is
 *        (e.g. "mtcAgent.service"); a template (sysd-template) composes
 *        "<base>@<instance>.service" from PLUGIN_NAME and the PLUGIN_PARAMETERS
 *        instance token (e.g. "paramdemo@one.service"). Returns only on exec
 *        failure; on any hard error the child exits with
 *        SM_SERVICE_ACTION_PLUGIN_FAILURE.
 *
 * @param[in] action_data  Systemd action to run.
 */
static void sm_service_action_child_exec_systemd(
    SmServiceActionDataT* action_data )
{
    char systemctl_cmd[SM_SERVICE_ACTION_PLUGIN_COMMAND_MAX_CHAR];
    char unit_name[SM_SERVICE_ACTION_SYSD_UNIT_NAME_MAX_CHAR];

    if( SM_OKAY != sm_service_action_get_systemd_cmd(
            action_data->service_name, action_data->plugin_command,
            systemctl_cmd ) )
    {
        DPRINTFE( "Service (%s) has no systemctl mapping for plugin "
                  "command (%s).", action_data->service_name,
                  action_data->plugin_command );
        exit( SM_SERVICE_ACTION_PLUGIN_FAILURE );
    }

    if( is_systemd_template( action_data ) )
    {
        if( !sm_service_action_systemd_template_instance(
                action_data->plugin_name, action_data->plugin_params,
                unit_name, sizeof(unit_name) ) )
        {
            DPRINTFE( "Service (%s) systemd template unit name "
                      "(%s@%s.service) too long for buffer (%zu).",
                      action_data->service_name, action_data->plugin_name,
                      action_data->plugin_params, sizeof(unit_name) );
            exit( SM_SERVICE_ACTION_PLUGIN_FAILURE );
        }
    } else {
        snprintf( unit_name, sizeof(unit_name), "%s",
                  action_data->plugin_name );
    }

    // e.g. systemctl start mtcAgent.service
    //      systemctl start ip-addr@oam-ipv4.service
    char* argv[] = { (char*)"systemctl", systemctl_cmd, unit_name, NULL };
    if( 0 > execv( "/usr/bin/systemctl", argv ) )
    {
        DPRINTFE( "Failed to exec systemd command for service (%s), "
                  "error=%s.", action_data->service_name, strerror( errno ) );
        exit( SM_SERVICE_ACTION_PLUGIN_FAILURE );
    }
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Child Exec
// ===========================
/**
 * @brief Exec the action in the child process. Systemd units are dispatched via
 *        "systemctl"; LSB and OCF scripts are exec'd directly as
 *        "<plugin_exec> <plugin_command>". When SM_SERVICE_ACTION_TIME_PLUGIN
 *        is defined, the direct-exec path is wrapped with "/usr/bin/time" for
 *        profiling. Returns only on exec failure (caller then exits with the
 *        failure code).
 *
 * @param[in] action_data  Action to exec.
 * @param[in] plugin_exec  Resolved exec path (LSB/OCF only).
 */
static void sm_service_action_child_exec(
    SmServiceActionDataT* action_data, char plugin_exec[] )
{
    if( is_systemd( action_data ) )
    {
        sm_service_action_child_exec_systemd( action_data );
        return;
    }

#ifdef SM_SERVICE_ACTION_TIME_PLUGIN
    char time_exec[] = "/usr/bin/time";
    char time_append[] = "-a";
    char time_output[] = "-o";
    char time_file[80];
    char* argv[] = { time_exec, time_append, time_output, time_file,
                     plugin_exec, action_data->plugin_command, NULL };

    snprintf( time_file, sizeof(time_file), "/tmp/%s_%s-timing.txt",
              action_data->service_name, action_data->plugin_command );

    if( 0 > execv( time_exec, argv ) )
    {
        DPRINTFE( "Failed to exec command for service (%s), error=%s.",
                  action_data->service_name, strerror( errno ) );
        exit( SM_SERVICE_ACTION_PLUGIN_FAILURE );
    }
#else
    char* argv[] = { plugin_exec, action_data->plugin_command, NULL };
    if( 0 > execv( plugin_exec, argv ) )
    {
        DPRINTFE( "Failed to exec command for service (%s), error=%s.",
                  action_data->service_name, strerror( errno ) );
        exit( SM_SERVICE_ACTION_PLUGIN_FAILURE );
    }
#endif // SM_SERVICE_ACTION_TIME_PLUGIN
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Run
// ====================
/**
 * @brief Run an action for a service: resolve and validate the plugin, then
 *        fork a child that sets up its environment and exec's the plugin
 *        (systemctl for systemd units, the script directly for LSB/OCF). An
 *        unmanaged service (a "<name>.unmanaged" marker) force-passes the
 *        action. The parent returns immediately with the child pid; the
 *        caller is expected to reap it and interpret the exit code.
 *
 * @param[in]  service_name    Service name.
 * @param[in]  instance_name   Instance name (for environment setup).
 * @param[in]  instance_params Instance parameters (for environment setup).
 * @param[in]  action          Action to run.
 * @param[out] process_id      Pid of the forked child (-1 on failure).
 * @param[out] timeout_in_ms   Action timeout in milliseconds (0 on failure).
 *
 * @return SM_OKAY if the child was forked; SM_NOT_FOUND if the action is
 *         unknown; an error code on resolve/validate/fork failure.
 */
SmErrorT sm_service_action_run( char service_name[], char instance_name[],
    char instance_params[], SmServiceActionT action, int* process_id,
    int* timeout_in_ms )
{
    pid_t pid;
    bool service_managed = true;
    char plugin_exec[SM_SERVICE_ACTION_PLUGIN_EXEC_MAX_CHAR];
    SmServiceActionDataT* action_data;
    SmErrorT error;

    *process_id = -1;
    *timeout_in_ms = 0;

    action_data = sm_service_action_table_read( service_name, action );
    if( NULL == action_data )
    {
        DPRINTFD( "Service (%s) action (%s) does not exist.", service_name,
                  sm_service_action_str( action ) );
        return( SM_NOT_FOUND );
    }

    snprintf( plugin_exec, sizeof(plugin_exec), "%s/%s.unmanaged",
              SM_RUN_SERVICES_DIRECTORY, service_name );
    if( 0 == access( plugin_exec,  F_OK ) )
    {
        DPRINTFI( "Service (%s) is unmanaged, actions are force-passed.",
                  service_name );
        service_managed = false;
    }

    if( service_managed )
    {
        sm_service_action_validate( action_data );

        error = sm_service_action_resolve_exec( action_data, plugin_exec,
                                                sizeof(plugin_exec) );
        if( SM_OKAY != error )
        {
            return( error );
        }

        DPRINTFD( "Plugin executable (%s) for service (%s).", plugin_exec,
                  action_data->service_name );

        error = sm_service_action_validate_plugin_file( action_data,
                                                        plugin_exec );
        if( SM_OKAY != error )
        {
            return( error );
        }
    }

    pid = fork();
    if( 0 > pid )
    {
        DPRINTFE( "Failed to fork process for service (%s), error=%s.",
                  action_data->service_name, strerror( errno ) );
        return( SM_FAILED );

    } else if( 0 == pid ) {
        // Child process.
        DPRINTFD( "Child process created for service (%s).",
                  action_data->service_name );

        sm_service_action_child_prepare( action_data );

        if( !service_managed )
        {
            exit( SM_SERVICE_ACTION_PLUGIN_FORCE_SUCCESS );
        }

        error = sm_service_action_setup_env( instance_name, instance_params,
                                             action_data );
        if( SM_OKAY != error )
        {
            DPRINTFE( "Failed to setup environment for service (%s), "
                      "error=%s.", action_data->service_name,
                      sm_error_str( error ) );
            exit( SM_SERVICE_ACTION_PLUGIN_FAILURE );
        }

        sm_service_action_child_exec( action_data, plugin_exec );

        exit( SM_SERVICE_ACTION_PLUGIN_FAILURE );

    } else {
        // Parent process.
        *process_id = (int) pid;
        *timeout_in_ms = action_data->timeout_in_secs * 1000;

        DPRINTFD( "Child process (%i) created for service (%s).", *process_id,
                  action_data->service_name );
    }

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Initialize
// ===========================
/**
 * @brief Initialize the service action module: the action table and the action
 *        result table.
 *
 * @return SM_OKAY on success; an error code if either table fails to
 *         initialize.
 */
SmErrorT sm_service_action_initialize( void )
{
    SmErrorT error;

    error = sm_service_action_table_initialize();
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to initialize service action table, error=%s.",
                  sm_error_str( error ) );
        return( error );
    }

    error = sm_service_action_result_table_initialize();
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to initialize service action result table, "
                  "error=%s.", sm_error_str( error ) );
        return( error );
    }

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Action - Finalize
// =========================
/**
 * @brief Finalize the service action module: the action result table and the
 *        action table.
 *
 * @return SM_OKAY (table finalize errors are logged but not propagated).
 */
SmErrorT sm_service_action_finalize( void )
{
    SmErrorT error;

    error = sm_service_action_result_table_finalize();
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to finalize service action result table, error=%s.",
                  sm_error_str( error ) );
    }

    error = sm_service_action_table_finalize();
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to finalize service action table, error=%s.",
                  sm_error_str( error ) );
    }

    return( SM_OKAY );
}
// ****************************************************************************
