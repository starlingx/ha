//
// Copyright (c) 2018-2026 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#include "sm_failover_fail_pending_state.h"
#include <stdlib.h>
#include <unistd.h>
#include <limits.h>
#include "sm_configuration_table.h"
#include "sm_cluster_hbs_info_msg.h"
#include "sm_types.h"
#include "sm_limits.h"
#include "sm_debug.h"
#include "sm_failover.h"
#include "sm_failover_fsm.h"
#include "sm_failover_ss.h"
#include "sm_failover_utils.h"
#include "sm_node_utils.h"
#include "sm_node_api.h"
#include "sm_worker_thread.h"


/****************************************************************************
 *
 * Name        : scale_failpending_timeout
 *
 * Description : Computes a timeout value based upon the heartbeat_period
 *    that is passed in as a parameter.
 *    Values are in milliseconds.
 *    Input values must be between 100 and 1000, otherwise 0 is returned.
 *    Return values range from 2000ms for a 100ms input and 4000ms for a
 *    1000ms input. All other in-between values are computed linearly
 *    and rounded to the nearest 100ms.
 *
 * Parameter  :
 *
 *    heartbeat_period - the value of the heartbeat_period in msecs
 *
 ***************************************************************************/
static int scale_failpending_timeout(unsigned int heartbeat_period)
{
    if (heartbeat_period < 100 || heartbeat_period > 1000)
    {
        return 0;
    }
    return (((int)(2000 + (heartbeat_period - 100) * 2.22 + 0.5) + 50) / 100 * 100);
}

// When entering the Fail-Pending State SM waits for a time period before comparing
// the state of itself and its peer controller.
static const int FAIL_PENDING_TIMEOUT_DEFAULT = 4000; // 4 seconds
static const int FAIL_PENDING_TIMEOUT_MIN = 1200;

/****************************************************************************
 *
 * Name        : get_failpending_timeout
 *
 * Description : Determines the timeout period in milliseconds to be used by
 *    the SM Fail-Pending state.
 *    Reads the value from the SM database. If not found it sets a timeout
 *    value based upon the heartbeat_period in SM Cluster information.
 *
 * Parameters  :
 *
 *    None
 *
 ***************************************************************************/
static inline int get_failpending_timeout()
{
    int fail_pending_timeout = 0;

    char buf[SM_CONFIGURATION_VALUE_MAX_CHAR + 1];

    // Read the SM database. If the value is not present "buf" will be an empty string
    if (SM_OKAY == sm_configuration_table_get("FAILPENDING_TIMEOUT_MS", buf, sizeof(buf) - 1)
        && buf[0] != '\0')
    {
        // Convert string to integer with error handling
        char *endptr;
        long temp_value = strtol(buf, &endptr, 10);

        // Check for conversion errors
        if (endptr == buf || *endptr != '\0' || temp_value < 0 || temp_value > INT_MAX)
        {
            DPRINTFE("Invalid FAILPENDING_TIMEOUT_MS value in SM database: %s", buf);
        }
        else
        {
            fail_pending_timeout = (int)temp_value;
            DPRINTFI("Reading Fail Pending Timeout from SM database: %d ms", fail_pending_timeout);
        }
    }

    if (fail_pending_timeout == 0)
    {
        // Get the heartbeat_period that was extracted from the heartbeat
        // received from the hbsAgent.
        unsigned int hb_period = SmClusterHbsInfoMsg::get_current_state().heartbeat_period;
        int scaled_timeout = scale_failpending_timeout(hb_period);
        if (scaled_timeout > 0)
        {
            // valid heartbeat_period successfully fetched
            DPRINTFI("heartbeat_period value is %u ms", hb_period);
            fail_pending_timeout = scaled_timeout;
        }
        else
        {
            DPRINTFE("Could not compute Fail Pending Timeout. hb_period = %u", hb_period);
        }
    }

    if (fail_pending_timeout < FAIL_PENDING_TIMEOUT_MIN)
    {
        DPRINTFE("Fail Pending Timeout: %d ms is below minimum. Using default: %d ms",
            fail_pending_timeout,
            FAIL_PENDING_TIMEOUT_DEFAULT
        );
        fail_pending_timeout = FAIL_PENDING_TIMEOUT_DEFAULT;
    }
    DPRINTFI("Fail Pending Timeout is set to %d ms", fail_pending_timeout);

    return fail_pending_timeout;
}

static SmTimerIdT action_timer_id = SM_TIMER_ID_INVALID;
static const int RESET_TIMEOUT = 10 * 1000; // 10 seconds for a reset command to reboot a node
static const int GO_ACTIVE_TIMEOUT = 30 * 1000; // 30 seconds for standby node go active
static const int WAIT_RESET_TIMEOUT = RESET_TIMEOUT + 5 * 1000; // extra 5 seconds for sending reset command

static void disable_peer(SmSimpleAction&)
{
    SmErrorT error;
    int counter = 0;
    bool done = false;
    DPRINTFI("To send mtce api to disable peer");

    while(!done && counter < 5)
    {
        error = sm_failover_disable_peer();
        counter ++;
        if(SM_OKAY != error)
        {
            int wait_interval_us = 1000000; // 1 second
            DPRINTFE("Failed to disable peer, reattempt in %d ms",
                wait_interval_us / 1000);
            usleep(wait_interval_us); // wait 1 second before retry
        }else
        {
            done = true;
        }
    }
}
static SmSimpleAction _disable_peer_action("disable-peer", disable_peer);

static bool wait_for_reset_timeout(SmTimerIdT timer_id, int64_t user_data)
{
    //timer never rearm, clear the timer id
    action_timer_id = SM_TIMER_ID_INVALID;
    sm_failover_utils_reset_stayfailed_flag();
    DPRINTFI("stayfailed flag file is removed");
    SmFailoverFSM::get_fsm().set_state(SM_FAILOVER_STATE_SURVIVED);
    return false;
}

static bool reset_standby_timeout(SmTimerIdT timer_id, int64_t user_data)
{
    //timer never rearm, clear the timer id
    action_timer_id = SM_TIMER_ID_INVALID;
    sm_failover_utils_set_stayfailed_flag();
    DPRINTFI("stayfailed flag file is set");
    const char* timer_name = "confirm standby reset";
    SmErrorT error = sm_timer_register( timer_name, WAIT_RESET_TIMEOUT + WAIT_RESET_TIMEOUT,
                               wait_for_reset_timeout,
                               0, &action_timer_id);

    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to register confirm standby reset timer");
    }
    DPRINTFI("wait for %d secs...", (WAIT_RESET_TIMEOUT + WAIT_RESET_TIMEOUT) / 1000);
    return false;
}

SmErrorT blind_guess_start_active()
{
    SmErrorT error;
    SmWorkerThread::get_worker().add_priority_action(&_disable_peer_action);

    const char* timer_name = "reset standby";
    error = sm_timer_register( timer_name, RESET_TIMEOUT,
                               reset_standby_timeout,
                               0, &action_timer_id);

    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to register reset standby timer");
        return SM_FAILED;
    }

    DPRINTFI("wait for %d secs...", RESET_TIMEOUT / 1000);
    return SM_OKAY;
}

static void standby_go_active_failed()
{
    sm_failover_utils_set_stayfailed_flag();
    DPRINTFI("stayfailed flag file is set");
    SmFailoverFSM::get_fsm().set_state(SM_FAILOVER_STATE_FAILED);
}

bool standby_wait_timeout(SmTimerIdT timer_id, int64_t user_data)
{
    //timer never rearm, clear the timer id
    action_timer_id = SM_TIMER_ID_INVALID;
    sm_failover_utils_reset_stayfailed_flag();
    DPRINTFI("stayfailed flag file is removed");
    char host_name[SM_NODE_NAME_MAX_CHAR];
    SmErrorT error = sm_node_utils_get_hostname(host_name);
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to get hostname, error=%s.",
                  sm_error_str( error ) );

        standby_go_active_failed();
        return false;
    }

    SmNodeScheduleStateT host_state = sm_get_controller_state(host_name);
    if(SM_NODE_STATE_ACTIVE != host_state)
    {
        standby_go_active_failed();
        return false;
    }

    SmWorkerThread::get_worker().add_priority_action(&_disable_peer_action);

    SmFailoverFSM::get_fsm().set_state(SM_FAILOVER_STATE_SURVIVED);
    return false;
}

static void blind_guess_start_standby()
{
    SmErrorT error;
    sm_failover_utils_set_stayfailed_flag();
    DPRINTFI("set stayfailed flag file");

    sm_failover_activate_self();
    const char* timer_name = "active controller action timeout";
    error = sm_timer_register( timer_name, WAIT_RESET_TIMEOUT + GO_ACTIVE_TIMEOUT,
                               standby_wait_timeout,
                               0, &action_timer_id);

    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to register blindguess action timer");
    }
    DPRINTFI("wait for %d secs", (WAIT_RESET_TIMEOUT + GO_ACTIVE_TIMEOUT) / 1000);
}

void blind_guess_scenario_start()
{
    SmSystemFailoverStatus& failover_status = SmSystemFailoverStatus::get_status();
    SmNodeScheduleStateT host_state = failover_status.get_host_pre_failure_schedule_state();
    SmNodeScheduleStateT peer_state = failover_status.get_peer_pre_failure_schedule_state();
    DPRINTFI("Pre failure host state %s, peer state %s",
        sm_node_schedule_state_str(host_state), sm_node_schedule_state_str(peer_state));
    if(SM_NODE_STATE_ACTIVE == host_state)
    {
        if(SM_NODE_STATE_STANDBY == peer_state)
        {
            blind_guess_start_active();
        }
    }else if(SM_NODE_STATE_STANDBY == host_state)
    {
        blind_guess_start_standby();
    }
}

SmFailoverFailPendingState::SmFailoverFailPendingState(SmFailoverFSM& fsm) : SmFSMState(fsm)
{
    this->_pending_timer_id = SM_TIMER_ID_INVALID;
}

SmFailoverFailPendingState::~SmFailoverFailPendingState()
{
    this->_deregister_timer();
}

SmErrorT SmFailoverFailPendingState::event_handler(SmFailoverEventT event, const ISmFSMEventData* event_data)
{
    bool duplex = false;
    bool blind_guess = false;
    switch (event)
    {
        case SM_FAILOVER_EVENT_IF_STATE_CHANGED:
            // Situation are changing, extend wait time
            this->_register_timer();
            break;

        case SM_FAILOVER_EVENT_FAIL_PENDING_TIMEOUT:
            sm_node_utils_is_aio_duplex(&duplex);
            if( duplex &&
                0 == (sm_failover_get_host_node_info_flags() & SM_FAILOVER_HEARTBEAT_ALIVE))
            {
                SmSystemModeT system_mode = sm_node_utils_get_system_mode();
                SmInterfaceTypeT interfaces_to_check[3] = {SM_INTERFACE_UNKNOWN};
                bool healthy = true;
                if(sm_failover_utils_is_stayfailed())
                {
                    healthy = false;
                }

                if(SM_SYSTEM_MODE_CPE_DUPLEX_DC == system_mode)
                {
                    interfaces_to_check[0] = SM_INTERFACE_OAM;
                }else
                {
                    interfaces_to_check[0] = SM_INTERFACE_MGMT;
                    interfaces_to_check[1] = SM_INTERFACE_CLUSTER_HOST;
                    interfaces_to_check[2] = SM_INTERFACE_ADMIN;
                }
                for(int i = 0; interfaces_to_check[i] != SM_INTERFACE_UNKNOWN; i ++)
                {
                    SmFailoverInterfaceStateT if_state = sm_failover_get_interface_info(interfaces_to_check[i]);
                    if(SM_FAILOVER_INTERFACE_DOWN == if_state)
                    {
                        healthy = false;
                        break;
                    }
                }

                if(healthy)
                {
                    blind_guess_scenario_start();
                    blind_guess = true;
                }
            }
            if( !blind_guess )
            {
                SmSystemFailoverStatus& failover_status = SmSystemFailoverStatus::get_status();
                SmErrorT error = sm_failover_ss_get_survivor(failover_status);
                SmNodeScheduleStateT host_state = failover_status.get_host_schedule_state();
                SmNodeScheduleStateT peer_state = failover_status.get_peer_schedule_state();
                if(SM_OKAY != error)
                {
                    DPRINTFE("Failed to get failover survivor. Error %s", sm_error_str(error));
                    return error;
                }

                error = sm_failover_set_system(failover_status);
                if(SM_NODE_STATE_FAILED == host_state)
                {
                    this->fsm.set_state(SM_FAILOVER_STATE_FAILED);
                }
                else if(SM_NODE_STATE_ACTIVE == host_state)
                {
                    if(SM_NODE_STATE_FAILED == peer_state)
                    {
                        this->fsm.set_state(SM_FAILOVER_STATE_SURVIVED);
                    }else
                    {
                        this->fsm.set_state(SM_FAILOVER_STATE_NORMAL);
                    }
                }
                else if(SM_NODE_STATE_STANDBY == host_state)
                {
                    this->fsm.set_state(SM_FAILOVER_STATE_NORMAL);
                }else
                {
                    DPRINTFE("Runtime error: unexpected scheduling state: %s",
                        sm_node_schedule_state_str(host_state));
                }
                return error;
            }
            break;
        case SM_FAILOVER_EVENT_PEER_IS_NORMAL:
            break;
        default:
            DPRINTFE("Runtime error, unexpected event %s, at state %s",
                sm_failover_event_str(event),
                sm_failover_state_str(this->fsm.get_state()));
    }
    return SM_OKAY;
}

bool SmFailoverFailPendingState::_fail_pending_timeout(
    SmTimerIdT timer_id, int64_t user_data)
{
    SmFailoverFSM::get_fsm().send_event(SM_FAILOVER_EVENT_FAIL_PENDING_TIMEOUT, NULL);
    return false;
}

SmErrorT SmFailoverFailPendingState::enter_state()
{
    SmFSMState::enter_state();
    DPRINTFI("Pre failure hbs cluster info:");
    const SmClusterHbsStateT& cluster_hbs_state = SmClusterHbsInfoMsg::get_current_state();
    log_cluster_hbs_state(cluster_hbs_state);

    SmErrorT error = this->_register_timer();
    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to register fail pending timer. Error %s", sm_error_str(error));
    }
    return error;
}

void _cluster_hbs_response_callback()
{
    const SmClusterHbsStateT& cluster_hbs_state = SmClusterHbsInfoMsg::get_current_state();
    DPRINTFI("Fail-pending timeout cluster info:");
    log_cluster_hbs_state(cluster_hbs_state);
    SmSystemFailoverStatus::get_status().set_cluster_hbs_state(cluster_hbs_state);
}

bool SmFailoverFailPendingState::_delay_query_hbs_timeout(
    SmTimerIdT timer_id, int64_t user_data)
{
    SmClusterHbsInfoMsg::cluster_hbs_info_query(_cluster_hbs_response_callback);
    return false;
}

SmErrorT SmFailoverFailPendingState::_register_timer()
{
    SmErrorT error;
    const char* timer_name = "FAIL PENDING TIMER";
    if(SM_TIMER_ID_INVALID != this->_pending_timer_id)
    {
        this->_deregister_timer();
    }

    int fail_pending_timeout = get_failpending_timeout();
    error = sm_timer_register(timer_name, fail_pending_timeout,
                              SmFailoverFailPendingState::_fail_pending_timeout,
                              0, &this->_pending_timer_id);

    const char* delay_query_hbs_timer_name = "DELAY QUERY HBS";

    error = sm_timer_register(delay_query_hbs_timer_name, fail_pending_timeout - 200,
                              SmFailoverFailPendingState::_delay_query_hbs_timeout,
                              0, &this->_delay_query_hbs_timer_id);

    return error;
}

SmErrorT SmFailoverFailPendingState::_deregister_timer()
{
    SmErrorT error = SM_OKAY;
    if(SM_TIMER_ID_INVALID != this->_pending_timer_id)
    {
        error = sm_timer_deregister(this->_pending_timer_id);
        if( SM_OKAY != error )
        {
            DPRINTFE( "Failed to cancel fail pending timer, error=%s.",
                      sm_error_str( error ) );
        }else
        {
            this->_pending_timer_id = SM_TIMER_ID_INVALID;
        }
    }

    if(SM_TIMER_ID_INVALID != this->_delay_query_hbs_timer_id)
    {
        error = sm_timer_deregister(this->_delay_query_hbs_timer_id);
        if( SM_OKAY != error )
        {
            DPRINTFE( "Failed to cancel query hbs info timer, error=%s.",
                      sm_error_str( error ) );
        }else
        {
            this->_delay_query_hbs_timer_id = SM_TIMER_ID_INVALID;
        }
    }
    return error;
}

SmErrorT SmFailoverFailPendingState::exit_state()
{
    SmErrorT error = this->_deregister_timer();
    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to deregister fail pending timer. Error %s", sm_error_str(error));
    }
    if(SM_TIMER_ID_INVALID != action_timer_id)
    {
        error = sm_timer_deregister(action_timer_id);
        action_timer_id = SM_TIMER_ID_INVALID;
        if( SM_OKAY != error)
        {
            DPRINTFE("Failed to deregister action timer. Error %s", sm_error_str(error));
        }
    }
    SmFSMState::exit_state();
    return error;
}
