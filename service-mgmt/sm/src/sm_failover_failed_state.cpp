//
// Copyright (c) 2018-2021 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <limits.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <errno.h>
#include <fcntl.h>

#include "sm_failover_failed_state.h"
#include "sm_types.h"
#include "sm_debug.h"
#include "sm_node_utils.h"
#include "sm_node_api.h"
#include "sm_failover.h"
#include "sm_failover_fsm.h"
#include "sm_failover_ss.h"
#include "sm_failover_utils.h"
#include "sm_cluster_hbs_info_msg.h"

extern bool is_cluster_host_interface_configured( void );

// Failover Failed Recovery Audit period = 5 seconds
static const int FAILED_STATE_AUDIT_PERIOD = 5000;

// Recovery log throttle threshold - 1 log every minute
static const int SM_FAILOVER_FAILED_LOG_THROTTLE_THLD = 12;

// processes to restart over a failover failed recovery
#define MAX_RESTART_PROCESS_NAME_LEN 10
#define PROCESS_SM       ((const char *)("sm"))

static struct timespec start_time;

// Failover Failed state class constructor
SmFailoverFailedState::SmFailoverFailedState(SmFailoverFSM& fsm) : SmFSMState(fsm)
{
    this->_failed_state_audit_timer_id = SM_TIMER_ID_INVALID;
}

// The 'Failover Failed' state destructor
//  - stops the recovery audit if needed
SmFailoverFailedState::~SmFailoverFailedState()
{
    this->_deregister_timer();
}

// Failover Failed state entry class member function
// - starts the Failover Failed state recovery audit timer
SmErrorT SmFailoverFailedState::enter_state()
{
    SmFSMState::enter_state();

    DPRINTFE("********************************************************");
    DPRINTFE("Entering Failover Failed state ; recovery audit started ");
    DPRINTFE("********************************************************");

    clock_gettime(CLOCK_MONOTONIC_RAW, &start_time);
    DPRINTFI("Wait for %d seconds to start failed recovery audit",
              sm_failover_get_reset_peer_wait_time());
    SmErrorT error = this->_register_timer();
    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to register failed state timer. Error %s", sm_error_str(error));
    }
    return error;
}

// Failover Failed state audit timer handler
bool SmFailoverFailedState::_failed_state_audit(
    SmTimerIdT timer_id, int64_t user_data)
{
    // wait enough time for peer to be reset to avoid conflict decision, i.e being reset
    struct timespec now;
    clock_gettime(CLOCK_REALTIME, &now);
    if(now.tv_sec - start_time.tv_sec - 1 > sm_failover_get_reset_peer_wait_time())
    {
        SmFailoverFSM::get_fsm().send_event(SM_FAILOVER_EVENT_FAILED_RECOVERY_AUDIT, NULL);
    }
    return true ;
}

// Issue a self restart through pmon-restart service
static bool sm_failover_failed_process_restart( const char * process )
{
    DPRINTFI( "Issuing controlled process restart ; pmon-restart %s", process);
    pid_t pid = fork();
    if( 0 > pid )
    {
        DPRINTFE( "Failed to fork 'pmond-restart %s' request, error=%s.",
                  process, strerror( errno ) );
        return( true );
    }
    else if( 0 == pid )
    {
        // set the arguement array for execv
        char pmon_restart_cmd[] = "/usr/local/sbin/pmon-restart";

        char pmon_restart_process[MAX_RESTART_PROCESS_NAME_LEN] ;
        snprintf(&pmon_restart_process[0], MAX_RESTART_PROCESS_NAME_LEN, "%s", process);

        char* pmon_restart_argv[3] ;
        pmon_restart_argv[0] = pmon_restart_cmd;
        pmon_restart_argv[1] = pmon_restart_process;
        pmon_restart_argv[2] = NULL;

        // Add the path to socat for pmon-restart
        char path[] = "PATH=/usr/bin:$PATH";
        char* pmon_restart_env[2] ;
        pmon_restart_env[0] = path;
        pmon_restart_env[1] = NULL;

        setpgid( 0, 0 );

        struct rlimit file_limits;
        if( 0 == getrlimit( RLIMIT_NOFILE, &file_limits ) )
        {
            unsigned int fd_i;
            for( fd_i=0; fd_i < file_limits.rlim_cur; ++fd_i )
            {
                close( fd_i );
            }
            open( "/dev/null", O_RDONLY ); // stdin
            open( "/dev/null", O_WRONLY ); // stdout
            open( "/dev/null", O_WRONLY ); // stderr
        }

        execve( pmon_restart_argv[0], pmon_restart_argv, pmon_restart_env );

        // Shouldn't get this far, else there was an error.
        exit(-1);
    }
    return( false );
}

// Failover Failed recovery criteria checker
static bool sm_failover_failed_recovery_criteria_met( void )
{
    bool criteria_met = false ;

    SmFailoverInterfaceStateT oam_state, mgmt_state, cluster_host_state;
    oam_state = sm_failover_get_interface_info(SM_INTERFACE_OAM);
    mgmt_state = sm_failover_get_interface_info(SM_INTERFACE_MGMT);

    const SmClusterHbsStateT& cluster_hbs_state = SmClusterHbsInfoMsg::get_current_state();
    int peer_controller_index = SmClusterHbsInfoMsg::get_peer_controller_index();

    // If peer has stalled, do not recover until peer recovers from stall
    if(!cluster_hbs_state.controllers[peer_controller_index].sm_heartbeat_fail)
    {
        if ( is_cluster_host_interface_configured() )
        {
            cluster_host_state = sm_failover_get_interface_info(SM_INTERFACE_CLUSTER_HOST);
            if ((( oam_state == SM_FAILOVER_INTERFACE_OK ) || ( oam_state == SM_FAILOVER_INTERFACE_MISSING_HEARTBEAT )) &&
                (( mgmt_state == SM_FAILOVER_INTERFACE_OK ) || ( mgmt_state == SM_FAILOVER_INTERFACE_MISSING_HEARTBEAT )) &&
                (( cluster_host_state == SM_FAILOVER_INTERFACE_OK ) || ( cluster_host_state == SM_FAILOVER_INTERFACE_MISSING_HEARTBEAT )))
            {
                criteria_met = true ;
            }
        }
        else if ((( oam_state == SM_FAILOVER_INTERFACE_OK ) || ( oam_state == SM_FAILOVER_INTERFACE_MISSING_HEARTBEAT )) &&
                 (( mgmt_state == SM_FAILOVER_INTERFACE_OK ) || ( mgmt_state == SM_FAILOVER_INTERFACE_MISSING_HEARTBEAT )))
        {
            criteria_met = true ;
        }
    }

    DPRINTFI("Oam:%s ; Mgmt:%s ; Cluster:%s ; recovery criteria met: %s",
              sm_failover_interface_state_str(oam_state),
              sm_failover_interface_state_str(mgmt_state),
              sm_failover_interface_state_str(cluster_host_state),
               criteria_met ? "Yes" : "No");

    return (criteria_met);
}

SmErrorT proceed_recovery()
{
    SmErrorT error;
    char peer_name[SM_NODE_NAME_MAX_CHAR];
    char host_name[SM_NODE_NAME_MAX_CHAR];
    // delete peer node
    error = sm_node_api_get_peername(peer_name);
    if(SM_OKAY != error)
    {
        DPRINTFI("Cannot retrieve peer's hostname, error %s", sm_error_str(error));
        return error;
    }
    error = sm_node_api_delete_node(peer_name);
    if(SM_OKAY != error)
    {
        DPRINTFI("Failed to delete peer %s, error %s", peer_name, sm_error_str(error));
        return error;
    }else
    {
        DPRINTFI("Peer %s is deleted.", peer_name);
    }

    // enable host
    error = sm_node_api_get_hostname(host_name);
    if(SM_OKAY != error)
    {
        DPRINTFI("Cannot retrieve hostname, error %s", sm_error_str(error));
        return error;
    }
    error = sm_node_api_recover_node(host_name);
    if(SM_OKAY != error)
    {
        DPRINTFI("Failed to recover %s, error %s", host_name, sm_error_str(error));
        return error;
    }else
    {
        DPRINTFI("Host %s is recovered.", host_name);
    }

    sm_node_utils_reset_unhealthy_flag();
    DPRINTFI("Unhealthy flag is removed");
    return SM_OKAY;
}

// The 'Failover Failed' state recovery audit handler
SmErrorT SmFailoverFailedState::event_handler(SmFailoverEventT event, const ISmFSMEventData* event_data)
{
    SmErrorT error;
    event_data=event_data;
    switch (event)
    {
        case SM_FAILOVER_EVENT_IF_STATE_CHANGED:
        case SM_FAILOVER_EVENT_FAILED_RECOVERY_AUDIT:
        {
            if ( sm_failover_failed_recovery_criteria_met() )
            {
                DPRINTFI("************************************");
                DPRINTFI("** Failover Failed state recovery **");
                DPRINTFI("************************************");
                error = proceed_recovery();
                if(SM_OKAY != error)
                {
                    DPRINTFE("Cannot recover from failed state");
                }else
                {
                    sm_failover_failed_process_restart(PROCESS_SM);
                    for ( int i = 0 ; i < 10 ; i++ )
                    {
                        // waiting for shutdown
                        sleep(1);
                    }
                    DPRINTFE("Restart did not occur ; reinstating unhealthy flag ; recovery will retry");
                    sm_node_utils_set_unhealthy();
                }
            }
            else if ( ++_log_throttle > 1 )
            {
                if ( _log_throttle > SM_FAILOVER_FAILED_LOG_THROTTLE_THLD )
                    _log_throttle = 0 ;
            }
            else
            {
                DPRINTFI("Failover Failed state recovery monitor");
            }
            break;
        }
        default:
            DPRINTFE("Runtime error, unexpected event %s, at state %s",
                sm_failover_event_str(event),
                sm_failover_state_str(this->fsm.get_state()));
    }
    return SM_OKAY;
}

// Start the 'Failover Failed' state recovery audit
SmErrorT SmFailoverFailedState::_register_timer()
{
    SmErrorT error;
    const char* timer_name = "FAILED STATE AUDIT TIMER";
    if(SM_TIMER_ID_INVALID != this->_failed_state_audit_timer_id)
        this->_deregister_timer();

    error = sm_timer_register(timer_name, FAILED_STATE_AUDIT_PERIOD,
                              SmFailoverFailedState::_failed_state_audit,
                              0, &this->_failed_state_audit_timer_id);

    return error;
}

// Stop the 'Failover Failed' state recovery audit
SmErrorT SmFailoverFailedState::_deregister_timer()
{
    SmErrorT error = SM_OKAY;
    if(SM_TIMER_ID_INVALID != this->_failed_state_audit_timer_id)
    {
        error = sm_timer_deregister(this->_failed_state_audit_timer_id);
        if( SM_OKAY != error )
        {
            DPRINTFE( "Failed to cancel failed timer, error=%s.",
                      sm_error_str( error ) );
        }else
        {
            this->_failed_state_audit_timer_id = SM_TIMER_ID_INVALID;
        }
    }
    return error;
}


SmErrorT SmFailoverFailedState::exit_state()
{
    SmErrorT error = this->_deregister_timer();
    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to deregister fail failed timer. Error %s", sm_error_str(error));
    }
    if(SM_TIMER_ID_INVALID != _failed_state_audit_timer_id)
    {
        error = sm_timer_deregister(_failed_state_audit_timer_id);
        _failed_state_audit_timer_id = SM_TIMER_ID_INVALID;
        if( SM_OKAY != error)
        {
            DPRINTFE("Failed to deregister action timer. Error %s", sm_error_str(error));
        }
    }
    SmFSMState::exit_state();
    return error;
}
