---
title: "Ubuntu 18.04 to 22.04 in-place upgrade"
date: 2023-08-28T03:04:11Z
slug: ubuntu-18-04-to-22-04-in-place-upgrade
categories: ["DevOps"]
aliases: ["/post/60/"]
legacy_id: 60
---
My manage said we have many ubuntu 16.04, can you believe?

Every single Ubuntu LTS comes with 5 years of standard support. During those five years, bug fixes and security patches will be provided. Ubuntu 18.04 ‘Bionic Beaver’ is reaching End of Standard Support this May. So today we are going to run in-place upgrade for Ubuntu 18.04 LTS to 22.04 LTS.

[![image tooltip here](/images/ubt-upg1.png)](/images/ubt-upg1.png)

**Pre-upgrade checklist**

- Validate current OS version and running service (nginx)

```bash
# current OS version
root@ubuntu-test:~# cat /etc/os-release
NAME="Ubuntu"
VERSION="18.04.6 LTS (Bionic Beaver)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 18.04.6 LTS"
VERSION_ID="18.04"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
VERSION_CODENAME=bionic
UBUNTU_CODENAME=bionic

# nginx service status

root@ubuntu-test:~# echo "ubuntu-inplace-upgrade zack-testing-nginx-service!!"  >> /var/www/html/index.html
root@ubuntu-test:~# systemctl restart nginx
root@ubuntu-test:~# curl localhost
ubuntu-inplace-upgrade zack-testing-nginx-service!!
```

- Fully update the system

```bash
# update system
root@ubuntu-test:~# sudo apt update
Hit:1 http://au.archive.ubuntu.com/ubuntu bionic InRelease
Hit:2 http://au.archive.ubuntu.com/ubuntu bionic-updates InRelease
Hit:3 http://au.archive.ubuntu.com/ubuntu bionic-backports InRelease
Hit:4 http://au.archive.ubuntu.com/ubuntu bionic-security InRelease
Reading package lists... Done
Building dependency tree
Reading state information... Done
All packages are up to date.
root@ubuntu-test:~# sudo apt upgrade -y
Reading package lists... Done
Building dependency tree
Reading state information... Done
Calculating upgrade... Done
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.

# reboot system before upgrade
root@ubuntu-test:~# sudo do-release-upgrade
Checking for a new Ubuntu release
You have not rebooted after updating a package which requires a reboot. Please reboot before upgrading.
root@ubuntu-test:~# reboot
Connection closing...Socket close.
```

- Take full system backup

Here I took a VM snapshot before upgrade

**18.04 to 22.04 upgrade**

There is no direct upgrade path from 18.04 LTS to Ubuntu 22.04 LTS, so we go Ubuntu 20.04 LTS first and then to Ubuntu 22.04 LTS.

- First upgrade to 20.04

```bash
# run upgrade
root@ubuntu-test:~# sudo do-release-upgrade

This session appears to be running under ssh. It is not recommended
to perform a upgrade over ssh currently because in case of failure it
is harder to recover.

If you continue, an additional ssh daemon will be started at port
'1022'.
Do you want to continue?

Continue [yN] y

Starting additional sshd

Calculating the changes
  MarkInstall libfwupdplugin1:amd64 < none -> 1.5.11-0ubuntu1~20.04.2 @un uN Ib > FU=1
  Installing libxmlb1 as Depends of libfwupdplugin1
    MarkInstall libxmlb1:amd64 < none -> 0.1.15-2ubuntu1~20.04.1 @un uN > FU=0

Do you want to start the upgrade?

Continue [yN]  Details [d]y
```

- Allow service restart during upgrade

[![image tooltip here](/images/ubt-upg2.png)](/images/ubt-upg2.png)

- Reboot after upgrade

The installation and removing of packages may take some time, then reboot is required after upgrade completion.

```text
Purging configuration files for ebtables (2.0.11-3build1) ...
Purging configuration files for python3.6-minimal (3.6.9-1~18.04ubuntu1.12) ...
Purging configuration files for mlocate (0.26-3ubuntu3) ...
Processing triggers for dbus (1.12.16-2ubuntu2.3) ...
Processing triggers for systemd (245.4-4ubuntu3.23) ...

System upgrade is complete.

Restart required

To finish the upgrade, a restart is required.
If you select 'y' the system will be restarted.

Continue [yN] y
```

- Validate OS and service

```bash
# validate nginx service
root@ubuntu-test:~# curl localhost
ubuntu-inplace-upgrade  zack-testing-nginx-service!!
# validate OS version
root@ubuntu-test:~# cat /etc/os-release
NAME="Ubuntu"
VERSION="20.04.6 LTS (Focal Fossa)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 20.04.6 LTS"
VERSION_ID="20.04"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
VERSION_CODENAME=focal
UBUNTU_CODENAME=focal
```

- Then upgrade to 22.04

```bash
root@ubuntu-test:~# sudo apt update
Hit:1 http://au.archive.ubuntu.com/ubuntu focal InRelease
Hit:2 http://au.archive.ubuntu.com/ubuntu focal-updates InRelease
Hit:3 http://au.archive.ubuntu.com/ubuntu focal-backports InRelease
Hit:4 http://au.archive.ubuntu.com/ubuntu focal-security InRelease
Reading package lists... Done
Building dependency tree
Reading state information... Done
All packages are up to date.

root@ubuntu-test:~# sudo apt upgrade
Reading package lists... Done
Building dependency tree
Reading state information... Done
Calculating upgrade... Done
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.

root@ubuntu-test:~# sudo do-release-upgrade

# validate after upgrade
root@ubuntu-test:~# curl localhost
ubuntu-inplace-upgrade  zack-testing-nginx-service!!

root@ubuntu-test:~# lsb_release -a
No LSB modules are available.
Distributor ID:	Ubuntu
Description:	Ubuntu 22.04.4 LTS
Release:	22.04
Codename:	jammy
```

**Conclusion**

Now we complete the in-place Ubuntu OS release upgrade from 18.04 to 22.04. The whole upgrade took about 1 hour to finish, with several confirmations required during the upgrade process. The service nginx was running after each upgrade.
