---
title: "MLOps - Deploy ML workload into EKS with Karpenter"
date: 2025-02-01T04:35:11Z
slug: mlops-deploy-ml-workload-into-eks-with-karpenter
categories: ["Machine Learning"]
aliases: ["/post/98/"]
legacy_id: 98
---
Finally, machine learning workload into AWS EKS with Karpenter

In the previous post, I was able to complete both local Pytorch ML and AWS SageMaker practice, and containerize and deploy ML docker image locally.

In this post, I will explore the model deployment to EKS cluster with Karpenter to simulate a more scalable and real-life production-ready environment.

**Challenges when moving to Cloud deployment**

Here are key differences between local PyTorch model vs AWS SageMaker artifacts, and how they impact the Docker image size and Performance considerations for LLM images in EKS deployment.

| Aspect | Local PyTorch Model (.pth) | AWS SageMaker Model (.tar.gz) |
| --- | --- | --- |
| `Contents` | Full model state\_dict + Python code | Only model parameters + inference code |
| `Framework` | Raw PyTorch implementation | Optimized MXNet framework |
| `Serialization` | torch.save() native format | Framework-specific serialization |
| `Dependencies` | Requires full PyTorch installation | Minimal runtime dependencies |

The latency between pod initialization and readiness to serve requests includes:

- Container image pull time
- Model download from storage
- Framework initialization
- GPU context creation
- Model loading into memory

Optimize Docker image size for AWS ECR and EKS deployment.

Optimized Dockerfile (Target: ~450MB)

```bash
# Use NVIDIA CUDA base image with Python
FROM nvidia/cuda:11.2.2-base-ubuntu20.04

# Install system dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3.8 \
    python3-pip \
    python3.8-venv \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy inference code
COPY app.py .

# Environment variables
ENV MODEL_S3_URI="s3://sagemaker-bucket-85xxxxxxxx42/models/image_model/classifier-2025-01-26-02-58-03-005-dbf196d2/output/model.tar.gz"
ENV AWS_REGION=ap-southeast-2

# Expose API port
EXPOSE 8080

# Startup command
CMD ["python3", "app.py"]
```

requirements.txt

```text
mxnet==1.9.1
flask==2.2.5
boto3==1.28.62
pillow==10.1.0
```

app.py (Optimized Inference Service)

```python
import os
import tarfile
import boto3
from flask import Flask, request, jsonify
import mxnet as mx
import numpy as np
from PIL import Image
import io

app = Flask(__name__)

# Initialize model
ctx = mx.gpu() if mx.context.num_gpus() > 0 else mx.cpu()
model = None

def download_and_extract_model():
    global model
    s3 = boto3.client('s3', region_name=os.environ['AWS_REGION'])
    model_path = '/tmp/model.tar.gz'
    bucket, key = os.environ['MODEL_S3_URI'].split('//')[1].split('/', 1)
    s3.download_file(bucket, key, model_path)

    with tarfile.open(model_path) as tar:
        tar.extractall(path='/model')

    sym, arg_params, aux_params = mx.model.load_checkpoint('/model/model', 0)
    mod = mx.mod.Module(symbol=sym, context=ctx)
    mod.bind(for_training=False, data_shapes=[('data', (1, 3, 224, 224))])
    mod.set_params(arg_params, aux_params)
    model = mod

@app.before_first_request
def initialize():
    download_and_extract_model()

def transform_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    img = img.resize((224, 224))
    img = np.array(img).transpose(2, 0, 1).astype(np.float32)
    img = mx.nd.array((img - 128) / 128)  # Match SageMaker preprocessing
    return img.reshape((1, 3, 224, 224))

@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    image = request.files['image'].read()
    data = transform_image(image)

    batch = mx.io.DataBatch([data])
    model.forward(batch, is_train=False)
    prob = model.get_outputs()[0].asnumpy().argmax()

    return jsonify({'prediction': int(prob)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

Size Comparison after optimization:

| Component | Local PyTorch | Optimized MXNet | Reduction |
| --- | --- | --- | --- |
| Base Image | 2.5GB | 418MB | -83% |
| Framework | 1.2GB | 89MB | -93% |
| Model Storage | Baked-in | S3 Download | -100% |
| Total Image Size | ~5GB | 537MB | -90% |

```bash
root@zackz:/mnt/f/ml-local/local-cv/eks# docker image ls
REPOSITORY                                TAG                                        IMAGE ID       CREATED          SIZE
classifier-eks                            latest                                     92736798f67f   11 seconds ago   537MB
pneumonia-frontend                        latest                                     ac8f5e301dfd   3 days ago       47.1MB
pneumonia-classifier-1                    latest                                     d0bf743556d8   3 days ago       4.73GB
```

**Provision EKS and Karpenter with Terraform**

Here I will use Terraform to [provision an EKS cluster with Karpenter](https://raw.githubusercontent.com/ZackZhouHB/zack-gitops-project/refs/heads/editing/EKS-Karpenter-Spot/main.tf).

```bash
root@zackz:/mnt/f/1/spot-and-karpenter# kubectl get node
NAME                                             STATUS   ROLES    AGE   VERSION
ip-10-0-119-37.ap-southeast-2.compute.internal   Ready    <none>   21m   v1.30.8-eks-aeac579
ip-10-0-65-17.ap-southeast-2.compute.internal    Ready    <none>   21m   v1.30.8-eks-aeac579
root@zackz:/mnt/f/1/spot-and-karpenter# kubectl get po -A
NAMESPACE     NAME                                  READY   STATUS    RESTARTS   AGE
karpenter     karpenter-7c9f6776cc-5djcv            1/1     Running   0          23m
karpenter     karpenter-7c9f6776cc-ntgwj            1/1     Running   0          23m
kube-system   aws-node-8v5v5                        2/2     Running   0          21m
kube-system   aws-node-pqlcg                        2/2     Running   0          21m
kube-system   coredns-7dd48c8549-97dbr              1/1     Running   0          23m
kube-system   coredns-7dd48c8549-dv4n4              1/1     Running   0          23m
kube-system   ebs-csi-controller-56cb7b4bc-2gwgl    6/6     Running   0          23m
kube-system   ebs-csi-controller-56cb7b4bc-wbffq    6/6     Running   0          23m
kube-system   ebs-csi-node-lnvg8                    3/3     Running   0          21m
kube-system   ebs-csi-node-nkg5c                    3/3     Running   0          21m
kube-system   efs-csi-controller-75645855f5-jssl5   3/3     Running   0          4m22s
kube-system   efs-csi-controller-75645855f5-lfd8r   3/3     Running   0          4m22s
kube-system   efs-csi-node-jc6lm                    3/3     Running   0          4m22s
kube-system   efs-csi-node-m6g7q                    3/3     Running   0          4m23s
kube-system   kube-proxy-44px7                      1/1     Running   0          21m
kube-system   kube-proxy-lrtfd                      1/1     Running   0          21m
root@zackz:/mnt/f/1/spot-and-karpenter# aws eks list-addons --cluster-name spot-and-karpenter --region ap-southeast-2
{
    "addons": [
        "aws-ebs-csi-driver",
        "aws-efs-csi-driver",
        "coredns",
        "kube-proxy",
        "vpc-cni"
    ]
}
```

[![image tooltip here](/images/mlops10-1.png)](/images/mlops10-1.png)

Then tag and push the optimized image classifier-eks to ECR and deploy it to EKS using Karpenter.

```bash
root@zackz:~# aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin 85xxxxxxxx42.dkr.ecr.ap-southeast-2.amazonaws.com
Login Succeeded
root@zackz:~# docker tag classifier-eks:latest 85xxxxxxxx42.dkr.ecr.ap-southeast-2.amazonaws.com/classifier-eks:latest
root@zackz:~# docker push 85xxxxxxxx42.dkr.ecr.ap-southeast-2.amazonaws.com/classifier-eks:latest
The push refers to repository [85xxxxxxxx42.dkr.ecr.ap-southeast-2.amazonaws.com/classifier-eks]
700cbfa4a29a: Pushed
1e026a0de221: Pushed
e30ec0bde91f: Pushed
9994fd5f0914: Pushed
67796cf8ce29: Pushed
0474cd91a62d: Pushed
3c2c7e066741: Pushed
3d25fa2df354: Pushed
0f24c57a5268: Pushed
6c3e7df31590: Pushed
latest: digest: sha256:ccb3a4f70dd01b59658bc365616346bb62c5389814857b78416e40499b6d35c2 size: 2416
```

Create Karpenter NodeClass and NodePool for GPU workloads.

```yaml
# nodepool-gpu.yaml
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: gpu-pool
spec:
  template:
    metadata:
      labels:
        workload-type: custom-ml
    spec:
      nodeClassRef:
        apiVersion: karpenter.k8s.aws/v1beta1
        kind: EC2NodeClass
        name: gpu-nodeclass
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["g4dn.2xlarge", "g5.xlarge", "g5.2xlarge"]  # Larger instance types
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
      taints:
        - key: "nvidia.com/gpu"
          value: "present"
          effect: NoSchedule
  disruption:
    consolidationPolicy: WhenUnderutilized
    expireAfter: 168h

# gpu-nodeclass.yaml
apiVersion: karpenter.k8s.aws/v1beta1
kind: EC2NodeClass
metadata:
  name: gpu-nodeclass
spec:
  role: "karpenter-spot-and-karpenter"
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "spot-and-karpenter"
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "spot-and-karpenter"
  amiFamily: Bottlerocket
  blockDeviceMappings:
    - deviceName: "/dev/xvda"
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
  userData: |
    [settings]
    [settings.kernel]
    lockdown = "integrity"
    [settings.kubernetes]
    node-labels = { "workload-type" = "custom-ml" }
```

Create EKS deployment to request GPU nodes using Karpenter, here I will choose spot `g4dn.2xlarge` instance to deploy the `classifier-eks:latest` image from ECR.

```yaml
# custom-ml-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-ml
spec:
  replicas: 1
  selector:
    matchLabels:
      app: custom-ml
  template:
    metadata:
      labels:
        app: custom-ml
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: workload-type
                    operator: In
                    values: ["custom-ml"]
      tolerations:
        - key: "nvidia.com/gpu"
          operator: "Exists"
          effect: "NoSchedule"
        - key: "karpenter.sh/interruption"
          operator: "Exists"
          effect: "NoSchedule"
      containers:
        - name: custom-ml
          image: 8xxxxxxxx42.dkr.ecr.ap-southeast-2.amazonaws.com/classifier-eks:latest
          resources:
            requests:
              nvidia.com/gpu: 1
              cpu: 3000m  # Reduced CPU request
              memory: 12Gi  # Reduced memory request
            limits:
              nvidia.com/gpu: 1
              cpu: 3000m
              memory: 12Gi
          command: ["python", "app.py"]
```

Check the EC2 GPU instance type and history price for spot instance, looks like the spot `g4dn.2xlarge` instance is very good choice with 8 vCPU and 32GB memory plus16GB GPU Memory with hourly cost $0.3121 could be a great choice to host some LLM models.

```bash
# list available GPU instances and spot price
root@zackz:/mnt/f/ml-local/local-cv# aws ec2 describe-spot-price-history \
    --instance-types $(aws ec2 describe-instance-types \
        --query 'InstanceTypes[?GpuInfo.Gpus!=null].InstanceType' --output text --region ap-southeast-2) \
    --product-descriptions "Linux/UNIX" \
    --start-time "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --region ap-southeast-2 \
    --query 'SpotPriceHistory[*].[InstanceType, SpotPrice]' \
    --output table
---------------------------------
|   DescribeSpotPriceHistory    |
+----------------+--------------+
|  g5.4xlarge    |  0.633900    |
|  g5.xlarge     |  0.396100    |
|  g5.8xlarge    |  0.996100    |
|  g6.12xlarge   |  1.890000    |
|  g5.48xlarge   |  6.971800    |
|  g5.12xlarge   |  2.227300    |
|  g4dn.metal    |  3.076200    |
|  g5.4xlarge    |  0.644500    |
|  g5.2xlarge    |  0.482900    |
|  g4dn.xlarge   |  0.202500    |
|  gr6.4xlarge   |  0.615000    |
|  gr6.4xlarge   |  0.614200    |
|  g6.2xlarge    |  0.418500    |
|  g4dn.12xlarge |  1.421100    |
|  g6.16xlarge   |  1.397200    |
|  g5.8xlarge    |  0.991000    |
|  g4dn.2xlarge  |  0.290400    |
|  g4dn.16xlarge |  1.828200    |
|  g5.24xlarge   |  3.025700    |
|  g6.4xlarge    |  0.668600    |
|  g4dn.metal    |  3.893000    |
|  g4dn.metal    |  4.544200    |
|  g6.16xlarge   |  1.395900    |
|  g4dn.8xlarge  |  0.917800    |
|  g4dn.2xlarge  |  0.312100    |
|  g5.12xlarge   |  2.156600    |
|  g6.12xlarge   |  1.775700    |
|  g5.xlarge     |  0.401000    |
|  p3.2xlarge    |  1.248900    |
|  g6.24xlarge   |  2.484600    |
|  g6.8xlarge    |  0.796000    |
|  g6.2xlarge    |  0.459600    |
|  p3.16xlarge   |  9.822300    |
|  gr6.8xlarge   |  0.990000    |
|  gr6.8xlarge   |  1.080300    |
|  g5.16xlarge   |  1.683200    |
|  p3.8xlarge    |  4.944200    |
|  p2.16xlarge   |  11.141200   |
|  g5.48xlarge   |  6.229500    |
|  g4dn.16xlarge |  1.870900    |
|  g6.48xlarge   |  5.242900    |
|  g4dn.16xlarge |  1.655800    |
|  g6.4xlarge    |  0.524600    |
|  g6.xlarge     |  0.374900    |
|  g4dn.12xlarge |  1.478100    |
|  g6.8xlarge    |  0.760100    |
|  g6.24xlarge   |  2.538400    |
|  g4dn.xlarge   |  0.213200    |
|  g4dn.xlarge   |  0.205000    |
|  g6.xlarge     |  0.355200    |
|  g5.16xlarge   |  1.591500    |
|  g4dn.2xlarge  |  0.295700    |
|  p2.xlarge     |  0.530700    |
|  g4dn.8xlarge  |  0.888700    |
|  p5.48xlarge   |  38.966200   |
|  g4dn.4xlarge  |  0.478200    |
|  g5.2xlarge    |  0.490200    |
|  g4dn.8xlarge  |  0.830500    |
|  g4dn.4xlarge  |  0.442800    |
|  g4dn.12xlarge |  1.577900    |
|  g6.48xlarge   |  5.181000    |
|  g4dn.4xlarge  |  0.455200    |
|  g5.24xlarge   |  3.213500    |
|  p2.xlarge     |  1.542000    |
|  p2.8xlarge    |  12.336000   |
|  p2.8xlarge    |  12.336000   |
|  p2.16xlarge   |  24.672000   |
|  p5.48xlarge   |  127.816000  |
|  p5.48xlarge   |  127.816000  |
+----------------+--------------+
(END)

----------------------------------------------------------------------------------------------------

root@zackz:/mnt/f/ml-local/local-cv# aws ec2 describe-instance-types \
    --query 'InstanceTypes[?GpuInfo.Gpus!=null].[InstanceType, GpuInfo.Gpus[0].Manufacturer, GpuInfo.Gpus[0].Name, GpuInfo.Gpus[0].Count, GpuInfo.TotalGpuMemoryInMiB]' \
    --region ap-southeast-2 --output table
-----------------------------------------------------
|               DescribeInstanceTypes               |
+----------------+---------+-------+-----+----------+
|  g5.4xlarge    |  NVIDIA |  A10G |  1  |  24576   |
|  g6.24xlarge   |  NVIDIA |  L4   |  4  |  91552   |
|  g5.2xlarge    |  NVIDIA |  A10G |  1  |  24576   |
|  g4dn.metal    |  NVIDIA |  T4   |  8  |  131072  |
|  g6.8xlarge    |  NVIDIA |  L4   |  1  |  22888   |
|  g6.48xlarge   |  NVIDIA |  L4   |  8  |  183104  |
|  p2.8xlarge    |  NVIDIA |  K80  |  8  |  98304   |
|  g4dn.12xlarge |  NVIDIA |  T4   |  4  |  65536   |
|  p3.2xlarge    |  NVIDIA |  V100 |  1  |  16384   |
|  g5.24xlarge   |  NVIDIA |  A10G |  4  |  98304   |
|  p5.48xlarge   |  NVIDIA |  H100 |  8  |  655360  |
|  p4d.24xlarge  |  NVIDIA |  A100 |  8  |  327680  |
|  g5.12xlarge   |  NVIDIA |  A10G |  4  |  98304   |
|  g4dn.xlarge   |  NVIDIA |  T4   |  1  |  16384   |
|  g6.2xlarge    |  NVIDIA |  L4   |  1  |  22888   |
|  g5.xlarge     |  NVIDIA |  A10G |  1  |  24576   |
|  g5.16xlarge   |  NVIDIA |  A10G |  1  |  24576   |
|  g6.xlarge     |  NVIDIA |  L4   |  1  |  22888   |
|  g6.16xlarge   |  NVIDIA |  L4   |  1  |  22888   |
|  gr6.8xlarge   |  NVIDIA |  L4   |  1  |  22888   |
|  g6.12xlarge   |  NVIDIA |  L4   |  4  |  91552   |
|  g6.4xlarge    |  NVIDIA |  L4   |  1  |  22888   |
|  g4dn.16xlarge |  NVIDIA |  T4   |  1  |  16384   |
|  gr6.4xlarge   |  NVIDIA |  L4   |  1  |  22888   |
|  p2.xlarge     |  NVIDIA |  K80  |  1  |  12288   |
|  p3.16xlarge   |  NVIDIA |  V100 |  8  |  131072  |
|  g5.8xlarge    |  NVIDIA |  A10G |  1  |  24576   |
|  g4dn.8xlarge  |  NVIDIA |  T4   |  1  |  16384   |
|  g5.48xlarge   |  NVIDIA |  A10G |  8  |  196608  |
|  p3.8xlarge    |  NVIDIA |  V100 |  4  |  65536   |
|  p2.16xlarge   |  NVIDIA |  K80  |  16 |  196608  |
|  g4dn.4xlarge  |  NVIDIA |  T4   |  1  |  16384   |
|  g4dn.2xlarge  |  NVIDIA |  T4   |  1  |  16384   |
+----------------+---------+-------+-----+----------+
(END)
```

Karpenter logs for troubleshooting:

Unfortunately, the GPU instance for ML workload is not provisioned by Karpenter due to `Max spot instance count exceeded` and `insufficient capacity with VcpuLimitExceeded`, Here are the logs from the Karpenter controller:

```bash
kubectl -n karpenter logs -l app.kubernetes.io/name=karpenter
```

```text
{
  "level": "ERROR",
  "time": "2025-02-01T00:48:15.820Z",
  "logger": "controller.nodeclaim.lifecycle",
  "message": "creating instance, insufficient capacity, with fleet error(s),
              MaxSpotInstanceCountExceeded: Max spot instance count exceeded",
  "commit": "1072d3b",
  "nodeclaim": "gpu-pool-m7qwg",
  "nodepool": "gpu-pool"
}

{
  "level": "ERROR",
  "time": "2025-02-01T01:01:49.074Z",
  "logger": "controller.nodeclaim.lifecycle",
  "message": "creating instance, insufficient capacity, with fleet error(s),
              VcpuLimitExceeded: You have requested more vCPU capacity than your
              current vCPU limit of 0 allows for the instance bucket that the
              specified instance type belongs to. Please visit
              http://aws.amazon.com/contact-us/ec2-request to request an
              adjustment to this limit.",
  "commit": "1072d3b",
  "nodeclaim": "gpu-pool-m6c45",
  "nodepool": "gpu-pool"
}

{
  "level": "ERROR",
  "time": "2025-02-01T01:04:37.398Z",
  "logger": "controller.provisioner",
  "message": "Could not schedule pod, incompatible with nodepool \"gpu-pool\",
              daemonset overhead={\"cpu\":\"210m\",\"memory\":\"240Mi\",\"pods\":\"5\"},
              no instance type satisfied resources {\"cpu\":\"1210m\",\"memory\":\"4336Mi\",
              \"nvidia.com/gpu\":\"1\",\"pods\":\"6\"} and requirements
              karpenter.k8s.aws/instance-family In [g5 p3 p4],
              karpenter.sh/capacity-type In [on-demand spot],
              karpenter.sh/nodepool In [gpu-pool],
              kubernetes.io/arch In [amd64], workload-type In [custom-ml]
              (no instance type met all requirements)",
  "commit": "1072d3b",
  "pod": "default/custom-ml"
}
```

Need to engage with AWS support to request GPU instance limit increase.

[![image tooltip here](/images/mlops10-2.png)](/images/mlops10-2.png)

**Conclusion**

This exploration of deploying an ML workload to EKS with Karpenter revealed several critical insights for production-grade MLOps. Key takeaways include:

- ML docker container Optimization
- EKS with Karpenter ready for ML load deployment

I will continue to explore the performance and cost practices after approved GPU quotas, by leveraging spot GPU instances and cold start and model cache to reduce the performance factors, particularly in terms of initialization time, model download, and container image pull times.

Then I will deploy the frontend application and K8S services to expose the load balancer for image upload and prediction.
