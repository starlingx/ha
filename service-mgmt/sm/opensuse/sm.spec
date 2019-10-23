Summary: Service Management
Name: sm
Version: 1.0.0
Release: 2
License: Apache-2.0
Group: System/Base
URL: https://www.starlingx.io
Source0: %{name}-%{version}.tar.gz

# Patches no applied to upstream yet.
Patch0: 0001-Change-shebang-to-help-rpm-runtime-dependency-detect.patch

BuildRequires: gcc-c++
BuildRequires: fm-common-dev
BuildRequires: libsm_db1-devel
BuildRequires: sm-common-devel
BuildRequires: mtce-devel
BuildRequires: glib2-devel
BuildRequires: glibc
BuildRequires: sqlite3-devel
BuildRequires: gcc
BuildRequires: libuuid-devel
BuildRequires: libjson-c3
BuildRequires: libjson-c-devel
BuildRequires: openssl-devel
BuildRequires: systemd-sysvinit
BuildRequires: insserv-compat

BuildRequires: systemd
BuildRequires: systemd-devel
Requires(post): systemd
Requires(preun): systemd

# Needed for /etc/init.d, can be removed when we go fully systemd
Requires: aaa_base
# Needed for /etc/logrotate.d
Requires: logrotate
# for collect stuff
Requires: time


%description
The StarlingX Service Managment system.

%prep
%setup -n %{name}-%{version}
%patch0 -p3

%build
VER=%{version}
MAJOR=`echo $VER | awk -F . '{print $1}'`
make -j"%(nproc)"

%install
rm -rf %{buildroot}
VER=%{version}
MAJOR=`echo $VER | awk -F . '{print $1}'`
make DEST_DIR=%{buildroot} UNIT_DIR=%{_unitdir} install

%pre
%service_add_pre sm.service
%service_add_pre sm-shutdown.service

%preun
%service_del_preun sm.service
%service_del_preun sm-shutdown.service

%post
%service_add_post sm.service
%service_add_post sm-shutdown.service
/usr/bin/systemctl enable sm.service >/dev/null 2>&1
/usr/bin/systemctl enable sm-shutdown.service >/dev/null 2>&1

%postun
%service_del_postun sm.service
%service_del_postun sm-shutdown.service

%files
%license LICENSE
%defattr(-,root,root,-)
%dir %{_sysconfdir}/pmon.d
%{_unitdir}/*
%{_bindir}/sm
/usr/local/sbin/sm-notify
/usr/local/sbin/sm-troubleshoot
/usr/local/sbin/sm-notification
%{_sysconfdir}/init.d/sm
%{_sysconfdir}/init.d/sm-shutdown
%config %{_sysconfdir}/pmon.d/sm.conf
%config %{_sysconfdir}/logrotate.d/sm.logrotate

%changelog
