Summary: Miscellaneous OCF scripts added by StarlingX
Name: stx-ocf-scripts
Version: 1.0
Release: %{tis_patch_ver}%{?_tis_dist}
License: Apache-2.0
Group: base
Packager: Wind River <info@windriver.com>
URL: unknown

Source0: %{name}-%{version}.tar.gz

BuildArch:     noarch
Requires: openstack-ras 

%description
Miscellaneous OCF scripts added by StarlingX

%prep
%setup
%build

%install
install -d -m 755 ${RPM_BUILD_ROOT}/usr/lib/ocf/resource.d/openstack
install -p -D -m 755 ocf/* ${RPM_BUILD_ROOT}/usr/lib/ocf/resource.d/openstack/

%files
%dir %attr(0755,root,root) /usr/lib/ocf/resource.d/openstack
%defattr(-,root,root,-)
/usr/lib/ocf/resource.d/openstack/*

