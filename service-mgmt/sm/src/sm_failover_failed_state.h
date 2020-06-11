//
// Copyright (c) 2020 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#ifndef __SM_FAILOVER_FAILED_STATE_H__
#define __SM_FAILOVER_FAILED_STATE_H__
#include "sm_types.h"
#include "sm_failover_fsm.h"
#include "sm_timer.h"

class SmFailoverFailedState : public SmFSMState
{
    public:
        SmFailoverFailedState(SmFailoverFSM& fsm);
        virtual ~SmFailoverFailedState();
        SmErrorT enter_state();
        SmErrorT exit_state();

    protected:
        SmErrorT event_handler(SmFailoverEventT event, const ISmFSMEventData* event_data);

    private:
        SmTimerIdT _failed_state_audit_timer_id;
        static bool _failed_state_audit(SmTimerIdT timer_id, int64_t user_data);
        SmErrorT _register_timer();
        SmErrorT _deregister_timer();

        int _log_throttle ;
};


#endif //__SM_FAILOVER_FAILED_STATE_H__
