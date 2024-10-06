#!/bin/bash

# install argocd

kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
sleep 60


curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
rm argocd-linux-amd64

argocd admin initial-password -n argocd

argocd login <ARGOCD_SERVER>

# get initial argo admin passwd
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d


# eks 

#refer one sg to eks sg
aws ec2 authorize-security-group-ingress --group-id sg-0872eeb942ae7b80e --protocol tcp --port 443 --source-group sg-01cf879d931cace7c
# update kubeconfig
aws eks update-kubeconfig --region ap-southeast-2 --name module-eks-cluster-stage
# update eks api endpoint from private to public
aws eks update-cluster-config --region ap-southeast-2 --name module-eks-cluster-stage --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=false
# describe eks cluster status -- updating or active
aws eks describe-cluster --name module-eks-cluster-stage --region ap-southeast-2
# eks add user to cluster