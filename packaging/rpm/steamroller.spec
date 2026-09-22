Name:           steamroller
Version:        0.1.0
Release:        1%{?dist}
Summary:        Safe RHEL 9 remote patching precheck automation
License:        AGPL-3.0-or-later
URL:            https://github.com/markhawks/SteamRoller
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

Requires:       ansible-core
Requires:       bash
Requires:       python3

%description
SteamRoller provides conservative, auditable Ansible workflows for RHEL 9
managed hosts. This release contains read-only connectivity and precheck
automation. The control node may run RHEL 9 or RHEL 10.

%prep
%autosetup

%build

%install
install -d %{buildroot}/opt/steamroller/{bin,playbooks,roles,scripts}
install -d %{buildroot}%{_sysconfdir}/steamroller/inventories/dev
install -d %{buildroot}%{_localstatedir}/lib/steamroller/reports
install -d %{buildroot}%{_localstatedir}/log/steamroller
install -d %{buildroot}%{_bindir}

install -m 0755 bin/steamroller %{buildroot}/opt/steamroller/bin/steamroller
install -m 0755 scripts/render_summary.py %{buildroot}/opt/steamroller/scripts/render_summary.py
install -m 0755 scripts/show_config.py %{buildroot}/opt/steamroller/scripts/show_config.py
install -m 0755 scripts/validate_config.py %{buildroot}/opt/steamroller/scripts/validate_config.py
install -m 0755 scripts/list_reports.py %{buildroot}/opt/steamroller/scripts/list_reports.py
install -m 0644 VERSION README.md %{buildroot}/opt/steamroller/
cp -a playbooks/. %{buildroot}/opt/steamroller/playbooks/
cp -a roles/. %{buildroot}/opt/steamroller/roles/
install -m 0644 config/ansible.cfg %{buildroot}%{_sysconfdir}/steamroller/ansible.cfg
install -m 0644 config/steamroller.yml %{buildroot}%{_sysconfdir}/steamroller/steamroller.yml
install -m 0644 config/hosts.yml.example \
    %{buildroot}%{_sysconfdir}/steamroller/inventories/dev/hosts.yml
ln -s /opt/steamroller/bin/steamroller %{buildroot}%{_bindir}/steamroller

%files
%license LICENSE
%doc README.md
/opt/steamroller
%{_bindir}/steamroller
%dir %{_sysconfdir}/steamroller
%dir %{_sysconfdir}/steamroller/inventories
%dir %{_sysconfdir}/steamroller/inventories/dev
%config(noreplace) %{_sysconfdir}/steamroller/ansible.cfg
%config(noreplace) %{_sysconfdir}/steamroller/steamroller.yml
%config(noreplace) %{_sysconfdir}/steamroller/inventories/dev/hosts.yml
%dir %{_localstatedir}/lib/steamroller
%dir %{_localstatedir}/lib/steamroller/reports
%dir %{_localstatedir}/log/steamroller

%changelog
* Thu Sep 17 2026 SteamRoller Team <root@localhost> - 0.1.0-1
- Initial Phase 1 package structure
