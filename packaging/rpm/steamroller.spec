Name:           steamroller
Version:        0.3.0
Release:        1%{?dist}
Summary:        Safe RHEL 9 remote patching precheck automation
License:        AGPL-3.0-or-later
URL:            https://github.com/markhawks/SteamRoller
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

Requires:       ansible-core
Requires:       bash
Requires:       iputils
Requires:       python3
Requires:       python3-pyyaml

%description
SteamRoller provides conservative, auditable Ansible workflows for RHEL 9
managed hosts, including assessment, interactive single-host package updates,
controlled reboot, and persistent evidence. The control node may run RHEL 9
or RHEL 10.

%prep
%autosetup

%build

%install
install -d %{buildroot}/opt/steamroller/{bin,playbooks,roles,scripts}
install -d %{buildroot}%{_sysconfdir}/steamroller/inventories/dev
install -d -m 0700 %{buildroot}%{_sysconfdir}/steamroller/ssh-keys
install -d %{buildroot}%{_localstatedir}/lib/steamroller/reports
install -d %{buildroot}%{_localstatedir}/log/steamroller
install -d %{buildroot}%{_bindir}
install -d %{buildroot}%{_datadir}/bash-completion/completions

install -m 0755 bin/steamroller %{buildroot}/opt/steamroller/bin/steamroller
install -m 0755 scripts/render_summary.py %{buildroot}/opt/steamroller/scripts/render_summary.py
install -m 0755 scripts/show_config.py %{buildroot}/opt/steamroller/scripts/show_config.py
install -m 0755 scripts/validate_config.py %{buildroot}/opt/steamroller/scripts/validate_config.py
install -m 0755 scripts/list_reports.py %{buildroot}/opt/steamroller/scripts/list_reports.py
install -m 0755 scripts/manage_inventory.py %{buildroot}/opt/steamroller/scripts/manage_inventory.py
install -m 0755 scripts/resolve_ssh_key.py %{buildroot}/opt/steamroller/scripts/resolve_ssh_key.py
install -m 0755 scripts/inventory_hostnames.py %{buildroot}/opt/steamroller/scripts/inventory_hostnames.py
install -m 0755 scripts/run_dnf_update.py %{buildroot}/opt/steamroller/scripts/run_dnf_update.py
install -m 0644 VERSION README.md %{buildroot}/opt/steamroller/
install -m 0644 completions/steamroller.bash \
    %{buildroot}%{_datadir}/bash-completion/completions/steamroller
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
%{_datadir}/bash-completion/completions/steamroller
%dir %{_sysconfdir}/steamroller
%dir %{_sysconfdir}/steamroller/inventories
%dir %{_sysconfdir}/steamroller/inventories/dev
%dir %attr(0700,root,root) %{_sysconfdir}/steamroller/ssh-keys
%config(noreplace) %{_sysconfdir}/steamroller/ansible.cfg
%config(noreplace) %{_sysconfdir}/steamroller/steamroller.yml
%config(noreplace) %{_sysconfdir}/steamroller/inventories/dev/hosts.yml
%dir %{_localstatedir}/lib/steamroller
%dir %{_localstatedir}/lib/steamroller/reports
%dir %{_localstatedir}/log/steamroller

%changelog
* Wed Sep 23 2026 SteamRoller Team <root@localhost> - 0.3.0-1
- Add interactive single-host DNF update, audited force mode, PostgreSQL unit
  protection, post-update validation, and suggested reboot command

* Tue Sep 22 2026 SteamRoller Team <root@localhost> - 0.2.0-1
- Add inventory management, Satellite and PostgreSQL checks, repository
  quarantine integration, SSH profiles, Bash completion, and controlled reboot

* Thu Sep 17 2026 SteamRoller Team <root@localhost> - 0.1.0-1
- Initial Phase 1 package structure
