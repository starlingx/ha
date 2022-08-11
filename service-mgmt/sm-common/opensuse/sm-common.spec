Summary: Service Management Common
Name: sm-common
Version: 1.0.0
Release: 1
License: Apache-2.0
Group: System/Base
URL: https://www.starlingx.io
Source0: %{name}-%{version}.tar.gz

BuildRequires: glib2-devel
BuildRequires: sqlite-devel
BuildRequires: gcc
BuildRequires: util-linux
BuildRequires: libuuid-devel
BuildRequires: gcc-c++
BuildRequires: systemd-sysvinit
BuildRequires: insserv-compat

Requires: libamon1
Requires: /bin/sh
Requires: sqlite
Requires: util-linux
Requires: systemd
BuildRequires: systemd
BuildRequires: systemd-devel
Requires(post): systemd
Requires: %{name}-libs = %{version}-%{release}

%description
Service Managment Common

%package libs
Summary: Service Management Common - shared library fles
Group: System/Base

%description libs
Service Managment Common  This package contains shared libraries.

%package devel
Summary: Service Management Common - Development files
Group: Development/Libraries/Other
Requires: %{name}-libs = %{version}-%{release}

%description devel
Service Managment Common  This package contains symbolic links, header
files, and related items necessary for software development.

%package -n sm-eru
Summary: Service Management ERU
Group: System/Base
Requires: %{name}-libs = %{version}-%{release}

%description -n sm-eru
Service Managment ERU.

%prep
%setup -n %{name}-%{version}

%build
VER=%{version}

MAJOR=`echo $VER | awk -F . '{print $1}'`
MINOR=`echo $VER | awk -F . '{print $2}'`
make  VER=${VER} VER_MJR=$MAJOR %{?_smp_mflags}

%global _buildsubdir %{_builddir}/%{name}-%{version}

%install
rm -rf %{buildroot}
VER=%{version}
MAJOR=`echo $VER | awk -F . '{print $1}'`
MINOR=`echo $VER | awk -F . '{print $2}'`
make DEST_DIR=%{buildroot} BIN_DIR=%{_bindir} UNIT_DIR=%{_unitdir} LIB_DIR=%{_libdir} INC_DIR=%{_includedir} BUILDSUBDIR=%{_buildsubdir} VER=$VER VER_MJR=$MAJOR install

%pre -n sm-eru
%service_add_pre sm-eru.service sm-eru.target

%preun -n sm-eru
%service_del_preun sm-eru.service sm-eru.target

%post -n sm-eru
%service_add_post sm-eru.service sm-eru.target
/usr/bin/systemctl enable sm-eru.service

%postun -n sm-eru
%service_del_postun sm-eru.service sm-eru.target
/usr/bin/systemctl disable sm-eru.service

%post -n sm-common-libs
/sbin/ldconfig

%postun -n sm-common-libs
/sbin/ldconfig

%files
%license LICENSE
%defattr(-,root,root,-)

%files libs
%{_libdir}/*.so.*
%dir %{_sharedstatedir}/sm

%files -n sm-eru
%defattr(-,root,root,-)
%dir %{_sysconfdir}/init.d
%dir %{_sysconfdir}/pmon.d
%{_sysconfdir}/init.d/sm-eru
%config %{_sysconfdir}/pmon.d/sm-eru.conf
%{_bindir}/sm-eru
%{_bindir}/sm-eru-dump
%{_unitdir}/sm-eru.service

%files devel
%defattr(-,root,root,-)
%{_includedir}/*
%{_libdir}/*.so

%changelog
