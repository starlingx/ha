Summary: Service Management Client and CLI
Name: sm-client
Version: 1.0.0
Release: 4
BuildArch: noarch
License: Apache-2.0
Group: System/Base
URL: https://www.starlingx.io
Source0: %{name}-%{version}.tar.gz

%define debug_package %{nil}

BuildRequires: python
BuildRequires: python-setuptools
BuildRequires: fdupes
Requires: python-six
Requires: python-pyparsing
Requires: python-httplib2
Requires: python-PrettyTable
Requires: python-keystoneclient

%description
Service Management Client and command line interface.

%prep
%setup -n %{name}-%{version}/%{name}

%build
%{__python2} setup.py build

%install
%global _buildsubdir %{_builddir}/%{name}-%{version}/%{name}
%{__python2} setup.py install -O1 --skip-build --root %{buildroot}
install -d %{buildroot}/usr/bin
ls %{_builddir}/
install -m 755 %{_buildsubdir}/usr/bin/smc %{buildroot}/usr/bin
%fdupes %{buildroot}/usr/lib/python2.7/site-packages/sm_client/

%files
%defattr(-,root,root,-)
%dir /usr/lib/python2.7/site-packages/sm_client
/usr/lib/python2.7/site-packages/sm_client/*
/usr/bin/smc
%dir /usr/lib/python2.7/site-packages/sm_client-1.0.0-py2.7.egg-info
/usr/lib/python2.7/site-packages/sm_client-1.0.0-py2.7.egg-info/*

%changelog
