#
## SPDX-License-Identifier: Apache-2.0
#

SW_VERSION="$(shell grep SW_VERSION /usr/include/build_info.h | cut -d ' ' -f 3)"

install:
	install -d ${DEST_DIR}/etc/sm/${SW_VERSION}
	install -d ${DEST_DIR}/var/lib/sm/patches
	install -d ${DEST_DIR}/usr/share/sm/patches
	install sm.hb.db ${DEST_DIR}/etc/sm/${SW_VERSION}
	install sm.db ${DEST_DIR}/etc/sm/${SW_VERSION}
	install -m 644 sm-patch.sql ${DEST_DIR}/usr/share/sm/patches
