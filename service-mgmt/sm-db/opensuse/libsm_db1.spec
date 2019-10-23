Summary: Service Management Databases
Name: libsm_db1
Version: 1.0.0
Release: 5
License: Apache-2.0
Group: System/Base
URL: https://www.starlingx.io
Source0: %{name}-%{version}.tar.gz

BuildRequires: gcc-c++
BuildRequires: sm-common-devel
BuildRequires: glib2-devel
BuildRequires: glibc
BuildRequires: sqlite3-devel
BuildRequires: libuuid-devel
BuildRequires: libsqlite3-0
BuildRequires: sqlite3

Requires: sqlite3

%description
The StarlingX Service Managment Databases

%package devel
Summary: Service Management Databases - Development files
Group: Development/Libraries/Other
Requires: %{name} = %{version}-%{release}

%description devel
Service Managment Databases  This package contains symbolic links, header
files, and related items necessary for software development.

%prep
%setup -n %{name}-%{version}

%build
sqlite3 database/sm.db < database/create_sm_db.sql
sqlite3 database/sm.hb.db < database/create_sm_hb_db.sql
VER=%{version}
export SUSE_ASNEEDED=0
MAJOR=`echo $VER | awk -F . '{print $1}'`
make VER=${VER} VER_MJR=$MAJOR

%install
VER=%{version}
MAJOR=`echo $VER | awk -F . '{print $1}'`
make DEST_DIR=$RPM_BUILD_ROOT VER=$VER VER_MJR=$MAJOR install

%post
/sbin/ldconfig

%postun
/sbin/ldconfig

%files
%license LICENSE
%defattr(-,root,root,-)
%dir %{_sharedstatedir}/sm/patches
%{_libdir}/libsm_db.so.1
%{_libdir}/libsm_db.so.1.0.0
%config(noreplace) %{_sharedstatedir}/sm/sm.hb.db
%config(noreplace) %{_sharedstatedir}/sm/sm.db
%{_sharedstatedir}/sm/patches/sm-patch.sql

%files devel
%defattr(-,root,root,-)
%{_libdir}/libsm_db.so
%{_includedir}/*.h

%changelog
