//
// Copyright (c) 2019-2023 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#ifndef __SM_CONFIGURE_H__
#define __SM_CONFIGURE_H__

#include "sm_types.h"

#ifdef __cplusplus
extern "C" {
#endif

// ****************************************************************************
// system config: provision service
// ================================
extern SmErrorT sm_provision_service( char service_group_name[], char service_name[] );
// ****************************************************************************

// ****************************************************************************
// system config: deprovision service
// ===============================
extern SmErrorT sm_deprovision_service( char service_group_name[], char service_name[] );
// ****************************************************************************

// ****************************************************************************
// system config: provision_service_domain_interface
// ================================
extern SmErrorT sm_provision_service_domain_interface( char service_domain_name[], char interface_name[] );
// ****************************************************************************

// ****************************************************************************
// system config: deprovision_service_domain_interface
// ================================
extern SmErrorT sm_deprovision_service_domain_interface( char service_domain_name[], char interface_name[] );
// ****************************************************************************


#ifdef __cplusplus
}
#endif

#endif // __SM_CONFIGURE_H__
