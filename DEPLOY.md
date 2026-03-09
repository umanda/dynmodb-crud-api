# Deployment Guide — EC2 + Ansible

This guide walks through provisioning an EC2 instance with AWS CDK and configuring it with Ansible.

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

## 3. Deploy Infrastructure (CDK)

```bash
# First time only
cdk bootstrap

# Deploy
cdk deploy --all --require-approval never
```

CDK outputs will show:

```
dynmodb-crud-api-compute.PublicIP = 54.x.x.x
dynmodb-crud-api-compute.SSHCommand = ssh -i <key>.pem ec2-user@54.x.x.x
dynmodb-crud-api-compute.AnsibleTarget = 54.x.x.x
```

## 4. Configure Ansible Inventory

Edit `ansible/inventory.ini` and replace the placeholder with the EC2 public IP:

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
  ACTIVE_TABLES: "test-KCRChannel-retored"
  AUTH0_DOMAIN: "dev-umanda.us.auth0.com"
  AUTH0_AUDIENCE: "https://api.acme.test"
  AUTH0_CLIENT_ID: "..."
  AUTH0_CLIENT_SECRET: "..."
  AUTH0_REALM: "Username-Password-Authentication"
```

## 6. Run Ansible Playbook

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

## 7. Verify

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
│  │  │  Port 80 → 8000             │  │  │
│  │  │  Auto-recovery alarm         │  │  │
│  │  └──────────────────────────────┘  │  │
│  │  SG: SSH(22) + HTTP(80) + HTTPS   │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
         ↑
   CloudWatch auto-recovery
   (StatusCheckFailed_System)
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| SSH timeout | Check SG allows your IP on port 22 and key pair name is correct |
| Ansible `unreachable` | Verify inventory IP and SSH key path |
| Container not starting | SSH in and run `docker logs dynmodb-crud-api` |
| Port 80 not responding | Check SG allows HTTP. Run `docker ps` to verify container is running |
| `synchronize` fails | Install rsync: `sudo dnf install rsync -y` on the EC2 host |
