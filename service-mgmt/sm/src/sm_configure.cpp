//
// Copyright (c) 2019 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#include "sm_configure.h"

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "sm_types.h"
#include "sm_debug.h"
#include "sm_node_api.h"
#include "sm_service_group_member_table.h"
#include "sm_service_table.h"
#include "sm_service_dependency_table.h"
#include "sm_service_api.h"
#include "sm_service_domain_assignment_table.h"
#include "sm_timer.h"
#include "sm_service_fsm.h"


// The behavior of a service is configured in multiple (>1) service groups has
// not been defined (no use case identified). Currently all services are
// configured in one service group per domain. Therefore if a service group member
// shall always be in the same provisioned state as the corresponding service.
// TODO: to remove the provisioned column in services table
//       services table should refer to (join) service_group_members table for provisioned status

// ****************************************************************************
// sm configure: provision service
// ================================
extern SmErrorT sm_provision_service( char service_group_name[], char service_name[] )
{
    SmErrorT error;
    SmServiceDomainAssignmentT* sdm;

    char hostname[SM_NODE_NAME_MAX_CHAR];
    char domain[] = "controller";

    DPRINTFI("Start provisioning %s:%s...", service_group_name, service_name);
    error = sm_node_api_get_hostname( hostname );
    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to get hostname");
        return error;
    }

    sdm = sm_service_domain_assignment_table_read(domain, hostname, service_group_name);
    if(NULL == sdm)
    {
        DPRINTFE("Failed to get service domain assignment controller:%s@%s", service_group_name, hostname);
        return SM_NOT_FOUND;
    }

    error = sm_service_group_member_provision(service_group_name, service_name);
    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to provision service group member %s:%s", service_group_name, service_name);
        return error;
    }

    error = sm_service_provision(service_name);
    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to provision service %s", service_name);
        return error;
    }

    error = sm_service_dependency_table_load();
    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to reload service dependency");
        return error;
    }

    switch(sdm->desired_state)
    {
        case SM_SERVICE_GROUP_STATE_ACTIVE:
            error = sm_service_api_go_active(service_name);
            break;
        case SM_SERVICE_GROUP_STATE_STANDBY:
            error = sm_service_api_go_standby(service_name);
            break;
        case SM_SERVICE_GROUP_STATE_DISABLED:
            error = sm_service_api_disable(service_name);
            break;
        default:
            error = SM_FAILED;
            DPRINTFE("Unexpected service domain assignment desired state %s",
                      sm_service_group_state_str(sdm->desired_state));
    }
    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to set service state");
        return error;
    }

    error = sm_service_api_audit(service_name);
    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to audit service %s. Error %s", service_name, sm_error_str(error));
        return error;
    }

    DPRINTFI("%s:%s is provisioned successfully", service_group_name, service_name);
    return SM_OKAY;

}
// ****************************************************************************

void static stop_all_service_timers(SmServiceT& service)
{
    SmTimerIdT* timers[] = {
        &service.fail_countdown_timer_id,
        &service.audit_timer_id,
        &service.action_timer_id,
        &service.action_state_timer_id,
        &service.pid_file_audit_timer_id
    };
    SmTimerIdT* timer;

    for(unsigned int i = 0; i < sizeof(timers) / sizeof(SmTimerIdT*); i++)
    {
        timer = timers[i];
        if( SM_TIMER_ID_INVALID != *timer )
        {
            sm_timer_deregister(*timer);
            *timer = SM_TIMER_ID_INVALID;
        }
    }
}

// ****************************************************************************
// sm configure: deprovision service
// ===============================
SmErrorT sm_deprovision_service( char service_group_name[], char service_name[] )
{
    SmErrorT error;
    DPRINTFI("Start deprovisioning %s:%s ...", service_group_name, service_name);

    SmServiceT* service = sm_service_table_read(service_name);
    if(NULL == service)
    {
        DPRINTFI("Service %s not found, already deprovisioned?", service_name);
        return SM_OKAY;
    }

    stop_all_service_timers(*service);

    error = sm_service_deprovision(service_name);
    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to deprovision service %s", service_name);
        return error;
    }

    error = sm_service_group_member_deprovision(service_group_name, service_name);
    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to deprovision service group member %s:%s", service_group_name, service_name);
        return error;
    }

    error = sm_service_dependency_table_load();
    if(SM_OKAY != error)
    {
        DPRINTFE("Failed to reload service dependency");
        return error;
    }

    error = sm_service_fsm_process_failure_deregister(service);
    if(SM_OKAY != error)
    {
        // By not able to deregister the process monitor routine, there will be an error log
        // nothing will go wrong. So log and continue as success
        DPRINTFE("Failed to deregister process failure monitor for service %s", service_name);
    }

    DPRINTFI("%s:%s is deprovisioned successfully", service_group_name, service_name);

    return SM_OKAY;
}
// ****************************************************************************
