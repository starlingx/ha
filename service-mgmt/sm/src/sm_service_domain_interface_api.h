//
// Copyright (c) 2014 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#ifndef __SM_SERVICE_DOMAIN_INTERFACE_API_H__
#define __SM_SERVICE_DOMAIN_INTERFACE_API_H__

#include "sm_types.h"
#include "sm_service_domain_interface_table.h"

#ifdef __cplusplus
extern "C" {
#endif

// ****************************************************************************
// Service Domain Interface API - Node Enabled
// ===========================================
extern SmErrorT sm_service_domain_interface_api_node_enabled( void );
// ****************************************************************************

// ****************************************************************************
// Service Domain Interface API - Node Disabled
// ============================================
extern SmErrorT sm_service_domain_interface_api_node_disabled( void );
// ****************************************************************************

// ****************************************************************************
// Service Domain Interface API - Audit
// ====================================
extern SmErrorT sm_service_domain_interface_api_audit( void );
// ****************************************************************************

// ****************************************************************************
// Service Domain Interface API - Provision
// ====================================
extern SmErrorT sm_service_domain_interface_api_provisioned( SmServiceDomainInterfaceT* interface );
// ****************************************************************************

// ****************************************************************************
// Service Domain Interface API - Deprovision
// ====================================
extern SmErrorT sm_service_domain_interface_api_deprovisioned( SmServiceDomainInterfaceT* interface );
// ****************************************************************************

// ****************************************************************************
// Service Domain Interface API - Initialize 
// =========================================
extern SmErrorT sm_service_domain_interface_api_initialize( void );
// ****************************************************************************

// ****************************************************************************
// Service Domain Interface API - Finalize 
// =======================================
extern SmErrorT sm_service_domain_interface_api_finalize( void );
// ****************************************************************************

#ifdef __cplusplus
}
#endif

#endif // __SM_SERVICE_DOMAIN_INTERFACE_API_H__
