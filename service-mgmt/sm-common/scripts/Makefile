#
# SPDX-License-Identifier: Apache-2.0
#

install:
	install -d $(DEST_DIR)$(UNIT_DIR)
	install -m 644 *.service $(DEST_DIR)$(UNIT_DIR) 
	install -d $(DEST_DIR)/etc/init.d
	install sm-eru $(DEST_DIR)/etc/init.d
	install -d $(DEST_DIR)$(PMONDIR)
	install *.conf $(DEST_DIR)$(PMONDIR)

