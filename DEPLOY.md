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

On Windows PowerShell, you can create one with AWS CLI and save the private key locally:

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

# Deploy
cdk deploy --all --require-approval never
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
