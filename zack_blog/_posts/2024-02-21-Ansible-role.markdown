---
layout: post
title:  "Ansible Advance - Roles"
date:   2024-02-21 11:15:29 +1100
categories: jekyll Cat2
---


<b>About Ansible Roles </b>

Here we play with Ansible Roles, as Ansible is powerful configuration automation tool by running playpook, in addition organizing multiple Ansible contents and playbooks into roles provides a structural and more manageable way to achieve complex tasks for multiple targets or groups.

===================================================================

Ansible Roles can be created by: 

- Method1: Create Ansible roles by ansible-galaxy


Quickly creating a well-defined role directory structure skeleton, we can leverage the command ansible-galaxy init <role_name>

{% highlight shell %}

[root@localhost ansible]# ansible-galaxy init zack-role
 Role zack-role was created successfully
[root@localhost ansible]# tree zack-role
zack-role
├── defaults
│   └── main.yml
├── files
├── handlers
│   └── main.yml
├── meta
│   └── main.yml
├── README.md
├── tasks
│   └── main.yml
├── templates
├── tests
│   ├── inventory
│   └── test.yml
└── vars
    └── main.yml


{% endhighlight %}


<b>defaults</b>: This directory can contain default variables for the role.


<b>files</b>: This directory can contain static files that you want to copy to the target hosts.


<b>handlers</b>: This directory can contain handlers, which are tasks triggered by other tasks.


<b>meta</b>: This directory can contain metadata for the role, such as dependencies.


<b>tasks</b>: This directory contains a main.yaml file, which includes tasks specific to the "server1" role.


<b>templates</b>: This directory can contain Jinja2 templates.


<b>vars</b>: This directory can contain variables specific to the "server1" role

===================================================================


- Method2: Manually create roles (server1 & server2) by create necessary folder structure and Setting up 2 server groups in ansible inventory file： 

{% highlight shell %}

vim /etc/ansible/hosts
# add group server1 as web server, server2 as backend
[defaults]
11.0.1.132
11.0.1.131

[server1]
11.0.1.131

[server2]
11.0.1.132

# create own roles structure server1 (web) and server2 (backend)
# create zack.html under role server1/files

[root@localhost ansible]# tree roles
roles
├── base
│   └── tasks
│       └── main.yaml
├── server1
│   ├── defaults
│   ├── files
│   │   └── zack.html
│   ├── handlers
│   ├── meta
│   ├── tasks
│   │   └── main.yaml
│   ├── templates
│   └── vars
└── server2
    ├── defaults
    ├── files
    ├── handlers
    ├── meta
    ├── tasks
    │   └── main.yaml
    ├── templates
    └── vars



{% endhighlight %}



- define tasks for role server1 and role server2


{% highlight shell %}

cat /etc/ansible/roles/server1/tasks/main.yaml
# web server tasks include: install httpd, enable service, open 80 port, replace index.html, restart httpd service
- name: Install HTTPD package
  yum:
    name: httpd
    state: present

- name: Enable HTTPD service
  service:
    name: httpd
    enabled: yes
    state: started

- name: Open port 80 in firewall
  firewalld:
    service: http
    permanent: yes
    state: enabled

- name: replace index.html
  copy:
    src: zack.html
    dest: /var/www/html/index.html
    owner: root
    group: root
    mode: 0644
  register: httpd_updated

- name: restart httpd service
  service:
    name: httpd
    state: restarted
  when: httpd_updated.changed


cat /etc/ansible/roles/server2/tasks/main.yaml

# backend server2 tasks include install epel repo, install iftop and lrzsz

- name: Install epel-release
  yum:
    name:
      - epel-release
    state: latest
- name: Check Yum Repository List
  yum:
    list: repo

- name: Install usage packages
  yum:
    name:
      - iftop
      - lrzsz
    state: latest

{% endhighlight %}


- define role main playbook zack-role.yaml


{% highlight shell %}
# update repo for all hosts, for server1 and server 2, execute each role server1 and server2

---
- become: true
  hosts: all
  pre_tasks:
  - name: update repository index
    tags: always
    yum:
      update_cache: yes
    changed_when: false

- import_playbook: /etc/ansible/add-more-user.yaml

- hosts: server1
  become: true
  roles:
    - server1


- hosts: server2
  become: true
  roles:
    - server2

{% endhighlight %}

- run playbook for zack-role.yaml

{% highlight shell %}

PLAY [all] **************************************************************************************************************************

TASK [Gathering Facts] **************************************************************************************************************
ok: [11.0.1.132]
ok: [11.0.1.131]

TASK [update repository index] ******************************************************************************************************
ok: [11.0.1.131]
ok: [11.0.1.132]


PLAY [server1] **********************************************************************************************************************

TASK [Gathering Facts] **************************************************************************************************************
ok: [11.0.1.131]

TASK [server1 : Install HTTPD package] **********************************************************************************************
ok: [11.0.1.131]

TASK [server1 : Enable HTTPD service] ***********************************************************************************************
ok: [11.0.1.131]

TASK [server1 : Open port 80 in firewall] *******************************************************************************************
ok: [11.0.1.131]

TASK [server1 : replace index.html] *************************************************************************************************
ok: [11.0.1.131]

TASK [server1 : restart httpd service] **********************************************************************************************
skipping: [11.0.1.131]

PLAY [server2] **********************************************************************************************************************

TASK [Gathering Facts] **************************************************************************************************************
ok: [11.0.1.132]

TASK [server2 : Install epel-release] ***********************************************************************************************
ok: [11.0.1.132]

TASK [server2 : Check Yum Repository List] ******************************************************************************************
ok: [11.0.1.132]

TASK [server2 : Install usage packages] *********************************************************************************************
ok: [11.0.1.132]

PLAY RECAP **************************************************************************************************************************
11.0.1.131                 : ok=11   changed=0    unreachable=0    failed=0    skipped=1    rescued=0    ignored=0   
11.0.1.132                 : ok=10   changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   

{% endhighlight %}

- Bingo! validate httpd on server1, and iftop & lrzsz installed on server2 by leveraging with ansible roles

{% highlight shell %}

[root@localhost ansible]# curl 11.0.1.131
This is zack test Ansible role web !!!!!!!!!!!   
!!!!!!!!!


{% endhighlight %}





