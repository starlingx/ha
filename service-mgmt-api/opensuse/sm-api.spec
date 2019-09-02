Summary: Service Management API
Name: sm-api
Version: 1.0.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: System/Packages
URL: https://opendev.org/starlingx/ha/
Source0: %{name}-%{version}.tar.gz

%define debug_package %{nil}

BuildRequires: python
BuildRequires: python-setuptools
BuildRequires: python2-pip
BuildRequires: util-linux
# BuildRequires systemd is to get %%_unitdir I think
BuildRequires: systemd
BuildRequires: systemd-devel
%if 0%{?suse_version}
BuildRequires: gcc-c++
BuildRequires: systemd-sysvinit
BuildRequires: insserv-compat
%endif
Requires: python2-six
# Needed for %%{_sysconfdir}/init.d, can be removed when we go fully systemd
Requires: aaa_base
# Needed for %%{_sysconfdir}/pmon.d
Requires:  libamon1

%description
The Service Management API

%prep
%setup -n %{name}-%{version}/%{name}

%build
%{__python2} setup.py build

%install
%global _buildsubdir %{_builddir}/%{name}-%{version}/%{name}
%{__python2} setup.py install -O1 --skip-build --root %{buildroot}
install -d %{buildroot}%{_sysconfdir}/sm
install -d %{buildroot}%{_sysconfdir}/init.d
install -d %{buildroot}%{_sysconfdir}/pmon.d
install -d %{buildroot}%{_sysconfdir}/sm-api
install -d %{buildroot}%{_unitdir}
install -m 644 %{_buildsubdir}/scripts/sm_api.ini %{buildroot}%{_sysconfdir}/sm
install -m 755 %{_buildsubdir}/scripts/sm-api %{buildroot}%{_sysconfdir}/init.d
install -m 644 %{_buildsubdir}/scripts/sm-api.service %{buildroot}%{_unitdir}
install -m 644 %{_buildsubdir}/scripts/sm-api.conf %{buildroot}%{_sysconfdir}/pmon.d
install -m 644 %{_buildsubdir}%{_sysconfdir}/sm-api/policy.json %{buildroot}%{_sysconfdir}/sm-api

%post
%{_bindir}/systemctl enable sm-api.service >/dev/null 2>&1

%files
%dir %{_sysconfdir}/pmon.d
%dir %{_sysconfdir}/sm-api
%defattr(-,root,root,-)
%dir "%{_prefix}/lib/python2.7/site-packages/sm_api"
%{_prefix}/lib/python2.7/site-packages/sm_api/*
%dir "%{_prefix}/lib/python2.7/site-packages/sm_api-1.0.0-py2.7.egg-info"
%{_prefix}/lib/python2.7/site-packages/sm_api-1.0.0-py2.7.egg-info/*
"%{_bindir}/sm-api"
%dir "%{_sysconfdir}/sm"
"%{_sysconfdir}/init.d/sm-api"
"%{_sysconfdir}/pmon.d/sm-api.conf"
"%{_sysconfdir}/sm-api/policy.json"
"%{_sysconfdir}/sm/sm_api.ini"
%{_unitdir}/*

%changelog
