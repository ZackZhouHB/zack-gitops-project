---
title: "EKS & VPC Lattice Integration for A/B Testing"
date: 2025-09-30T23:56:25Z
slug: eks-vpc-lattice-integration-for-a-b-testing
categories: ["Kubernetes"]
aliases: ["/post/153/"]
legacy_id: 153
---
For those experienced with Kubernetes, managing traffic between microservices often brings tools like Istio to mind. I had done some posts before on Istio for [Distributed Tracing and Traffic Routing](/posts/istio-traffic-routing/).

This PoC explores a different approach: using **AWS VPC Lattice**. While the goal—in this case, A/B testing between different service versions—is the same, the implementation differs. Instead of Istio's `VirtualService` and `DestinationRule` resources, this setup leverages the vendor-neutral Kubernetes Gateway API. This allows for a more standardized way of defining routing within the cluster, while VPC Lattice provides the power to extend this networking seamlessly across different VPCs.

[![[Image Placeholder 01: Introduction Graphic]](/images/vpc1.png)](/images/vpc1.png)

---

This post is about integrating AWS EKS cluster with VPC Lattice to enable advanced traffic management and A/B testing for microservices. The setup leverages the standard Kubernetes Gateway API to define routing rules, which are implemented by the AWS Gateway Controller to provision and configure VPC Lattice resources automatically.

[![[Image Placeholder 01: Introduction Graphic]](/images/vpc2.png)](/images/vpc2.png)

**The Architecture**

The resulting architecture allows internet traffic to be routed through a Network Load Balancer to a UI service. The UI then communicates with backend services through VPC Lattice, which manages traffic splitting for A/B testing between two different versions of the `checkout` service.

```text
Internet Traffic
    ↓
Network Load Balancer (ui-nlb)
    ↓
UI Service (updated to use VPC Lattice)
    ↓
VPC Lattice Gateway (managed by AWS)
    ↓
HTTPRoute (splits traffic 75% / 25%)
    ├───────────↓
    │           ↓
Checkout v1 (25%)   Checkout v2 (75%)
```

**Phase 1: Infrastructure Setup (EKS Security Group)**

- **Goal**: Allow the EKS cluster to securely receive traffic from the VPC Lattice service network.
- **Process**: The cluster's primary security group was modified to allow ingress traffic from the AWS-managed prefix lists for VPC Lattice. This opens a secure communication channel without exposing ports to the public internet.
- **Key Commands**:

  ```bash
  # 1. Get the EKS cluster's security group ID
  CLUSTER_SG=$(aws eks describe-cluster --name $EKS_CLUSTER_NAME --output json| jq -r '.cluster.resourcesVpcConfig.clusterSecurityGroupId')

  # 2. Find the AWS-managed prefix list for VPC Lattice
  PREFIX_LIST_ID=$(aws ec2 describe-managed-prefix-lists --query "PrefixLists[?PrefixListName=='com.amazonaws.$AWS_REGION.vpc-lattice'].PrefixListId" | jq -r '.[]')

  # 3. Authorize ingress traffic from the prefix list to the cluster's security group
  aws ec2 authorize-security-group-ingress --group-id $CLUSTER_SG --ip-permissions "PrefixListIds=[{PrefixListId=${PREFIX_LIST_ID}}],IpProtocol=-1"
  ```

- **Outcome**: ✅ Network connectivity established between VPC Lattice and the EKS cluster.

**Phase 2: Gateway API Installation**

- **Goal**: Install the Kubernetes components required to understand and manage Gateway API resources.
- **Process**: This involved two parts: first, applying the standard Gateway API Custom Resource Definitions (CRDs), which provide the `Gateway` and `HTTPRoute` resource types. Second, installing the AWS Gateway Controller using Helm, which acts as the "translator" between the Kubernetes API and VPC Lattice.
- **Key Commands**:

  ```bash
  # 1. Install Gateway API CRDs (the "language")
  kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml

  # 2. Install the AWS Gateway Controller (the "translator")
  helm install gateway-api-controller oci://public.ecr.aws/aws-application-networking-k8s/aws-gateway-controller-chart --version=v1.0.5 --namespace gateway-api-controller
  ```

- **Outcome**: ✅ The AWS Gateway Controller is running and ready to provision VPC Lattice resources based on Gateway API objects.

**Phase 3: Gateway Configuration**

- **Goal**: Define and create the VPC Lattice Service Network.
- **Process**: A `GatewayClass` resource was applied to define "VPC Lattice" as a gateway provider. Then, a `Gateway` resource was created, which prompted the controller to provision the actual VPC Lattice service network and associate it with the cluster.
- **Key Commands**:

  ```bash
  # 1. Define VPC Lattice as a gateway provider
  kubectl apply -f gatewayclass.yaml

  # 2. Create the Gateway, which provisions the VPC Lattice Service Network
  cat eks-workshop-gw.yaml | envsubst | kubectl apply -f -

  # 3. Wait for the gateway to be programmed and ready
  kubectl wait --for=condition=Programmed gateway/${EKS_CLUSTER_NAME} -n checkout
  ```

- **Outcome**: ✅ A VPC Lattice service network is created and associated with the EKS cluster.

[![[Image Placeholder 01: Introduction Graphic]](/images/vpc3.png)](/images/vpc3.png)

[![[Image Placeholder 01: Introduction Graphic]](/images/vpc4.png)](/images/vpc4.png)

**Phase 4: Application Deployment for A/B Testing**

- **Goal**: Deploy two distinct versions of the `checkout` application to serve as targets for traffic splitting.
- **Process**: Using Kustomize, two versions of the `checkout` service were deployed into separate namespaces (`checkout` and `checkoutv2`) to simulate a real-world A/B testing scenario.
- **Key Commands**:

  ```bash
  # Deploy the two application versions
  kubectl apply -k ~/environment/eks-workshop/modules/networking/vpc-lattice/abtesting/

  # Verify the rollout status of the v2 deployment
  kubectl rollout status deployment/checkout -n checkoutv2
  ```

- **Outcome**: ✅ Two versions of the `checkout` service are running independently.

**Phase 5: Traffic Routing & Health Checks**

- **Goal**: Define the traffic splitting rules and configure health checks for the application targets.
- **Process**: An `HTTPRoute` resource was created to define the core routing logic, splitting traffic 25% to the original `checkout` service and 75% to the `checkoutv2` service. A `TargetGroupPolicy` was also applied to configure detailed health checks for the VPC Lattice target groups.
- **Key Resources**:

  **HTTPRoute for Traffic Splitting:**

  ```yaml
  apiVersion: gateway.networking.k8s.io/v1
  kind: HTTPRoute
  metadata:
    name: checkoutroute
    namespace: checkout
  spec:
    parentRefs:
    - name: eks-workshop
      sectionName: http
    rules:
    - backendRefs:
      - name: checkout
        namespace: checkout
        port: 80
        weight: 25
      - name: checkout
        namespace: checkoutv2
        port: 80
        weight: 75
      matches:
      - path:
          type: PathPrefix
          value: /
  ```

  **TargetGroupPolicy for Health Checks:**

  ```yaml
  apiVersion: application-networking.k8s.aws/v1alpha1
  kind: TargetGroupPolicy
  metadata:
    name: checkout-policy
    namespace: checkout
  spec:
    targetRef:
      kind: Service
      name: checkout
    healthCheck:
      enabled: true
      path: "/health"
  ```

- **Outcome**: ✅ Traffic is actively being split between the two service versions with proper health checks in place.

**Phase 6: UI Integration**

- **Goal**: Reconfigure the frontend UI application to send traffic to the new VPC Lattice endpoint.
- **Process**: The UI deployment was updated to use the DNS name assigned by VPC Lattice to the `HTTPRoute`. This directs all backend calls from the UI through the managed VPC Lattice gateway instead of using internal Kubernetes service DNS.
- **Key Commands**:

  ```bash
  # 1. Get the VPC Lattice assigned DNS name
  export CHECKOUT_ROUTE_DNS="http://$(kubectl get httproute checkoutroute -n checkout -o json | jq -r '.metadata.annotations["application-networking.k8s.aws/lattice-assigned-domain-name"]')"

  # 2. Update and redeploy the UI to use the new DNS name
  kubectl kustomize ~/environment/eks-workshop/modules/networking/vpc-lattice/ui/ | envsubst | kubectl apply -f -
  kubectl rollout restart deployment/ui -n ui
  ```

- **Outcome**: ✅ The end-to-end traffic flow is complete and fully functional.

In browser and try to checkout multiple times (with different items in the cart), we notice that the checkout now uses the "Lattice checkout" pods about 75% of the time.

[![[Image Placeholder 01: Introduction Graphic]](/images/vpc5.png)](/images/vpc5.png)

---

**VPC Lattice vs. Istio Service Mesh**

**Similarities**

- Both handle traffic routing (blue/green, canary), service discovery, load balancing, and enforce auth policies.

**Differences**

- **Architecture**: Istio uses sidecars; VPC Lattice is AWS-managed (no sidecars).
- **Ops**: Istio needs you to manage control plane & certs; VPC Lattice is fully managed.
- **Performance**: Sidecars can add latency; Lattice uses AWS networking (lower latency).
- **Scope**: Istio works anywhere; Lattice is AWS-only (EKS, ECS, EC2, Lambda).
- **Complexity**: Istio is harder to learn; Lattice is simpler with AWS tools.

**When to Use**

**VPC Lattice**: Best if you’re all-in on AWS, want simplicity, no sidecars, and cross-service AWS connectivity.

**Istio**: Best for multi-cloud/on-prem, advanced mesh features, vendor-neutral, and deep traffic control.

VPC Lattice essentially provides a "service mesh as a service" for AWS workloads, reducing the operational complexity that comes with self-managed solutions like Istio. The full source code and guide can be found at  [GitHub repo](https://github.com/aws-samples/eks-workshop-v2/tree/stable/manifests/modules/networking/vpc-lattice).
