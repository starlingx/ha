#
# Copyright (c) 2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

ETC_DIR ?= /etc

build:
	@(cd src; make build VER=$(VER) VER_MJR=$(VER_MJR))

install:
	@(cd src; make DEST_DIR=$(DEST_DIR) BIN_DIR=$(BIN_DIR) LIB_DIR=$(LIB_DIR) INC_DIR=$(INC_DIR) VER=$(VER) VER_MJR=$(VER_MJR) install)
	@(cd scripts; make DEST_DIR=$(DEST_DIR) PMONDIR=$(PMONDIR) UNIT_DIR=$(UNIT_DIR) install)
	install -m 750 -d $(DEST_DIR)/usr
	install -m 750 -d $(DEST_DIR)/usr/bin
	install -m 750 -d $(DEST_DIR)/var/lib/sm
	install -m 750 -p -D $(BUILDSUBDIR)/src/sm_eru $(DEST_DIR)/$(BIN_DIR)/sm-eru
	install -m 750 -p -D $(BUILDSUBDIR)/src/sm_eru_dump $(DEST_DIR)/$(BIN_DIR)/sm-eru-dump
	install -m 644 -p -D $(BUILDSUBDIR)/scripts/sm-eru.service $(DEST_DIR)/$(UNIT_DIR)/sm-eru.service
	install -m 750 -d $(DEST_DIR)$(PMONDIR)
	install -m 640 -p -D $(BUILDSUBDIR)/scripts/sm-eru.conf $(DEST_DIR)$(PMONDIR)/sm-eru.conf
	install -m 750 -p -D $(BUILDSUBDIR)/scripts/sm-eru $(DEST_DIR)/$(ETC_DIR)/init.d/sm-eru

clean:
	@( cd src; make clean )
