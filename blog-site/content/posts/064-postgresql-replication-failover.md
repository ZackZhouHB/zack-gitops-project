---
title: "PostgreSQL: Replication & Failover"
date: 2024-01-08T03:10:54Z
slug: postgresql-replication-failover
categories: ["DevOps"]
aliases: ["/post/64/"]
legacy_id: 64
---
Last post I started a hands-on session with PostgreSQL installation on both Docker and Docker Compose, explored important PostgreSQL configuration, and was able to mount persistent volumes and config files to customize PostgreSQL.

In this post, I will set up a second PostgreSQL instance to establish primary and standby replication for PostgreSQL HA, using some pg tools. Lastly, we will test failover by shutting down the primary and promoting the standby instance.

[![image tooltip here](/images/ps2-1.png)](/images/ps2-1.png)

To achieve this, follow these steps:

- **Setup Docker network and Create Replication User in Primary instance**

To establish PostgreSQL replication, it is necessary to set unique data volumes for data between instances and unique config files for each instance.

```bash
# create both primary and standby folders
root@ubt-server:~# mkdir postgres-1
root@ubt-server:~# mkdir postgres-2

# move previous post config file to postgres-1 and postgres-2
root@ubt-server:~# cp -r config/* postgres-1/config/
root@ubt-server:~# mv config/* postgres-2/config/

# create docker network so PostgreSQL containers on the same network
root@ubt-server:~/postgres-1/config# docker network create postgres
9891c6d9cd3bdbeea2fdfc2b287c868a0f67a3cec7f2939e1299cfb0ae293021

# run primary
root@ubt-server:~/postgres-1# docker run -it --rm --name postgres-1 \
--net postgres \
-e POSTGRES_USER=postgresadmin \
-e POSTGRES_PASSWORD=admin123 \
-e POSTGRES_DB=postgresdb \
-e PGDATA="/data" \
-v ${PWD}/postgres-1/pgdata:/data \
-v ${PWD}/postgres-1/config:/config \
-v ${PWD}/postgres-1/archive:/mnt/server/archive \
-p 5000:5432 postgres:15.0 \
-c 'config_file=/config/postgresql.conf'

2024-01-11 13:15:07.762 UTC [1] LOG: starting PostgreSQL 15.0 (Debian 15.0-1.pgdg110+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 10.2.1-6) 10.2.1 20210110, 64-bit
2024-01-11 13:15:07.763 UTC [1] LOG: listening on IPv4 address "0.0.0.0", port 5432
2024-01-11 13:15:07.763 UTC [1] LOG: listening on IPv6 address "::", port 5432
2024-01-11 13:15:07.764 UTC [1] LOG: listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"
2024-01-11 13:15:07.766 UTC [63] LOG: database system was shut down at 2024-01-11 13:15:07 UTC
2024-01-11 13:15:07.768 UTC [1] LOG: database system is ready to accept connections

# create Replication User, chown postgres to access archive folder
root@ubt-server:~# docker exec -it postgres-1 bash
root@2bf6be3e4fa8:/# createuser -U postgresadmin -P -c 5 --replication replicationUser
Enter password for new role:
Enter it again:
root@2bf6be3e4fa8:/# chown postgres:postgres /mnt/server/archive

# add replication into configuration file
root@ubt-server:~/postgres-1/config# vim pg_hba.conf
# TYPE  DATABASE      USER           ADDRESS            METHOD
# add replication user
host     replication     replicationUser         0.0.0.0/0       md5
```

- **Enable Write-Ahead Log, archive, and Replication**

Write-Ahead Log (WAL) is a PostgreSQL data integrity mechanism of writing transaction logs to a file. PostgreSQL does not accept the transaction until it has been written to the transaction log and flushed to disk. This ensures that if there is a crash in the system, the database can be recovered from the transaction log.

So, we need to add the following lines into `postgresql.conf` to enable Write-Ahead Log and set up the replication and archive.

```bash
root@ubt-server:~/postgres-1/config# vim postgresql.conf

# replication
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /mnt/server/archive/%f && cp %p /mnt/server/archive/%f'
max_wal_senders = 3
```

- **Set up standby instance and validate replication**

Here, we need to use the tool `pg_basebackup` to create a standby instance by taking a primary instance base backup, entering the "replicationUser" password, and then backing up the `postgres-1` database into the `postgres-2` `pgdata` folder.

```bash
root@ubt-server:~# docker run -it --rm --net postgres -v ${PWD}/postgres-2/pgdata:/data --entrypoint /bin/bash postgres:15.0

root@56e38636a87b:/# pg_basebackup -h postgres-1 -p 5432 -U replicationUser -D /data/ -Fp -Xs -R
Password:
```

Now, we start the standby instance. See the log below. Postgres-2 is entering standby mode, ready to accept read-only connections, and starting streaming WAL from the primary.

```bash
root@ubt-server:~# docker run -it --rm --name postgres-2 --net postgres -e POSTGRES_USER=postgresadmin -e POSTGRES_PASSWORD=admin123 -e POSTGRES_DB=postgresdb -e PGDATA="/data" -v ${PWD}/postgres-2/pgdata:/data -v ${PWD}/postgres-2/config:/config -v ${PWD}/postgres-2/archive:/mnt/server/archive -p 5001:5432 postgres:15.0 -c 'config_file=/config/postgresql.conf'

PostgreSQL Database directory appears to contain a database; Skipping initialization

2024-01-11 14:25:21.008 UTC [1] LOG: starting PostgreSQL 15.0 (Debian 15.0-1.pgdg110+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 10.2.1-6) 10.2.1 20210110, 64-bit
2024-01-11 14:25:21.008 UTC [1] LOG: listening on IPv4 address "0.0.0.0", port 5432
2024-01-11 14:25:21.008 UTC [1] LOG: listening on IPv6 address "::", port 5432
2024-01-11 14:25:21.010 UTC [1] LOG: listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"
2024-01-11 14:25:21.012 UTC [29] LOG: database system was interrupted; last known up at 2024-01-11 14:21:16 UTC
2024-01-11 14:25:21.017 UTC [29] LOG: entering standby mode
2024-01-11 14:25:21.026 UTC [29] LOG: redo starts at 0/5000028
2024-01-11 14:25:21.026 UTC [29] LOG: consistent recovery state reached at 0/5000100
2024-01-11 14:25:21.026 UTC [1] LOG: database system is ready to accept read-only connections
2024-01-11 14:25:21.034 UTC [30] LOG: started streaming WAL from primary at 0/6000000 on timeline 1
```

- **Test replication and failover**

First, let's test the replication by logging into `postgres-1`, creating a `zack_customers` table, and validating from `postgres-2`.

```bash
# bash into postgres-1, create zack_customers table
root@ubt-server:~# docker exec -it postgres-1 bash
root@06dd98085df7:/# psql --username=postgresadmin postgresdb
psql (15.0 (Debian 15.0-1.pgdg110+1))
Type "help" for help.

postgresdb=# CREATE TABLE zack_customers (zackname text, z_customer_id serial, date_created timestamp);
CREATE TABLE
postgresdb=# \dt
               List of relations
 Schema |     Name     | Type  |     Owner
--------+----------------+-------+---------------
 public | zack_customers | table | postgresadmin
(1 row)

postgresdb=# \q
root@06dd98085df7:/# exit
exit

# bash into postgres-2, validate zack_customers table
root@ubt-server:~/postgres-2/pgdata# docker exec -it postgres-2 bash
root@b333ff290624:/# psql --username=postgresadmin postgresdb
psql (15.0 (Debian 15.0-1.pgdg110+1))
Type "help" for help.

postgresdb=# \dt
               List of relations
 Schema |     Name     | Type  |     Owner
--------+----------------+-------+---------------
 public | zack_customers | table | postgresadmin
(1 row)

postgresdb=# \q
root@b333ff290624:/# exit
exit
```

Now, we simulate failover by using the load balancer tool `pgctl`, shutting down the primary instance, and then promoting the standby read-only instance into a read-write instance.

```bash
# shut down the primary instance
root@ubt-server:~# docker rm -f postgres-1
postgres-1
# exec standby try to create a table zack_customers_2, get error as it's read-only
root@ubt-server:~# docker exec -it postgres-2 bash
root@b333ff290624:/# psql --username=postgresadmin postgresdb
psql (15.0 (Debian 15.0-1.pgdg110+1))
Type "help" for help.

postgresdb=# CREATE TABLE zack_customers_2 (zackname text, z_customer_id serial, date_created timestamp);
ERROR:  cannot execute CREATE TABLE in a read-only transaction

postgresdb-# \q

# promote postgres-2 from standby to primary
root@b333ff290624:/# runuser -u postgres -- pg_ctl promote
waiting for server to promote.... done
server promoted

# exec to create table zack_customers_2, this time works
root@b333ff290624:/# psql --username=postgresadmin postgresdb
psql (15.0 (Debian 15.0-1.pgdg110+1))
Type "help" for help.

postgresdb=# CREATE TABLE zack_customers_2 (zackname text, z_customer_id serial, date_created timestamp);
CREATE TABLE
postgresdb=# \dt
               List of relations
 Schema |       Name        | Type  |     Owner
--------+-------------------+-------+---------------
 public | zack_customers    | table | postgresadmin
 public | zack_customers_2  | table | postgresadmin
(2 rows)

postgresdb=# \q
root@b333ff290624:/# exit
exit
root@ubt-server:~#
```

**Conclusion**

Now we are able to run PostgreSQL primary and standby instances to test replication and failover. In the next blog, I will explore how to deploy a single PostgreSQL on Kubernetes.
