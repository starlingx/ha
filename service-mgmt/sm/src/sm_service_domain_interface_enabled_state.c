//
// Copyright (c) 2014 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#include "sm_service_domain_interface_enabled_state.h"

#include <stdio.h>
#include <string.h>

#include "sm_types.h"
#include "sm_debug.h"
#include "sm_msg.h"
#include "sm_hw.h"
#include "sm_log.h"
#include "sm_heartbeat.h"
#include "sm_service_domain_table.h"
#include "sm_service_domain_interface_fsm.h"

// ****************************************************************************
// Service Domain Interface Enabled State - Entry
// ==============================================
SmErrorT sm_service_domain_interface_enabled_state_entry(
    SmServiceDomainInterfaceT* interface )
{
    SmServiceDomainT* service_domain;
    SmErrorT error;

    service_domain = sm_service_domain_table_read( interface->service_domain );
    if( NULL == service_domain )
    {
        DPRINTFE( "Service domain (%s) does not exist.",
                  interface->service_domain );
        return( SM_NOT_FOUND );
    }

    error = sm_msg_add_peer_interface( interface->interface_name,
                                       &(interface->network_peer_address),
                                       interface->network_peer_port,
                                       interface->auth_type,
                                       interface->auth_key );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to add peer messaging interface for service "
                  "domain (%s), error=%s.", interface->service_domain,
                  sm_error_str( error ) );
        return( error );
    }

    error = sm_msg_open_sockets( interface );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to open sockets on service domain (%s) "
                  "interface (%s), error=%s", interface->service_domain,
                  interface->service_domain_interface, sm_error_str( error ) );
        return( error );
    }

    error = sm_heartbeat_add_interface( interface );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to add messaging interface for service domain (%s), "
                  "error=%s.", interface->service_domain,
                  sm_error_str( error ) );
        return( error );
    }

    error = sm_heartbeat_add_peer_interface( interface->id,
                                             interface->interface_name,
                                             &(interface->network_peer_address),
                                             interface->network_heartbeat_port,
                                             service_domain->dead_interval );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to add peer messaging interface for service "
                  "domain (%s), error=%s.", interface->service_domain,
                  sm_error_str( error ) );
        return( error );
    }

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Domain Interface Enabled State - Exit
// =============================================
SmErrorT sm_service_domain_interface_enabled_state_exit(
    SmServiceDomainInterfaceT* interface )
{
    SmErrorT error;

    error = sm_heartbeat_delete_peer_interface( interface->interface_name,
                                          &(interface->network_peer_address),
                                          interface->network_heartbeat_port );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to delete peer messaging interface for service "
                  "domain (%s), error=%s.", interface->service_domain,
                  sm_error_str( error ) );
        return( error );
    }

    error = sm_msg_delete_peer_interface( interface->interface_name,
                                          &(interface->network_peer_address),
                                          interface->network_peer_port );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to delete peer messaging interface for service "
                  "domain (%s), error=%s.", interface->service_domain,
                  sm_error_str( error ) );
        return( error );
    }

    error = sm_msg_close_sockets( interface );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to close sockets on service domain (%s) "
                  "interface (%s), error=%s", interface->service_domain,
                  interface->service_domain_interface, sm_error_str( error ) );
        return( error );
    }

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Domain Interface Enabled State - Transition
// ===================================================
SmErrorT sm_service_domain_interface_enabled_state_transition(
    SmServiceDomainInterfaceT* interface, SmInterfaceStateT from_state )
{
    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Domain Interface Enabled State - Event Handler
// ======================================================
SmErrorT sm_service_domain_interface_enabled_state_event_handler(
    SmServiceDomainInterfaceT* interface,
    SmServiceDomainInterfaceEventT event, void* event_data[] )
{
    bool enabled;
    char reason_text[SM_LOG_REASON_TEXT_MAX_CHAR] = "";
    SmErrorT error;

    error = sm_hw_get_if_state( interface->interface_name, &enabled );
    if( SM_OKAY != error )
    {
        DPRINTFE( "Failed to audit hardware state of interface (%s), "
                  "error=%s", interface->interface_name,
                  sm_error_str( error ) );
        return( error );
    }
    if( !enabled )
    {
        DPRINTFI( "Interface %s is disabled", interface->interface_name );
    }

    switch( event )
    {
        case SM_SERVICE_DOMAIN_INTERFACE_EVENT_ENABLED:
            // Already in this state.
        break;

        case SM_SERVICE_DOMAIN_INTERFACE_EVENT_NODE_DISABLED:
            error = sm_service_domain_interface_fsm_set_state( 
                                            interface->service_domain,
                                            interface->service_domain_interface,
                                            SM_INTERFACE_STATE_DISABLED,
                                            "node disabled" );
            if( SM_OKAY != error )
            {
                DPRINTFE( "Set state (%s) of service domain (%s) interface (%s) "
                          "failed, error=%s.",
                          sm_interface_state_str( SM_INTERFACE_STATE_DISABLED ),
                          interface->service_domain,
                          interface->service_domain_interface,
                          sm_error_str( error ) );
                return( error );
            }
        break;

        case SM_SERVICE_DOMAIN_INTERFACE_EVENT_DISABLED:
            if( !enabled )
            {
                snprintf( reason_text, sizeof(reason_text), "%s disabled",
                          interface->interface_name );

                error = sm_service_domain_interface_fsm_set_state( 
                                            interface->service_domain,
                                            interface->service_domain_interface,
                                            SM_INTERFACE_STATE_DISABLED,
                                            reason_text );
                if( SM_OKAY != error )
                {
                    DPRINTFE( "Set state (%s) of service domain (%s) interface "
                              "(%s) failed, error=%s.",
                              sm_interface_state_str( SM_INTERFACE_STATE_DISABLED ),
                              interface->service_domain,
                              interface->service_domain_interface,
                              sm_error_str( error ) );
                    return( error );
                }
            }
        break;

        case SM_SERVICE_DOMAIN_INTERFACE_EVENT_NODE_ENABLED:
        case SM_SERVICE_DOMAIN_INTERFACE_EVENT_AUDIT:
            if( !enabled )
            {
                snprintf( reason_text, sizeof(reason_text), "%s disabled",
                          interface->interface_name );
            }

            if( !enabled )
            {
                error = sm_service_domain_interface_fsm_set_state( 
                                                interface->service_domain,
                                                interface->service_domain_interface,
                                                SM_INTERFACE_STATE_DISABLED,
                                                reason_text );
                if( SM_OKAY != error )
                {
                    DPRINTFE( "Set state (%s) of service domain (%s) "
                              "interface (%s) failed, error=%s.",
                              sm_interface_state_str( SM_INTERFACE_STATE_DISABLED ),
                              interface->service_domain,
                              interface->service_domain_interface,
                              sm_error_str( error ) );
                    return( error );
                }
            }
        break;

        case SM_SERVICE_DOMAIN_INTERFACE_EVENT_NOT_IN_USE:
            snprintf( reason_text, sizeof(reason_text), "interface %s "
                          "not in use", interface->interface_name );
            error = sm_service_domain_interface_fsm_set_state(
                                        interface->service_domain,
                                        interface->service_domain_interface,
                                        SM_INTERFACE_STATE_NOT_IN_USE,
                                        reason_text );
            if( SM_OKAY != error )
            {
                DPRINTFE( "Set state (%s) of service domain (%s) "
                          "interface (%s) failed, error=%s.",
                          sm_interface_state_str( SM_INTERFACE_STATE_ENABLED ),
                          interface->service_domain,
                          interface->service_domain_interface,
                          sm_error_str( error ) );
                return( error );
            }
        break;

        default:
            DPRINTFD( "Service domain (%s) interface (%s) ignoring event (%s).",
                      interface->service_domain,
                      interface->service_domain_interface,
                      sm_service_domain_interface_event_str( event ) );
        break;
    }

    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Domain Interface Enabled State - Initialize
// ===================================================
SmErrorT sm_service_domain_interface_enabled_state_initialize( void )
{
    return( SM_OKAY );
}
// ****************************************************************************

// ****************************************************************************
// Service Domain Interface Enabled State - Finalize
// =================================================
SmErrorT sm_service_domain_interface_enabled_state_finalize( void )
{
    return( SM_OKAY );
}
// ****************************************************************************
