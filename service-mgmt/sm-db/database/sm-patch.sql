--THIS IS A VERY IMPORTANT SYSTEM FILE. MODIFYING THIS FILE MAY CAUSE UNEXPECTED BEHAVIOR.

-- SCST iSCSI gateway (scst-gw-exit), added after the release. A patched system
-- keeps its locally modified master database, so the service definition from
-- create_sm_db.sql would never reach Service Manager and stx-puppet's
-- sm-provision would update no rows. Every statement is idempotent: this file
-- runs each time the runtime database is rebuilt from the master copy.
INSERT INTO "SERVICE_GROUP_MEMBERS" SELECT (SELECT MAX(id) + 1 FROM "SERVICE_GROUP_MEMBERS"),'no','controller-services','scst-gw-exit','critical' WHERE NOT EXISTS (SELECT 1 FROM "SERVICE_GROUP_MEMBERS" WHERE NAME = 'controller-services' AND SERVICE_NAME = 'scst-gw-exit');
INSERT INTO "SERVICES" SELECT (SELECT MAX(id) + 1 FROM "SERVICES"), 'no','scst-gw-exit','initial','initial','none','none',2,1,90000,4,16,'' WHERE NOT EXISTS (SELECT 1 FROM "SERVICES" WHERE NAME = 'scst-gw-exit');
INSERT OR IGNORE INTO "SERVICE_DEPENDENCY" VALUES('action','scst-gw-exit','not-applicable','enable','drbd-platform','enabled-active');
INSERT OR IGNORE INTO "SERVICE_DEPENDENCY" VALUES('action','drbd-platform','not-applicable','disable','scst-gw-exit','disabled');
INSERT OR IGNORE INTO "SERVICE_DEPENDENCY" VALUES('action','scst-gw-exit','not-applicable','enable','platform-fs','enabled-active');
INSERT OR IGNORE INTO "SERVICE_DEPENDENCY" VALUES('action','platform-fs','not-applicable','disable','scst-gw-exit','disabled');
INSERT OR IGNORE INTO "SERVICE_DEPENDENCY" VALUES('action','scst-gw-exit','not-applicable','enable','cluster-host-ipv4','enabled-active');
INSERT OR IGNORE INTO "SERVICE_DEPENDENCY" VALUES('action','cluster-host-ipv4','not-applicable','disable','scst-gw-exit','disabled');
INSERT OR IGNORE INTO "SERVICE_DEPENDENCY" VALUES('action','scst-gw-exit','not-applicable','enable','cluster-host-ipv6','enabled-active');
INSERT OR IGNORE INTO "SERVICE_DEPENDENCY" VALUES('action','cluster-host-ipv6','not-applicable','disable','scst-gw-exit','disabled');
INSERT OR IGNORE INTO "SERVICE_ACTIONS" VALUES('scst-gw-exit','enable','lsb-script','','scst-gw-exit','start','',2,2,2,30,'');
INSERT OR IGNORE INTO "SERVICE_ACTIONS" VALUES('scst-gw-exit','disable','lsb-script','','scst-gw-exit','stop','',0,0,0,120,'');
INSERT OR IGNORE INTO "SERVICE_ACTIONS" VALUES('scst-gw-exit','audit-enabled','lsb-script','','scst-gw-exit','status','',2,4,4,15,60);
INSERT OR IGNORE INTO "SERVICE_ACTIONS" VALUES('scst-gw-exit','audit-disabled','lsb-script','','scst-gw-exit','status','',0,0,0,15,40);
