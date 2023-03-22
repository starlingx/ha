//
// Copyright (c) 2017-2023 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#ifndef __SM_FAILOVER_H__
#define __SM_FAILOVER_H__
#include <stdio.h>
#include <stdint.h>
#include "sm_types.h"
#include "sm_service_domain_interface_table.h"
#include "sm_db_nodes.h"
#include "sm_failover_ss.h"
#ifdef __cplusplus
extern "C" {
#endif

typedef struct
{
    char* service_domain;
    char* service_domain_interface;
    char* interface_name;
    SmInterfaceStateT interface_state;
}SmFailoverInterfaceT;


typedef enum
{
    SM_FAILOVER_DEGRADE_SOURCE_SERVICE_GROUP = 1,
    SM_FAILOVER_DEGRADE_SOURCE_IF_DOWN = 2
}SmFailoverDegradeSourceT;


// ****************************************************************************
// initialize mutex
// ==============
extern SmErrorT sm_failover_mutex_initialize ( void );
// ****************************************************************************

// ****************************************************************************
// destroy mutex
// ==============
extern SmErrorT sm_failover_mutex_finalize ( void );
// ****************************************************************************

// ****************************************************************************
// Failover - check
// ==================
extern void sm_failover_check();
// ****************************************************************************

// ****************************************************************************
// Failover - audit
// ==================
extern void sm_failover_audit(bool recheck);
// ****************************************************************************

// ****************************************************************************
// Failover - lost hello msg
// ==================
extern void sm_failover_lost_hello_msg();
// ****************************************************************************


// ****************************************************************************
// Failover - hello msg restore
// ==================
extern void sm_failover_hello_msg_restore();
// ****************************************************************************

// ****************************************************************************
// Failover - lost heartbeat
// ==================
extern void sm_failover_lost_heartbeat( SmFailoverInterfaceT* interface );
// ****************************************************************************


// ****************************************************************************
// Failover - heartbeat restore
// ==================
extern void sm_failover_heartbeat_restore( SmFailoverInterfaceT* interface );
// ****************************************************************************


// ****************************************************************************
// Failover - interface down
// ==================
extern void sm_failover_interface_down( const char* const interface_name );
// ****************************************************************************


// ****************************************************************************
// Failover - interface down
// ==================
extern void sm_failover_interface_up( const char* const interface_name );
// ****************************************************************************

// ****************************************************************************
// Failover - node info update for peer
extern void sm_failover_node_info_update(const char node_name[],
        SmHeartbeatMsgNodeInfoT node_info);
// ****************************************************************************

// ****************************************************************************
// Failover - get local interface state flags
extern SmHeartbeatMsgNodeInfoT sm_failover_get_host_node_info_flags();
// ****************************************************************************

// ****************************************************************************
// Failover - action
// ==================
SmErrorT sm_failover_action( void );
// ****************************************************************************

// ****************************************************************************
// Failover - degrade
// ==================
SmErrorT sm_failover_degrade(SmFailoverDegradeSourceT source);
// ****************************************************************************

// ****************************************************************************
// Failover - degraded clear
// ==================
SmErrorT sm_failover_degrade_clear(SmFailoverDegradeSourceT source);
// ****************************************************************************

// ****************************************************************************
// Failover - get node
// ==================
SmErrorT sm_failover_get_node(char* node_name, SmDbNodeT& node);
// ****************************************************************************

// ****************************************************************************
// Failover - get node interface info
// ==================
SmFailoverInterfaceStateT sm_failover_get_interface_info(SmInterfaceTypeT interface_type);
// ****************************************************************************


// ****************************************************************************
// Failover - get peer node info flags
// ==================
SmHeartbeatMsgNodeInfoT sm_failover_get_peer_node_info_flags();
// ****************************************************************************


// ****************************************************************************
// Failover - set system to scheduled status
// ==================
SmErrorT sm_failover_set_system(const SmSystemFailoverStatus& failover_status);
// ****************************************************************************

// ****************************************************************************
// Failover - active self
// =======================
SmErrorT sm_failover_activate_self();
// ****************************************************************************

// ****************************************************************************
// Failover - disable peer node
// =======================
SmErrorT sm_failover_disable_peer();
// ****************************************************************************

// ****************************************************************************
// Failover - is active controller
// ==================
bool sm_is_active_controller();
// ****************************************************************************

// ****************************************************************************

// ****************************************************************************
// Failover - dump state
// ==================
extern void sm_failover_dump_state(FILE* fp);
// ****************************************************************************

// ****************************************************************************
// Failover - Initialize
// ======================
extern SmErrorT sm_failover_initialize( void );
// ****************************************************************************

// ****************************************************************************
// Failover - Finalize
// ====================
extern SmErrorT sm_failover_finalize( void );
// ****************************************************************************

#ifdef __cplusplus
}
#endif

#endif

