# Deployment Guide — EC2 + Ansible and ECR + ECS

This guide covers two deployment options for the same FastAPI app.

## Choose a Deployment Path

| Path | Best for | Infra | Config Management | Deploy Unit |
|------|----------|-------|-------------------|-------------|
| EC2 + Ansible | Full host control, lowest migration effort | EC2 | Ansible | Docker container on EC2 |
| ECR + ECS (Fargate) | Docker-native managed runtime, less server ops | ECS/Fargate + ALB + ECR | Not required | Container image in ECR |

## Do You Need Ansible?

- For **EC2 deployments**: Yes, in this repository Ansible installs Docker and deploys the app.
- For **ECS/Fargate deployments**: No, Ansible is usually unnecessary because ECS schedules containers directly from ECR.
- Hybrid is possible: keep EC2 + Ansible working as-is, and add ECS as an experimental or staging path.

---

## Path A: Deploy with EC2 + Ansible (Current, Working)

## Prerequisites

| Tool | Install |
|------|---------|
| Python 3.10+ | <https://www.python.org/downloads/> |
| AWS CDK CLI | `npm install -g aws-cdk` |
| AWS CLI | <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html> |
| Ansible 2.15+ | `pip install ansible` |
| rsync | Required by the `synchronize` module (built-in on Linux/macOS) |

Ensure your AWS credentials are configured (`aws configure` or env vars).

## 1. Install CDK Dependencies

```bash
pip install -r requirements-cdk.txt
```

## 2. Configure

Create your local CDK config from the sample:

```powershell
Copy-Item cdk.json.sample cdk.json
```

All settings live in `cdk.json` → `context`:

| Key | Description | Default |
|-----|-------------|---------|
| `app_name` | Resource name prefix | `dynmodb-crud-api` |
| `region` | AWS region | `us-east-1` |
| `ec2.instance_type` | Instance size | `t3.micro` |
| `ec2.volume_size_gb` | Root EBS volume (GB) | `20` |
| `ec2.key_pair_name` | **Required** — EC2 Key Pair name for SSH | `""` |
| `ec2.ami_name` | AMI name pattern | `al2023-ami-2023.*-x86_64` |
| `ec2.allowed_ssh_cidrs` | CIDRs allowed to SSH | `["0.0.0.0/0"]` |
| `network.existing_vpc_id` | Import existing VPC (blank = create new) | `""` |
| `network.existing_subnet_id` | Import subnet (blank = auto-select) | `""` |
| `network.existing_sg_id` | Import security group (blank = create new) | `""` |

> **Important**: Set `ec2.key_pair_name` to the name of an existing EC2 Key Pair in your target region.  
> Restrict `ec2.allowed_ssh_cidrs` to your IP (e.g. `["203.0.113.10/32"]`) for production.

### 2.1 Create and Save EC2 Key Pair (Required)

`ec2.key_pair_name` must match an EC2 Key Pair that exists in the same AWS region as your deployment.

### Windows (PowerShell)

Create one with AWS CLI and save the private key locally:

```powershell
# 1) Choose a key name (this is what goes into cdk.json)
$KEY_NAME = "dynmodb-crud-api-dev"

# 2) Ensure local SSH folder exists
New-Item -ItemType Directory -Force "$HOME\.ssh" | Out-Null

# 3) Create key pair in AWS and save private key locally
aws ec2 create-key-pair `
  --region us-east-1 `
  --key-name $KEY_NAME `
  --query "KeyMaterial" `
  --output text | Out-File -FilePath "$HOME\.ssh\$KEY_NAME.pem" -Encoding ascii

# 4) Lock down file permissions
icacls "$HOME\.ssh\$KEY_NAME.pem" /inheritance:r /grant:r "$env:USERNAME:(R)"
```

### Linux / macOS (bash or zsh)

Create one with AWS CLI and save the private key locally:

```bash
# 1) Choose a key name (this is what goes into cdk.json)
KEY_NAME="dynmodb-crud-api-dev"

# 2) Ensure local SSH folder exists
mkdir -p ~/.ssh

# 3) Create key pair in AWS and save private key locally
aws ec2 create-key-pair \
  --region us-east-1 \
  --key-name "$KEY_NAME" \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/${KEY_NAME}.pem

# 4) Lock down file permissions
chmod 400 ~/.ssh/${KEY_NAME}.pem
```

Then set the value in `cdk.json`:

```json
"ec2": {
  "key_pair_name": "dynmodb-crud-api-dev"
}
```

Notes:
1. Save the `.pem` file outside the repo (for example, `%USERPROFILE%\\.ssh\\...`).
2. Do not commit the `.pem` file to Git.
3. If the `.pem` file is lost, AWS cannot recover it. Create a new key pair and update `ec2.key_pair_name`.

## 3. Deploy Infrastructure (CDK)

```bash
# First time only
cdk bootstrap

# Deploy EC2 path only (recommended explicit command)
cdk deploy dynmodb-crud-api-network dynmodb-crud-api-compute \
  --require-approval never \
  -c deploy.mode=ec2
```

CDK outputs will show:

```
dynmodb-crud-api-compute.PublicIP = 54.x.x.x
dynmodb-crud-api-compute.SSHCommand = ssh -i <key>.pem ec2-user@54.x.x.x
dynmodb-crud-api-compute.AnsibleTarget = 54.x.x.x
```

## 4. Create and Configure Ansible Inventory

Create a local inventory file from the sample first:

```bash
cp ansible/inventory-sample.ini ansible/inventory.ini
```

> If your sample file is named `ansible/inventory.sample.ini` in your local branch, use:
>
> ```bash
> cp ansible/inventory.sample.ini ansible/inventory.ini
> ```

Then edit `ansible/inventory.ini` and replace the placeholder with the EC2 public IP and your real key:

```ini
[api]
54.x.x.x ansible_user=ec2-user ansible_ssh_private_key_file=~/.ssh/my-key.pem
```

## 5. Set App Environment Variables

Edit `ansible/group_vars/all.yml` and fill in the `app_env` section with your real values:

```yaml
app_env:
  AWS_ACCESS_KEY_ID: "AKIA..."
  AWS_SECRET_ACCESS_KEY: "..."
  AWS_DEFAULT_REGION: "us-east-1"
  ACTIVE_TABLES: "test-table"
  AUTH0_DOMAIN: "dev-umanda.us.auth0.com"
  AUTH0_AUDIENCE: "https://api.acme.test"
  AUTH0_CLIENT_ID: "..."
  AUTH0_CLIENT_SECRET: "..."
  AUTH0_REALM: "Username-Password-Authentication"
```

## 6. Test Ansible Connectivity

Before running the deployment playbook, verify SSH access from Ansible:

```bash
cd ansible
ansible api -i inventory.ini -m ping
```

Expected success output (example):

```text
3.92.74.59 | SUCCESS => {
  "changed": false,
  "ping": "pong"
}
```

> A Python interpreter discovery warning may appear. This is usually informational and does not block deployment.

## 7. Run Ansible Playbook

```bash
cd ansible
ansible-playbook playbook.yml
```

This will:
1. Install Docker on the EC2 instance
2. Copy the project files via rsync
3. Write the `.env` file from your variables
4. Build the Docker image using `Dockerfile.prod`
5. Start the container with `--restart unless-stopped` on port 80

## 8. Verify

```bash
# Swagger UI
curl http://<EC2_PUBLIC_IP>/docs

# Health check (if implemented)
curl http://<EC2_PUBLIC_IP>/
```

## Re-deploying Code Changes

After making code changes, just re-run the Ansible playbook:

```bash
cd ansible
ansible-playbook playbook.yml
```

This will rsync the updated code, rebuild the Docker image, and recreate the container.

## Teardown

```bash
cdk destroy --all
```

### Delete Entire CloudFormation Stacks Manually

If you want to force cleanup stack-by-stack using AWS CLI:

```bash
aws cloudformation delete-stack --stack-name dynmodb-crud-api-compute --region us-east-1
aws cloudformation delete-stack --stack-name dynmodb-crud-api-network --region us-east-1
```

Wait for deletion to complete:

```bash
aws cloudformation wait stack-delete-complete --stack-name dynmodb-crud-api-compute --region us-east-1
aws cloudformation wait stack-delete-complete --stack-name dynmodb-crud-api-network --region us-east-1
```

Optional: delete CDK bootstrap stack as well (only if not used by other CDK apps in the same account/region):

```bash
aws cloudformation delete-stack --stack-name CDKToolkit --region us-east-1
```

## Architecture

```
┌──────────────────────────────────────────┐
│  VPC (new or existing)                   │
│  ┌────────────────────────────────────┐  │
│  │  Public Subnet                     │  │
│  │  ┌──────────────────────────────┐  │  │
│  │  │  EC2 (Amazon Linux 2023)     │  │  │
│  │  │  ┌────────────────────────┐  │  │  │
│  │  │  │  Docker                │  │  │  │
│  │  │  │  ┌──────────────────┐  │  │  │  │
│  │  │  │  │ FastAPI :8000    │  │  │  │  │
│  │  │  │  └──────────────────┘  │  │  │  │
│  │  │  └────────────────────────┘  │  │  │
│  │  │  Port 80 → 8000              │  │  │
│  │  │  Auto-recovery alarm         │  │  │
│  │  └──────────────────────────────┘  │  │
│  │  SG: SSH(22) + HTTP(80) + HTTPS    │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
         ↑
   CloudWatch auto-recovery
   (StatusCheckFailed_System)
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Error reading config file ... ansible.cfg: File contains no section headers` | Ensure `ansible/ansible.cfg` is INI format and does **not** start with `---` |
| `no such identity: ~/.ssh/<your-key>.pem` | Replace placeholder key path in `ansible/inventory.ini` with a real `.pem` file path |
| `Permission denied (publickey)` right after deploy | Check EC2 `KeyName` is not `None`: `aws ec2 describe-instances --instance-ids <id> --region us-east-1 --query 'Reservations[0].Instances[0].KeyName' --output text` |
| EC2 `KeyName` is `None` | Set `cdk.json` -> `context.ec2.key_pair_name` and redeploy compute stack |
| SSH timeout | Check SG allows your IP on port 22 and key pair name is correct |
| Ansible `unreachable` | Verify inventory IP and SSH key path |
| Container not starting | SSH in and run `docker logs dynmodb-crud-api` |
| Port 80 not responding | Check SG allows HTTP. Run `docker ps` to verify container is running |
| `synchronize` fails | Install rsync: `sudo dnf install rsync -y` on the EC2 host |

---

## Path B: Deploy with ECR + ECS (Experimental)

This is the Docker-native AWS path and a good next experiment.

### Why ECR + ECS

1. No SSH or host patching required.
2. No Ansible needed for app rollout.
3. Rolling deployments and easier autoscaling.
4. Cleaner CI/CD flow: build image -> push to ECR -> deploy ECS service.

### Recommended AWS Architecture

1. ECR repository for app images (for example `dynmodb-crud-api`).
2. ECS Cluster (Fargate launch type).
3. ECS Task Definition using image from ECR and port `8000`.
4. ECS Service behind an Application Load Balancer (ALB).
5. CloudWatch Logs for container stdout/stderr.
6. Secrets Manager/SSM Parameter Store for sensitive env values.

### Implemented CDK Stacks in This Repository

ECS/ECR is now implemented with these stacks:

1. `infra/ecr_stack.py`
2. `infra/ecs_stack.py`

Stack selection is controlled by `cdk.json -> context.deploy.mode`:

1. `ec2`: deploy `network + compute`
2. `ecs`: deploy `network + ecr + ecs`
3. `both`: deploy all four stacks

Current stack names:

1. `dynmodb-crud-api-network`
2. `dynmodb-crud-api-compute`
3. `dynmodb-crud-api-ecr`
4. `dynmodb-crud-api-ecs`

Example deploy context:

```json
"deploy": {
  "mode": "both",
  "ecs": {
    "cpu": 256,
    "memory_mib": 512,
    "desired_count": 1,
    "container_port": 8000
  }
}
```

### Deploy ECS Infrastructure with CDK

```bash
# First time only
cdk bootstrap

# ECS path only
cdk deploy dynmodb-crud-api-network dynmodb-crud-api-ecr dynmodb-crud-api-ecs \
  --require-approval never \
  -c deploy.mode=ecs
```

Optional combined deployment:

```bash
cdk deploy --all --require-approval never -c deploy.mode=both
```

### Manual ECS Deployment Flow (Without GitHub Actions)

1. Create/Deploy infra with CDK (VPC/ECR/ECS/ALB).
2. Build container image locally.
3. Push image to ECR.
4. Update ECS service/task definition.

Example commands:

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Build and push
docker build -t dynmodb-crud-api:latest -f Dockerfile.prod .
docker tag dynmodb-crud-api:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/dynmodb-crud-api:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/dynmodb-crud-api:latest

# Trigger ECS rollout (if task def uses :latest)
aws ecs update-service \
  --cluster <ECS_CLUSTER_NAME> \
  --service <ECS_SERVICE_NAME> \
  --force-new-deployment \
  --region us-east-1
```

### CI/CD for ECS (Implemented Workflow)

For ECS you typically do not run Ansible in CD.

Pipeline stages:

1. CI (PR + push):
   - Python checks/tests
   - Docker build validation
   - Optional security scan
2. CD (main branch or manual):
   - Authenticate to AWS using GitHub OIDC role
   - Build and push image to ECR with immutable tag (commit SHA)
   - Update ECS task definition image
   - Deploy ECS service and wait for stability

Workflow file:

1. `.github/workflows/cd-deploy-ecs.yml`

How to run:

1. Open GitHub Actions.
2. Choose `CD Deploy ECS`.
3. Click `Run workflow`.
4. Optionally set `deploy_infra=true` to run CDK infra deployment first.

Required GitHub secret:

1. `AWS_ROLE_TO_ASSUME` (OIDC role ARN used by `aws-actions/configure-aws-credentials`)

Workflow inputs:

1. `aws_region`
2. `deploy_infra`
3. `ecr_repository`
4. `ecs_cluster`
5. `ecs_service`
6. `desired_count`

What the ECS workflow does:

1. Assumes AWS role via OIDC.
2. Optionally deploys CDK ECS infra.
3. Builds Docker image from `Dockerfile.prod`.
4. Pushes image tags `${GITHUB_SHA}` and `latest` to ECR.
5. Triggers ECS service rollout and waits for stability.

### Required IAM Permissions for ECS CD Role

At minimum, the GitHub OIDC-assumed role should be able to:

1. Push/pull images in ECR (`ecr:*` scoped to repo actions like `PutImage`, `InitiateLayerUpload`, `UploadLayerPart`, `CompleteLayerUpload`).
2. Register and describe task definitions (`ecs:RegisterTaskDefinition`, `ecs:DescribeTaskDefinition`).
3. Update ECS service (`ecs:UpdateService`, `ecs:DescribeServices`).
4. Pass execution/task roles (`iam:PassRole`) for the ECS task definition.

### Environment and Secrets Guidance for ECS

1. Non-secret config: task definition environment variables.
2. Secrets: AWS Secrets Manager or SSM Parameter Store references in task definition.
3. Avoid static AWS keys inside container env when possible.

### Observability for ECS

1. Enable CloudWatch logs in task definition.
2. Add ALB health check path (for example `/health`).
3. Use ECS service deployment alarms/rollback settings for safer releases.

### Teardown for ECS Resources

If you add ECS stacks in CDK, tear down by stack name:

```bash
cdk destroy <ecs-stack-name> <ecr-stack-name>
```

Or with CloudFormation CLI directly:

```bash
aws cloudformation delete-stack --stack-name <ecs-stack-name> --region us-east-1
aws cloudformation delete-stack --stack-name <ecr-stack-name> --region us-east-1
```
