#
# Copyright (c) 2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

INCLUDES =-I$(STAGING_DIR)/usr/include/glib-2.0
INCLUDES+=-I$(STAGING_DIR)/usr/lib64/glib-2.0/include -I.
INCLUDES+=-I$(STAGING_DIR)/usr/lib/x86_64-linux-gnu/glib-2.0/include

SRCS=sm_types.c
SRCS+=sm_debug.c
SRCS+=sm_debug_thread.c
SRCS+=sm_trap.c
SRCS+=sm_trap_thread.c
SRCS+=sm_thread_health.c
SRCS+=sm_utils.c
SRCS+=sm_node_utils.c
SRCS+=sm_node_stats.c
SRCS+=sm_selobj.c
SRCS+=sm_time.c
SRCS+=sm_timer.c
SRCS+=sm_netlink.c
SRCS+=sm_hw.c
SRCS+=sm_uuid.c
SRCS+=sm_sha512.c
SRCS+=sm_eru_db.c
SRCS+=sm_util_types.c

OBJS = $(SRCS:.c=.o)
CCFLAGS= -fPIC -g -O2 -Wall -Werror -Wno-restrict -Wno-format-truncation -std=c++11
SW_VERSION="$(shell grep SW_VERSION /usr/include/build_info.h | cut -d ' ' -f 3)"
EXTRACCFLAGS= -D__STDC_FORMAT_MACROS -DSW_VERSION=\"$(SW_VERSION)\"
EXTRACCFLAGS+= -Wformat -Wformat-security
LDLIBS= -lsqlite3 -lglib-2.0 -lgmodule-2.0 -luuid -lrt -lpthread
LDFLAGS = -shared -rdynamic

build: libsm_common.so sm_eru sm_eru_dump

.c.o:
	$(CXX) $(INCLUDES) $(CCFLAGS) $(EXTRACCFLAGS) -c $< -o $@

libsm_common.so: libsm_common.so.$(VER_MJR)
	ln -sf $^ $@

libsm_common.so.$(VER_MJR): libsm_common.so.$(VER)
	ln -sf $^ $@

libsm_common.so.$(VER): ${OBJS}
	$(CXX) ${LDFLAGS} -Wl,--start-group $(LDLIBS) -Wl,-soname,libsm_common.so.$(VER_MJR) -o $@ $^

sm_eru: libsm_common.so
	$(CXX) $(INCLUDES) $(CCFLAGS) $(EXTRACCFLAGS) $(OBJS) sm_eru_process.c sm_eru_main.c $(LDLIBS) -L./ -lsm_common -o sm_eru

sm_eru_dump: libsm_common.so
	$(CXX) $(INCLUDES) $(CCFLAGS) $(EXTRACCFLAGS) $(OBJS) sm_eru_dump.c $(LDLIBS) -L./ -lsm_common -o sm_eru_dump

install:
	# install of these 3 are in the .spec file so that they can be
	# renamed with '-' like they are in the bitbake file.
	#
	# install -d $(DEST_DIR)$(BIN_DIR)
	# install sm_eru sm_eru_dump $(DEST_DIR)$(BIN_DIR)
	install -d $(DEST_DIR)$(LIB_DIR)
	install libsm_common.so.${VER} $(DEST_DIR)$(LIB_DIR)
	cp -P libsm_common.so libsm_common.so.$(VER_MJR) $(DEST_DIR)$(LIB_DIR)
	install -d $(DEST_DIR)$(INC_DIR)
	install -m 644 *.h $(DEST_DIR)$(INC_DIR)

clean:
	rm -f *.o *.so *.so.*
