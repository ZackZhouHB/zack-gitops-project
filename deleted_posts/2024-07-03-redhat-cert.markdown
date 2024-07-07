---
layout: post
title:  "RedHat Certified RHCSA & RHCE"
date:   2024-07-03 11:15:29 +1100
categories: jekyll Cat2
---

<b>The RedHat Certs</b>

Recently I have been working on Redhat certifications to add to all my [<b>professional certs on Credly</b>](https://www.credly.com/users/zhou-zack/badges).

Here are the RedHat exam results and preparations.

![image tooltip here](/assets/rhcert1.png)

- Red Hat Certified System Administrator (RHCSA)

{% highlight shell %}
# RHCSA
# Red Hat Enterprise Linux 9

1. network
 
hostnamectl nmcli -h
 
 
hostnamectl set-hostname node1.domain250.example.com
 
nmcli connection modify "Wired connection 1" ipv4.method manual ipv4.dns 172.25.250.254 ipv4.addresses 172.25.250.100/24 ipv4.gateway 172.25.250.254 autoconnect yes
 
 
nmcli connection up "Wired connection 1"
 
 
2. yum repo
 
yum repolist
yum repoinfo
 
vim /etc/yum/yum.repos.d/rhcsa.repo
 
[base]
name=base
baseurl=http://content/rhel9.0/x86_64/dvd/BaseOS
gpgcheck=0
enabled=1
 
[app]
name=app
baseurl=http://content/rhel9.0/x86_64/dvd/appstream
gpgcheck=0
enabled=1
 
validate:
 
3. SElinux

semanage -h
man semanage port
man semanage fcontext   # !!!

ls -Z /var/www/html  # check se content

systemctl status httpd

semanage port -a -t http_port_t -p tcp 82

firewall-cmd  --add-port=82/tcp --permanent
firewall-cmd  --add-service=http --permanent
firewall-cmd --reload

semanage fcontext -m -t httpd_sys_content_t /var/www/html/file1  # !!!

restorecon -Rv /var/www/html/  # -R v must !!

systemctl restart httpd
systemctl enable httpd
systemctl status httpd

4. add user and group
 
groupadd sysmgrs
useradd harry -G sysmgrs
useradd natasha -G sysmgrs
useradd sarah -s /sbin/nologin
 
passwd harry
 
5. cron

crontab -e -u harry
 
23 14 * * * "/usr/bin/echo hello"


* * * * * command_to_be_executed
- - - - -
| | | | |
| | | | +----- Day of the week (0 - 7) (Sunday=0 or 7)
| | | +------- Month (1 - 12) (January=1, December=12)
| | +--------- Day of the month (1 - 31)
| +----------- Hour (0 - 23)
+------------- Minute (0 - 59)
 
6. collborative directory
 
 
mkdir /home/managers
chgrp sysmgrs /home/managers
chmod 2770 /home/managers
 
2770: group = rwx, owner = rwx, user = none specialpermission = group

Three special permission bits: setuid (4), setgid (2), and sticky (1).

setuid (4): When set on an executable file, this bit allows the file to be executed with the permissions of the file owner.

chmod 4755 /path/to/executable
The permissions of the executable file become rwsr-xr-x.
The s in the owner’s execute position (rws) indicates the setuid bit is set.

setgid (2): When set on a directory, files created in the directory inherit the group ID of the directory, rather than the group ID of the user who created the file.
chmod 2770 /home/managers
The permissions of the directory become rwxrws---.
The s in the group’s execute position (rws) indicates the setgid bit is set.
Any file created in /home/managers will have its group set to the group of the directory (managers).
rwx (7) for the owner means the owner has read, write, and execute permissions.
rws (7) for the group means the group has read, write, and execute permissions, and the setgid bit is set (indicated by s).
--- (0) for others means no permissions for others.

sticky (1): When set on a directory, users can only delete or rename files within that directory if they are the owner of the file or the directory.
chmod 1777 /tmp
The permissions of the directory become rwxrwxrwt.
The t in the others’ execute position (rwt) indicates the sticky bit is set.
This is often used in directories like /tmp to prevent users from deleting each other’s files.

setuid + setgid (4 + 2 = 6):
chmod 6755 /path/to/executable
The permissions become rwsr-sr-x.

setgid + sticky (2 + 1 = 3):
chmod 3770 /home/shared
The permissions become rwxrws--t.

7. NTP

yum search ntp

vim /etc/chrony.conf

server materials.example.com iburst

systemctl restart chronyd

8. autofs

id remoteuser1

yum install autofs -y
yum install nfs-utils

showmount -e materials.example.com

vim /etc/auto.master

/rhome /etc/autofs.misc

vim /etc/autofs.misc

remoteuser1     -rw     materials.example.com:/rhome/remoteuser1
remoteuser1 	-fstype=nfs,rw 	materials.example.com:/rhome/remoteuser1

systemctl restart autofs

validate 

from other machine
ssh remoteuser1@node1
cd /rhome
cd remoteuser1
df -h

mount | grep rhome

9. user with uid

useradd -u 3533 manalo
passwd manalo

10. find file by user

find -h
man find

mkdir /root/findfiles

find -user jacques -exec cp -a {} /root/findfiles \;  # need to be remembered

11. grep line from file

cat /usr/share/xml/iso-codes/iso_639_3.xml | grep ng > /root/list

12. tar bzip2 and gzip

tar -cvjf /root/backup.tar.bz2 /usr/local  # j need to be remembered

tar -cvzf /root/backup.tar.gz /usr/local  # z for gz 

tar -xjf backup.tar.bz2  # untar bz2

tar -xzf backup.tar.gz   # untar gz 


validate 

file /root/backup.tar.bz2


13. podman build

use root to :

yum search container

yum install container-tools.noarch -y  # need to be done first !!


ssh wallah@node1 ## very important

wget http://classroom/Containerfile

podman login -u admin -p redhat321 registry.lab.example.com

man podman build

podman build -t pdf .



14. container as a service 

as user wallah

sudo mkdir /opt/file
sudo mkdir /opt/progress

sudo chown wallah:wallah /opt/file
sudo chown wallah:wallah /opt/progress

podman run -d --name ascii2pdf -v /opt/file:/dir1 -v /opt/progress:/dir2 pdf  # --name and -d !!!

podman ps

mkdir -p ~/.config/systemd/user # -p 

cd ~/.config/systemd/user

podman generate systemd -n ascii2pdf -f --new  # podman generate systemd --help

podman stop ascii2pdf
podman container rm ascii2pdf



loginctl --help

loginctl enable-linger wallah
loginctl show-user wallah


systemctl --user daemon-reload
systemctl --user start container-ascii2pdf
systemctl --user enable container-ascii2pdf

validate:

sudo reboot

podman ps



15. sudo no password

visudo 

%sysmgrs       ALL=(ALL)       NOPASSWD: ALL 

validate 

su - natasha

sudo cat /etc/shadow

16. break root 


add rw rd.break  #  need to be remembered

chroot /sysroot
passwd root

touch /.autorelabel  # need to be remembered
sync

exit
reboot

17. configure yum repo

18. logic volume size

lvextend -L 230M /dev/myvol/vo # need remember

blkid /dev/mapper/myvol-vo: UUID="d68a6907-91b6-4ca4-b736-e143936954b8" BLOCK_SIZE="1024" TYPE="ext4"  # type

resize2fs /dev/myvol/vo  # if ext4

# xfs_growfs /dev/myvol/vo  # if xfs  !!!

19. SWAP

lsblk  # check device
    # decide which device to go

fdisk /dev/sdc

n # create new
last sector +512M
# write

mkswap /dev/sdc1   # initialize 

vim /etc/fstab 
/dev/vdb3 swap swap defaults 0 0 # add new swap to boot 

swapon /dev/sdd1
swapon -a  # activate all swap
swapon # list all activated swap

20. VG LV

lsblk  # check device
    # decide which device to go

fdisk /dev/sdc
n # new
p # primary
2 # default partition
last  60x16mb=960mb +1200M
w # write

lsblk  # check device now should with new sdc2 with 1.2GB

vgcreate -h
man vgcreate 
vgcreate -s 16M qagroup /dev/sdc2  # cerate pv with #  name : qagroup, # -s to define each physical extent size pv size 16M # use /dev/sdc2

lvcreate -h
man lvcreate 
lvcreate -l 60 -n qa qagroup
lvscan

mkfs.  # check which type 
# yum provides */mkfs.vfat

mkfs.vfat /dev/qagroup/qa

mkdir /mnt/qa

vim /etc/fstab
/dev/qagroup/qa /mnt/qa vfat defaults 0 0    # not vdd1, /dev/qagroup/qa , typy xfat

mount -a   # remember

df-Th


21. tuned

yum -y install tuned
systemctl enable tuned
systemctl restart tuned
tuned-adm active
tuned-adm recommend

tuned-adm profile virtual-guest
tuned-adm active
{% endhighlight %}

- Red Hat Certified Engineer (RHCE)

{% highlight shell %}

# RHCE
# Ansible Automation Platform 2.2
# Red Hat Enterprise Linux 9
ssh greg@control

Q1: install ansible
pwd 

# install ansible core and navigator

sudo yum install ansible-core -y
sudo yum install ansible-navigator.noarch -y

# define user greg's ansible folder
# with inventory file
# generate ansible.cfg from default cat /etc/ansible/ansible.cfg
# create folders for mycollections and roles

mkdir ansible
cd ansible
touch inventory

mkdir -p mycollections
mkdir roles

[greg@control ansible]$ ll

-rw-r--r--. 1 greg greg 54183 Jul  1 06:31 ansible.cfg
-rw-r--r--. 1 greg greg    96 Jul  1 06:20 inventory
drwxr-xr-x. 2 greg greg     6 Jul  1 06:26 mycollection
drwxr-xr-x. 2 greg greg     6 Jul  1 06:26 roles

cat /etc/ansible/ansible.cfg

ansible-config init --disabled -t all > ansible.cfg

# define defaults for remote_user, inventory, host_key_checking, collection_path and roles_path

vim ansible.cfg

[defaults]

inventory = /home/greg/ansible/inventory
remote_user = greg
host_key_checking = False
collections_path = /home/greg/ansible/mycollection:~/.ansible/collections:/usr/share/ansible/collections
roles_path = /home/greg/ansible/roles:~/.ansible/roles:/usr/share/ansible/roles:/etc/ansible/roles

[privilege_escalation]
become=True

# define inventory, use : children to define a group in another group

vim inventory

[dev]
node1

[test]
node2

[prod]
node3
node4

[balancers]
node5

[webservers:children]
prod

Validation:

ansible --version

ansible-inventory --graph
ansible all -a "hostname"

podman login -u admin -p redhat utility.lab.example.com

ansible-navigator images
ansible-navigator collections

###########################################################
Q2: yum_repository

# search yum module 
ansible-doc -l | grep yum
ansible-doc yum_repository

vim yum_repo.yml

---
- name: Add multiple repositories into the same file (1/2)
  hosts: all
  tasks:
  - ansible.builtin.yum_repository:
      name: EX294_BASE
      description: EX294 base software
      baseurl: http://content/rhel9.0/x86_64/dvd/BaseOS
      gpgcheck: yes
      enabled: yes
      gpgkey: http://content/rhel9.0/x86_64/dvd/RPM-GPG-KEY-redhat-release
 
  - ansible.builtin.yum_repository:
      name: EX294_STREAM
      description: EX294 stream software
      gpgkey: http://content/rhel9.0/x86_64/dvd/RPM-GPG-KEY-redhat-release
      baseurl: http://content/rhel9.0/x86_64/dvd/AppStream
      enabled: yes
      gpgcheck: yes

ansible-playbook --syntax-check yum_repo.yml

ansible-navigator run yum_repo.yml -m stdout

ansible all -a "yum repoinfo"
ansible all -a "yum install ftp -y"

Q3: package

ansible-doc yum

vim packages.yml


---
- name: php
  hosts: dev,test,prod
  tasks:
  - ansible.builtin.yum:
      name: "{{ packages }}"
      state: present # add state
    vars:     
      packages:
      - php   
      - mariadb

- name: devtools
  hosts: dev
  tasks:
  - ansible.builtin.yum:
      name: "@RPM Development Tools" # where the @ symbol indicates that "Development Tools" is a package group
      state: present # add state

- name: install dev update
  hosts: dev
  tasks:
  - ansible.builtin.yum:
      name: '*'
      state: latest

ansible-navigator run -m stdout packages.yml

ansible-playbook --syntax-check packages.yml


validate:

ansible dev -a "php --version"
ansible test -a "mariadb --version"
ansible dev -a "yum update"
ansible dev -a "yum grouplist"  # need remember

Q4: selinux roles

yum search roles
sudo yum install rhel-system-roles.noarch -y  # remember to search role

ansible-galaxy list            # when role = galaxy to list installed roles
# /home/greg/ansible/roles
# /usr/share/ansible/roles
- rhel-system-roles.selinux

# go /usr/share/doc tp find example

cp /usr/share/doc/rhel-system-roles/selinux/example-selinux-playbook.yml /home/greg/ansible/selinux.yml

vim /home/greg/ansible/selinux.yml

remove and keep:

vars: # keep 

tasks: 
    block


---
- hosts: all
  become: true
  become_method: sudo
  become_user: root
  vars:
    # Use "targeted" SELinux policy type
    selinux_policy: targeted
    # Set "enforcing" mode
    selinux_state: enforcing
    # Switch some SELinux booleans
  tasks:
    - name: execute the role and catch errors
      block:
        - name: Include selinux role
          include_role:
            name: rhel-system-roles.selinux
      rescue:
        # Fail if failed for a different reason than selinux_reboot_required.
        - name: handle errors
          fail:
            msg: "role failed"
          when: not selinux_reboot_required

        - name: restart managed host
          reboot:

        - name: wait for managed host to come back
          wait_for_connection:
            delay: 10
            timeout: 300

        - name: reapply the role
          include_role:
            name: rhel-system-roles.selinux

ansible-playbook --syntax-check selinux.yml

USE ansible-playbook
ansible-playbook selinux.yml


Validate:

# getenforce
ansible all -a "getenforce"
# /ect/selinux/config, use grep -E `^SELINUX=` 
ansible all -a "grep -E '^SELINUX=' /etc/selinux/config"


Q5: install collections

ansible-galaxy collection install -r -p

vim requirements.yml  # need remember !! all as yml

---
collections:
- name: http://classroom/materials/redhat-insights-1.0.7.tar.gz
- name: http://classroom/materials/community-general-5.5.0.tar.gz
- name: http://classroom/materials/redhat-rhel_system_roles-1.19.3.tar.gz

ansible-galaxy collection install -r requirements.yml -p /home/greg/ansible/mycollection

validation:

ansible-navigator collections
ansible-galaxy collection list

Q6: Galaxy install roles


ansible-galaxy role install --help

vim /home/greg/ansible/roles/requirements.yml

# no roles here !!!
---
- src: http://classroom/materials/haproxy.tar
  name: balancer
- src: http://classroom/materials/phpinfo.tar
  name: phpinfo

ansible-galaxy role install -r /home/greg/ansible/roles/requirements.yml -p /home/greg/ansible/roles/

validate:
ansible-galaxy list
# /home/greg/ansible/roles
- balancer, (unknown version)
- phpinfo, (unknown version)

ll /home/greg/ansible/roles/
total 4
drwxr-xr-x. 9 greg greg 122 Jul  1 07:35 balancer
drwxr-xr-x. 9 greg greg 118 Jul  1 07:35 phpinfo
-rw-r--r--. 1 greg greg 129 Jul  1 07:34 requirements.yml

Q7: galaxy init role apache

# initiate apache role, remember the path
ansible-galaxy role init roles/apache

# get fact by setup module, search for "ansible_nodename" and "ansible_default_ipv4"
ansible dev -m setup > xxx.txt
vim xxx.txt
/nodename
/ansible_default_ipv4

# create file "index.html.j2" under roles/apache/templates/ to define content
# use {{ vars }} to define build in vars for ansible

vim roles/apache/templates/index.html.j2
Welcome to {{ ansible_nodename }} on {{ ansible_default_ipv4.address }}

# check for tree for apache role
tree roles/apache

# add task in /roles/apache/tasks/main.yml
vim /home/greg/ansible/roles/apache/tasks/main.yml

# search for yum module to install httpd and firewalld
# search for systemd module to enable and start httpd and firewalld service
# search for command module, use cmd to pass shell command to add firewall-cmd for http service and reload
# use -template with src and dest to define j2 template
# ansible-navigator collections
# go ansible.posix
# go firewalld  / EXAMPLES  !!! immediate: yes
---
- name: Install the latest version of Apache
  ansible.builtin.yum:
    name: httpd
    state: latest

- name: Enable and start service httpd
  ansible.builtin.systemd:
    name: httpd
    enabled: yes
    state: started

- name: Ensure firewalld is installed
  ansible.builtin.yum:
    name: firewalld
    state: present

- name: Ensure firewalld is running and enabled
  ansible.builtin.systemd:
    name: firewalld
    state: started
    enabled: yes

#- name: enable http on firewalld                         
#  ansible.builtin.command: 
#    cmd: firewall-cmd --permanent --add-service=http

#- name: reload firewalld
#  ansible.builtin.command: 
#    cmd: firewall-cmd --reload

- name: Start apache
  ansible.posix.firewalld:  # 注意防火墙中Apache服务名不是httpd
    service: http
    permanent: yes
    state: enabled
    immediate: yes  # immediate


- template:
    src: index.html.j2
    dest: /var/www/html/index.html

# create a apache.yml to use the role

vim /home/greg/ansible/apache.yml

---
- name: apache role
  hosts: webservers
  roles:
  - apache

# run apache.yml to apply the role
ansible-navigator run apache.yml -m stdout

validate 

go browser
http://node3
http://node4


Q8: use role "phpinfo" and "balancer" from galaxy

vim /home/greg/ansible/roles.yml

---
- name: balacer role
  hosts: balancers
  roles:
  - balancer

- name: phpinfo role
  hosts: webservers
  roles:
  - phpinfo

ansible-navigator run roles.yml -m stdout

validate:

go browser

http://node5
http://node5

http://node3/hello.php
http://node4/hello.php

Q9: Create and use LV

ansible-navigator doc

ansible-navigator doc community.general.system.lvol
ansible-navigator doc community.general.system.filesystem

ansible-doc debug

vim /xxx.txt
/ find lvm
ansible_lvm.vgs.research

/home/greg/ansible/lv.yml

---
- name: lv
  hosts: all
  tasks:
  - block  # remember
    - name: Create a logical volume of 1500m        
      community.general.lvol:  
        vg: research           
        lv: data               
        size: 1500             
 
    - name: Create a ext4 filesystem
      community.general.filesystem:
        fstype: ext4           
        dev: /dev/research/data

    rescue: # rescue indentation 
    - name: Create a logical volume of 800m        
      community.general.lvol:  
        vg: research           
        lv: data               
        size: 800             
 
    - name: Create a ext4 filesystem
      community.general.filesystem:
        fstype: ext4           
        dev: /dev/research/data
    
    - ansible.builtin.debug:
        msg: Could not create logical volume of that size
      when: ansible_lvm.vgs.research is defined   # vim setup for ansible fact 

  - ansible.builtin.debug:           # ~~ remember indentation
      msg: Volume group done not exist
    when: ansible_lvm.vgs.research is not defined       

ansible-playbook --syntax-check lv.yml
ansible-navigator run lv.yml -m stdout

validate

ansible all -a "blkid /dev/research/data"
ansible all -m shell -a 'lsblk'


Q10: myhosts j2

vim xxx.txt

# /find bellow keywords for j2 
ipv4
nodename
hostname


# understand ansible biuldin vars

groups.all
groups.dev
inventory_hostname
hostvars[i]

# j2 for loop
{% for i in groups.all %}
{{ hostvars[i]. }}
{% endfor %}

# ansible-doc template

wget http://classroom/materials/hosts.j2

vim /home/greg/ansible/hosts.yml

---
- name: j2
  hosts: all  # has to go all to get all groups.all hosts
  tasks:
  - name: Template a hostfile
    ansible.builtin.template:template
      src: /home/greg/ansible/hosts.j2
      dest: /etc/myhosts
    when: inventory_hostname in groups.dev # only excute for dev hosts

vim hosts.j2

{% for i in groups.all %}
{{ hostvars[i].ansible_default_ipv4.address }} {{ hostvars[i].ansible_nodename }} {{ hostvars[i].ansible_hostname }}
{% endfor %}

ansible-navigator run hosts.yml -m stdout


validate:

ansible dev -a "cat /etc/myhosts"

Q11: issue, change file

groups.dev
groups.test
inventory_hostname

ansible-doc copy

vim /home/greg/ansible/issue.yml

---
- name: issue
  hosts: all
  tasks:
  - name: dev
    ansible.builtin.copy:
      content: 'Development'
      dest: /etc/issue
    when: inventory_hostname in groups.dev

  - name: test
    ansible.builtin.copy:
      content: 'Test'
      dest: /etc/issue
    when: inventory_hostname in groups.test

  - name: prod
    ansible.builtin.copy:
      content: 'Production'
      dest: /etc/issue
    when: inventory_hostname in groups.prd

ansible-navigator run issue.yml -m stdout

validate:

ansible all -a "cat /etc/issue"

Q12: create WEB content

ansible-doc copy   !!  setype

ansible-doc file
ansible-doc group

ansible dev -a "ls -Z /var/www/html"

vim /home/greg/ansible/webcontent.yml
---
- name: create web
  hosts: dev
  roles:
  - apache
  tasks:
  - name: Ensure group "webdev" exists
    ansible.builtin.group:
      name: webdev
      state: present

  - name: create dir
    ansible.builtin.file:
      path: /webdev
      state: directory
      mode: u+rwx,g+rws,o+rx
      group: webdev

  - name: link
    ansible.builtin.file:
      src: /webdev   # remember order for syc and dest
      dest: /var/www/html/webdev
      state: link

  - name: copy content
    ansible.builtin.copy:
      content: 'Development'
      dest: /webdev/index.html
      setype: httpd_sys_content_t   # man semanage fcontext for httpd_sys_content_t

ansible dev -a "ls -Z /var/www/html"

validate :

http://node1/devweb


Q13: hardware report

# get empty report, understand keywords
wget http://materials/hwreport.empty
vim hwreport.empty


vim xxx.txt
# /find vars in setup
ansible_memtotal_mb
ansible_bios_version
vda
ansible_devices.vda.size

# user get_url and lininfile module
ansible-doc get_url

ansible-doc lineinfile


vim /home/greg/ansible/hwreport.yml
---
- name: hardware report
  hosts: all
  tasks:
  - name: Copy file 
    ansible.builtin.get_url:
      url: http://classroom/materials/hwreport.empty
      dest: /root/hwreport.txt

  - name: hostname
    ansible.builtin.lineinfile:
      path: /root/hwreport.txt
      regexp: '^HOST='
      line: "HOST={{ inventory_hostname }}"
  - name: memory
    ansible.builtin.lineinfile:
      path: /root/hwreport.txt
      regexp: '^MEMORY='
      line: "MEMORY={{ ansible_memtotal_mb }}"
  - name: bios
    ansible.builtin.lineinfile:
      path: /root/hwreport.txt
      regexp: '^BIOS='
      line: "BIOS={{ ansible_bios_version }}"
  - name: vda
    ansible.builtin.lineinfile:
      path: /root/hwreport.txt
      regexp: '^DISK_SIZE_VDA='
      line: "DISK_SIZE_VDA={{ ansible_devices.vda.size }}"
  - name: hostname
    ansible.builtin.lineinfile:
      path: /root/hwreport.txt
      regexp: '^DISK_SIZE_VDB='
      line: "DISK_SIZE_VDB={{ ansible_devices.vdb.size | default('NONE', true) }}" # remember # () need remember

ansible-playbook --syntax-check hwreport.yml
ansible-navigator run -m stdout hwreport.yml

validate 
ansible all -a "cat /root/hwreport.txt"


Q14: vault

ansible-vault --help

ansible-vault create /home/greg/ansible/locker.yml 
password

echo whenyouwishuponastar > /home/greg/ansible/secret.txt

validate:

cat /home/greg/ansible/locker.yml
ansible-vault view /home/greg/ansible/locker.yml
password




Q15: user

# understand user list
wget  http://classroom/materials/user_list.yml
cat user_list.yml 

# understand user and group module
ansible-doc user
ansible-doc group

# define vars_files in playbook
vars_files
/home/greg/ansible/user_list.yml
/home/greg/ansible/locker.yml

# set passwd file in ansible.cfg, # search for vault then add bellow
vim ansible.cfg1
vim ansible.cfg

vault_password_file = /home/greg/ansible/secret.txt

# understand passwd hash
passwd hash512
| password_hash('sha512') 


vim /home/greg/ansible/users.yml

---
- name: u1
  hosts: dev, test
  vars_files:
  - /home/greg/ansible/user_list.yml
  - /home/greg/ansible/locker.yml
  tasks:
  - name: group1
    ansible.builtin.group:
      name: devops
      state: present
  - name: u1
    ansible.builtin.user:
      name: "{{ item.name }}"
      password_expire_max: "{{ item.password_expire_max }}"  
      uid: "{{ item.uid }}"
      group: devops
      password: "{{ pw_developer | password_hash('sha512') }}"  # remember 
    loop: "{{ users }}"
    when: item.job == "developer" 

- name: u2
  hosts: prod
  vars_files:
  - /home/greg/ansible/user_list.yml
  - /home/greg/ansible/locker.yml
  tasks:
  - name: group2
    ansible.builtin.group:
      name: opsmgr
      state: present
  - name: Set u2
    ansible.builtin.user:
      name: "{{ item.name }}"
      password_expire_max: "{{ item.password_expire_max }}"
      groups: opsmgr
      password: "{{ pw_manager | password_hash('sha512') }}"
      uid: "{{ item.uid }}"
    loop: "{{ users }}"
    when: item.job == "manager"


validate 

ansible all -a "id bob"
ansible all -a "id sally"

ssh bob@node1 Imadev
ssh sally@node3 Imamgr

Q16: vault rekey

wget http://classroom/materials/salaries.yml

ansible-vault rekey salaries.yml
old password
new password

vaildate:

cat salaries.yml 

ansible-vault view salaries.yml 
Vault password: 

Q17: cron

ansible-doc cron


vim /home/greg/ansible/cron.yml

---
- name: cron
  hosts: test
  tasks:
  - name: cron job
    ansible.builtin.cron:
      name: "cron job1"
      minute: "*/2"   # remember "" to inlude 
      job: 'logger "EX200 in progress"' # remember '""'
      user: natasha

ansible-playbook --syntax-check cron.yml
ansible-navigator run -m stdout cron.yml

validate:

ansible test -a "crontab -l -u natasha"

{% endhighlight %}