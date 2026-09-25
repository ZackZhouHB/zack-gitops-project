---
title: "Rook-Ceph for dynamic Persistent Volume"
date: 2022-11-09T23:01:53Z
slug: rook-ceph-for-dynamic-persistent-volume
categories: ["Kubernetes"]
aliases: ["/post/51/"]
legacy_id: 51
---
Today, I will explore how to install and configure Persistent Volume for all the deployment in K8S to consume.

Helm install Rook-Ceph for persistent storage

- Configure local VM block storage to add 50Gb sdb to all k8s master and worker nodes
- Install rook-ceph cluster

```bash
git clone --single-branch --branch master https://github.com/rook/rook.git
cd rook/deploy/examples
kubectl create -f crds.yaml -f common.yaml -f operator.yaml
kubectl create -f cluster.yaml
```

- Ceph toolbox to check cluster status

```bash
kubectl create -f toolbox.yaml
kubectl -n rook-ceph exec -it deploy/rook-ceph-tools -- bash
ceph status
ceph osd status
ceph df
rados df
```

- Ceph Dashboard service for HTTPS login

```bash
kubectl create -f dashboard-external-https.yaml
kubectl -n rook-ceph get secret rook-ceph-dashboard-password -o jsonpath="{['data']['password']}" | base64 --decode && echo
```

- Create storage pool and storage class

```bash
kubectl create -f pool.yaml
cd csi/rbd
kubectl create -f storageclass.yaml
```

- Set "rook-ceph-block" as the default storage class

```bash
kubectl patch storageclass rook-ceph-block -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'

kubectl get sc
NAME                        PROVISIONER                  RECLAIMPOLICY  VOLUMEBINDINGMODE  ALLOWVOLUMEEXPANSION   AGE
rook-ceph-block (default)   rook-ceph.rbd.csi.ceph.com   Delete          Immediate          true                  8d
```

Check pool and OSDs in Ceph web UI

[![image tooltip here](/images/ceph.png)](/images/ceph.png)
