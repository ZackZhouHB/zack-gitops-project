---
layout: post
title:  " RedHat Identity management (IdM) "
date:   2024-04-04 11:15:29 +1100
categories: jekyll Cat2
---

<b> About Linux Identity management </b>

In Linux, user and permission management is crucial for maintaining system security and controlling access to files, directories, and resources.

Redhat provides such enterprise-level solution called redhat Identity management (IdM), also with its opensource free version called freeIPA, to offer centralized authentication, authorization, and identity management services such as Single Sign-On (SSO), Role-Based Access Control (RBAC), Identity Federation, Integration with Microsoft AD and AAD, also can cross-cloud access with AWS SSO as external identity provider. 

when a company facing challenge to manage its Linux environments across local and public cloud, RedHat Identity management can be the solution to achieve: 

- With Local AD and Azure AD (AAD) Integration

- With AWS SSO Integration as externel identity provider

- Cross-account access and cross-cloud access


<b> Typical AD User Authentication Flow across AWS and IdM would be: </b>


- When a user attempts to access AWS resources, they first authenticate through Azure AD using their Azure AD credentials.

- Azure AD authenticates the user and issues a security token.

- The user accesses AWS SSO, which is configured to use Red Hat IDM as an identity provider.

- AWS SSO redirects the user to the Red Hat IDM authentication page.

- The user enters their Red Hat IDM credentials and authenticates against the IdM server.

- Red Hat IDM validates the user's credentials and issues a SAML assertion to AWS SSO.

- AWS SSO validates the SAML assertion and grants the user access to the requested AWS resources.



<b> freeIPA: the opensource version of RedHat IdM </b>

Here I am going to install and configure a local lab IdM portal using the opensource version of RedHat IdM called "freeIPA", with 3 linux boxes to validate the user permission and client hosts (both CentOS and Ubuntu) enrollment, requirement and design as bellow:

- freeIPA Server: freeipa-server.zackz.oonline 11.0.1.150 (CentOS 7.9)

- freeIPA Client1: freeipa-client1.zackz.oonline 11.0.1.151 (CentOS 7.9)

- freeIPA Client2: freeipa-client2.zackz.oonline 11.0.1.72 (Ubuntu 22.04)

<b> freeIPA server installation </b>

on freeIPA Server freeipa-server.zackz.oonline 11.0.1.150 (CentOS 7.9)

{% highlight shell %}
# set hostname with domain
hostnamectl set-hostname freeipa-server.zackz.oonline

# add 3 hosts to /etc/hosts
echo 11.0.1.150 freeipa-server.zackz.oonline  ipa >> /etc/hosts
echo 11.0.1.151 freeipa-client1.zackz.oonline ipa >> /etc/hosts
echo 11.0.1.72  freeipa-client2.zackz.oonline ipa >> /etc/hosts

# install ipa-server
yum install ipa-server bind-dyndb-ldap ipa-server-dns

# Configure ipa-server and DNS, here set ipa console and domain admin passwd
ipa-server-install --setup-dns

# configure firewall rules and services
firewall-cmd --permanent --add-service={http,https,ldap,ldaps,kerberos,dns,kpasswd,ntp}
firewall-cmd --permanent --add-service freeipa-ldap
firewall-cmd --permanent --add-service freeipa-ldaps
firewall-cmd --reload

# check ipastatus
[root@freeipa ~]# ipactl status
Directory Service: RUNNING
krb5kdc Service: RUNNING
kadmin Service: RUNNING
httpd Service: RUNNING
ipa-custodia Service: RUNNING
ntpd Service: RUNNING
pki-tomcatd Service: RUNNING
ipa-otpd Service: RUNNING
ipa: INFO: The ipactl command was successful


# Obtain a Kerberos ticket for the Kerberos admin user and Verify the ticket
kinit admin
klist

Ticket cache: KEYRING:persistent:0:0
Default principal: admin@ZACKZ.OONLINE

Valid starting     Expires            Service principal
04/04/24 22:17:29  05/04/24 22:02:43  HTTP/freeipa-server.zackz.oonline@ZACKZ.OONLINE

# check content of /etc/resolv.conf
cat /etc/resolv.conf
search zackz.oonline
nameserver 127.0.0.1

# Configure FreeIPA for User Authentication

yum install -y vsftpd
systemctl enable vsftpd && systemctl start vsftpd
firewall-cmd --permanent --add-service=ftp
firewall-cmd --reload


# copy CA certificate of the IPA server to the FTP site
cp /root/cacert.p12 /var/ftp/pub

# Configure default login shell to Bash and Create Users
ipa config-mod --defaultshell=/bin/bash
ipa user-add alice --first=alice --last=abernathy --password
ipa user-add vince --first=vincent --last=valentine --password

# add client hosts 
ipa host-add --ip-address 11.0.1.151 freeipa-client1.zackz.oonline
ipa host-add --ip-address 11.0.1.72 freeipa-client2.zackz.oonline

# create NFS service entry in the IdM domain
ipa service-add nfs/freeipa-client1.zackz.oonline
ipa service-add nfs/freeipa-client2.zackz.oonline

# add entry to the keytab file /etc/krb5.keytab
kadmin.local
Authenticating as principal admin/admin@RHCE.LOCAL with password.
kadmin.local:  ktadd nfs/freeipa-client1.zackz.oonline
kadmin.local:  ktadd nfs/freeipa-client2.zackz.oonline
kadmin.local:  quit

# verify keytab file
[root@freeipa-server pub]# klist -k
Keytab name: FILE:/etc/krb5.keytab
KVNO Principal
---- --------------------------------------------------------------------------
   2 host/freeipa-server.zackz.oonline@ZACKZ.OONLINE
   2 host/freeipa-server.zackz.oonline@ZACKZ.OONLINE
   2 host/freeipa-server.zackz.oonline@ZACKZ.OONLINE
   2 host/freeipa-server.zackz.oonline@ZACKZ.OONLINE
   2 host/freeipa-server.zackz.oonline@ZACKZ.OONLINE
   2 host/freeipa-server.zackz.oonline@ZACKZ.OONLINE
   1 nfs/freeipa-client2.zackz.oonline@ZACKZ.OONLINE
   1 nfs/freeipa-client2.zackz.oonline@ZACKZ.OONLINE
   1 nfs/freeipa-client2.zackz.oonline@ZACKZ.OONLINE
   1 nfs/freeipa-client2.zackz.oonline@ZACKZ.OONLINE
   1 nfs/freeipa-client2.zackz.oonline@ZACKZ.OONLINE
   1 nfs/freeipa-client2.zackz.oonline@ZACKZ.OONLINE
   1 nfs/freeipa-client1.zackz.oonline@ZACKZ.OONLINE
   1 nfs/freeipa-client1.zackz.oonline@ZACKZ.OONLINE
   1 nfs/freeipa-client1.zackz.oonline@ZACKZ.OONLINE
   1 nfs/freeipa-client1.zackz.oonline@ZACKZ.OONLINE
   1 nfs/freeipa-client1.zackz.oonline@ZACKZ.OONLINE
   1 nfs/freeipa-client1.zackz.oonline@ZACKZ.OONLINE


# Generate keys to copy over to NFS systems, chmod to Make the keytab file accessible to FTP clients
ipa-getkeytab -s freeipa-server.zackz.oonline -p nfs/freeipa-client2.zackz.oonline -k /var/ftp/pub/freeipa-client2.keytab
ipa-getkeytab -s freeipa-server.zackz.oonline -p nfs/freeipa-client1.zackz.oonline -k /var/ftp/pub/freeipa-client1.keytab
chmod 644 /var/ftp/pub/*.keytab

# Configure DNS
ipa dnszone-mod --allow-transfer=11.0.1.0/24 zackz.oonline
ipa dnsrecord-add zackz.oonline vhost1 --ttl=3600 --a-ip-address=11.0.1.151
ipa dnsrecord-add zackz.oonline dynamic1 --ttl=3600 --a-ip-address=11.0.1.151
ipa dnsrecord-add zackz.oonline @ --mx-rec="0 freeipa-server.zackz.oonline."

{% endhighlight %}


<b> Console login </b>

login freeIPA console with serverIP or DNS name

![image tooltip here](/assets/linuxidm1.png)

list the 2 users "alice" and "vincent" previously created

![image tooltip here](/assets/linuxidm2.png)


<b> Add and enroll client hosts into IdM </b>

To add client hosts into freeIPA can be done via command or console, but to enroll the host can only be done via each client host by install "freeipa-client" and condigure domain. 

- For CentOS client (11.0.1.151 freeipa-client1.zackz.oonline) enrollment: 

{% highlight shell %}

# set client hostname with domain
hostnamectl set-hostname freeipa-client1.zackz.oonline

# add 3 hosts to /etc/hosts
echo 11.0.1.150 freeipa-server.zackz.oonline  ipa >> /etc/hosts
echo 11.0.1.151 freeipa-client1.zackz.oonline ipa >> /etc/hosts
echo 11.0.1.72  freeipa-client2.zackz.oonline ipa >> /etc/hosts


# install freeipa-client and manually configure domain
[root@freeipa-client1 ~]# ipa-client-install --mkhomedir
WARNING: ntpd time&date synchronization service will not be configured as
conflicting service (chronyd) is enabled
Use --force-ntpd option to disable it and force configuration of ntpd

DNS discovery failed to determine your DNS domain
Provide the domain name of your IPA server (ex: example.com): zackz.oonline
Provide your IPA server name (ex: ipa.example.com): freeipa-server.zackz.oonline
The failure to use DNS to find your IPA server indicates that your resolv.conf file is not properly configured.
Autodiscovery of servers for failover cannot work with this configuration.
If you proceed with the installation, services will be configured to always access the discovered server for all operations and will not fail over to other servers in case of failure.
Proceed with fixed values and no DNS discovery? [no]: yes
Client hostname: freeipa-client1.zackz.oonline
Realm: ZACKZ.OONLINE
DNS Domain: zackz.oonline
IPA Server: freeipa-server.zackz.oonline
BaseDN: dc=zackz,dc=oonline

Continue to configure the system with these values? [no]: yes
Skipping synchronizing time with NTP server.
User authorized to enroll computers: admin
Password for admin@ZACKZ.OONLINE: 
Successfully retrieved CA cert
    Subject:     CN=Certificate Authority,O=ZACKZ.OONLINE
    Issuer:      CN=Certificate Authority,O=ZACKZ.OONLINE
    Valid From:  2024-04-04 10:45:20
    Valid Until: 2044-04-04 11:45:20

Enrolled in IPA realm ZACKZ.OONLINE
Created /etc/ipa/default.conf
New SSSD config will be created
Configured sudoers in /etc/nsswitch.conf
Configured /etc/sssd/sssd.conf
trying https://freeipa-server.zackz.oonline/ipa/json
[try 1]: Forwarding 'schema' to json server 'https://freeipa-server.zackz.oonline/ipa/json'
trying https://freeipa-server.zackz.oonline/ipa/session/json
[try 1]: Forwarding 'ping' to json server 'https://freeipa-server.zackz.oonline/ipa/session/json'
[try 1]: Forwarding 'ca_is_enabled' to json server 'https://freeipa-server.zackz.oonline/ipa/session/json'
Systemwide CA database updated.
Hostname (freeipa-client1.zackz.oonline) does not have A/AAAA record.
Failed to update DNS records.
Missing reverse record(s) for address(es): 11.0.1.151.
Adding SSH public key from /etc/ssh/ssh_host_rsa_key.pub
Adding SSH public key from /etc/ssh/ssh_host_ecdsa_key.pub
Adding SSH public key from /etc/ssh/ssh_host_ed25519_key.pub
[try 1]: Forwarding 'host_mod' to json server 'https://freeipa-server.zackz.oonline/ipa/session/json'
Could not update DNS SSHFP records.
SSSD enabled
Configured /etc/openldap/ldap.conf
Unable to find 'admin' user with 'getent passwd admin@zackz.oonline'!
Unable to reliably detect configuration. Check NSS setup manually.
Configured /etc/ssh/ssh_config
Configured /etc/ssh/sshd_config
Configuring zackz.oonline as NIS domain.
Configured /etc/krb5.conf for IPA realm ZACKZ.OONLINE
Client configuration complete.
The ipa-client-install command was successful


{% endhighlight %}

- for Ubuntu client host (11.0.1.72 freeipa-client2.zackz.oonline) enrollment:

First back to freeIPA server, add DNS record for Ubuntu
{% highlight shell %}

# add DNS record for Ubuntu client on freeIPA server
ipa dnsrecord-add hwdomain.io ubuntu-node.hwdomain.io --a-rec 192.168.10.50

{% endhighlight %}

Then login Ubuntu host to install freeipa-client and enroll:

{% highlight shell %}

# set hostname 
hostnamectl set-hostname freeipa-client2.zackz.oonline

# add 3 hosts to /etc/hosts
echo 11.0.1.150 freeipa-server.zackz.oonline  ipa >> /etc/hosts
echo 11.0.1.151 freeipa-client1.zackz.oonline ipa >> /etc/hosts
echo 11.0.1.72  freeipa-client2.zackz.oonline ipa >> /etc/hosts

# install ipa client
apt update && apt install freeipa-client oddjob-mkhomedir

# add ubuntu client to freeIPA server
ipa-client-install --hostname=`hostname -f` --mkhomedir /
--server=freeipa-server.zackz.oonline /
--domain zackz.online /
--realm ZACKZ.OONLINE

# change PAM profile to enable "Create a home directory on login" 
pam-auth-update
{% endhighlight %}

now back to console, the 2 client hosts had been added and enrolled into freeIPA server
![image tooltip here](/assets/linuxidm3.png)


- verify to use user "alice" and its passwd to ssh login to ubuntu client from freeIPA server

{% highlight shell %}
[root@freeipa-server ~]# ssh alice@freeipa-client2.zackz.oonline
Password: 
Welcome to Ubuntu 22.04.4 LTS (GNU/Linux 5.15.0-101-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/pro

  System information as of Thu Apr  4 01:02:00 PM UTC 2024

  System load:  0.0               Processes:              234
  Usage of /:   8.0% of 93.93GB   Users logged in:        1
  Memory usage: 11%               IPv4 address for ens33: 11.0.1.72
  Swap usage:   0%

 * Strictly confined Kubernetes makes edge and IoT secure. Learn how MicroK8s
   just raised the bar for easy, resilient and secure K8s cluster deployment.

   https://ubuntu.com/engage/secure-kubernetes-at-the-edge

Expanded Security Maintenance for Applications is not enabled.

18 updates can be applied immediately.
To see these additional updates run: apt list --upgradable

Enable ESM Apps to receive additional future security updates.
See https://ubuntu.com/esm or run: sudo pro status


Last login: Thu Apr  4 11:47:37 2024 from 11.0.1.150
alice@freeipa-client2:~$ id
uid=1239800001(alice) gid=1239800001(alice) groups=1239800001(alice)
alice@freeipa-client2:~$ 
{% endhighlight %}

<b> Conclusion</b>

Now we install Redhat IdM server and be able to enroll client hosts, looking at the user details, IdM using Kerberos for authentication, together with user group, policy, HBAC and Sudo roles, provides a flexible and robust authentication framework that supports multiple authentication mechanisms, enabling organizations to authenticate users securely across their Linux and Unix environments.

![image tooltip here](/assets/linuxidm5.png)

More info can be found via Freeipa workshop: https://freeipa.readthedocs.io/en/latest/workshop.html

Or from RedHat website: 
https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/managing_idm_users_groups_hosts_and_access_control_rules/index 