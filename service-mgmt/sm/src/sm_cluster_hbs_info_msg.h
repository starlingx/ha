//
// Copyright (c) 2018,2023 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
#ifndef __SM_CLUSTER_HBS_INFO_MSG_H__
#define __SM_CLUSTER_HBS_INFO_MSG_H__
#include <list>
#include <pthread.h>
#include <stdio.h>
#include "mtceHbsCluster.h"
#include "sm_types.h"
#include "sm_timer.h"
#include "sm_util_types.h"
#include "sm_limits.h"

// ****************************************************************************
// struct SmClusterHbsInfoT
//        Store cluster hbs info
// ========================
struct _SmClusterHbsInfoT
{
    bool storage0_responding;
    int number_of_node_reachable;
    int number_of_node_enabled;
    bool sm_heartbeat_fail;
    _SmClusterHbsInfoT() : storage0_responding(false),
                           number_of_node_reachable(0),
                           number_of_node_enabled(0),
                           sm_heartbeat_fail(false)
    {
    }
};
typedef struct _SmClusterHbsInfoT SmClusterHbsInfoT;

bool operator==(const SmClusterHbsInfoT& lhs, const SmClusterHbsInfoT& rhs);
bool operator!=(const SmClusterHbsInfoT& lhs, const SmClusterHbsInfoT& rhs);

const unsigned int max_controllers = 2;

// ****************************************************************************
// struct SmClusterHbsInfoT
//        Store cluster hbs info aggregate data from all (max_controllers)
//        controllers
// ========================
typedef struct
{
    SmClusterHbsInfoT controllers[max_controllers];
    bool storage0_enabled;
    time_t last_update;
}SmClusterHbsStateT;

bool operator==(const SmClusterHbsStateT& lhs, const SmClusterHbsStateT& rhs);
bool operator!=(const SmClusterHbsStateT& lhs, const SmClusterHbsStateT& rhs);

inline bool is_valid(const SmClusterHbsStateT& state)
{
    return state.last_update > 0;
}

void log_cluster_hbs_state(const SmClusterHbsStateT& state);

typedef void(*cluster_hbs_query_ready_callback)();
// ****************************************************************************
// class SmClusterHbsInfoMsg -
//       handle requesting/receiving and processing cluster hbs info from hbsAgent.
//
//       hbsAgent sends hbs cluster info when there is a change in the cluster.
//       Keep track of most up-to-date info prior to a failure occurs.
//       Provide async query with callback when hbsAgent response is received
// ========================
class SmClusterHbsInfoMsg
{
    public:
        typedef std::list<cluster_hbs_query_ready_callback> hbs_query_respond_callback;
        static SmErrorT initialize();
        static SmErrorT finalize();
        static const SmClusterHbsStateT& get_current_state();
        static const SmClusterHbsStateT& get_previous_state();
        static bool cluster_hbs_info_query(cluster_hbs_query_ready_callback callback = NULL, bool alive_pulse = false);
        static bool send_alive_pulse();
        static void dump_hbs_record(FILE* fp);
        static int get_peer_controller_index();
        static int get_this_controller_index();

    private:
        static int _sock;
        static unsigned short _last_reqid;
        static pthread_mutex_t sm_cluster_hbs_mutex;
        static SmClusterHbsStateT _cluster_hbs_state_current;
        static SmClusterHbsStateT _cluster_hbs_state_previous;
        static hbs_query_respond_callback _callbacks;
        static SmErrorT open_socket();
        static SmErrorT get_controller_index();

        static SmErrorT _get_address(struct sockaddr_in* addr);
        static void _cluster_hbs_info_msg_received( int selobj, int64_t user_data );
        static bool _process_cluster_hbs_history(mtce_hbs_cluster_history_type history,
                                                 SmClusterHbsStateT& state);

        static char server_port[SM_CONFIGURATION_VALUE_MAX_CHAR + 1];
        static char client_port[SM_CONFIGURATION_VALUE_MAX_CHAR + 1];
        static int peer_controller_index;
        static int this_controller_index;
};

#endif // __SM_CLUSTER_HBS_INFO_MSG_H__
