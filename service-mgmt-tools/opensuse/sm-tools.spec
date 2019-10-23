Summary:        Service Management Tools
Name:           sm-tools
Version:        1.0.0
Release:        0
License:        Apache-2.0
Group:          Development/Tools/Other
URL:            https://opendev.org/starlingx/metal
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  python
BuildRequires:  python-pip
BuildRequires:  python-setuptools

BuildArch:      noarch

%description
StarlingX Service Management Tools

%prep
%setup -n %{name}-%{version}/%{name}

%build
python2 setup.py build

%install
python2 setup.py install -O1 --skip-build --root %{buildroot}

%files
%defattr(-,root,root,-)
%dir "%{_prefix}/lib/python2.7/site-packages/sm_tools"
%{_prefix}/lib/python2.7/site-packages/sm_tools/*
%dir "%{_prefix}/lib/python2.7/site-packages/sm_tools-1.0.0-py2.7.egg-info"
%{_prefix}/lib/python2.7/site-packages/sm_tools-1.0.0-py2.7.egg-info/*
%{_bindir}/*

%changelog
