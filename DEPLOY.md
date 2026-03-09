# AWS Deployment Guide — CDK (Python)

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │          cdk.json (config)           │
                    └──────┬──────────┬──────────┬────────┘
                           │          │          │
                  ┌────────▼──┐  ┌────▼─────┐  ┌▼──────────┐
                  │  Network  │  │ Security │  │  Compute   │
                  │  Stack    │  │  Stack   │  │  Stack     │
                  │───────────│  │──────────│  │────────────│
                  │ VPC (new  │  │ Secrets  │  │ ECS Cluster│
                  │ or exist) │  │ Manager  │  │ Fargate    │
                  │           │  │ IAM      │  │ ALB (opt.) │
                  │           │  │ Policy   │  │ Auto-scale │
                  └───────────┘  └──────────┘  │ CloudWatch │
                                               └────────────┘
```

**Two deployment modes:**

| Mode | `enable_alb` | Use case | Cost |
|---|---|---|---|
| **ALB + Fargate** | `true` | Production — load balancing, health checks, stable DNS | ~$20/mo + ALB |
| **Fargate only** | `false` | Dev/test — public IP directly on task, no ALB | ~$10/mo |

---

## Prerequisites

1. **AWS CLI** configured (`aws configure`)
2. **AWS CDK CLI**:
   ```bash
   npm install -g aws-cdk
   ```
3. **Docker** running (CDK builds the image locally)
4. **Python 3.12+**

---

## Configuration — `cdk.json`

All settings live in `cdk.json` → `context`. **No hardcoded values in stack code.**

### General

| Key | Type | Description |
|---|---|---|
| `app_name` | string | Prefix for all resource names |
| `account` | string | AWS account ID (leave `""` to use CLI default) |
| `region` | string | AWS region |

### Tags

Applied to **every** resource across all stacks:

```json
"tags": {
  "Project": "dynmodb-crud-api",
  "Environment": "dev",
  "Owner": "umanda",
  "ManagedBy": "cdk"
}
```

### DynamoDB Tables

```json
"dynamo_tables": ["test-KCRChannel-retored"]
```

For production:

```json
"dynamo_tables": ["BMIChannel", "KCRChannel", "KoreaChannel"]
```

### Network

| Key | Type | Description |
|---|---|---|
| `existing_vpc_id` | string | `""` = create new VPC, `"vpc-abc123"` = use existing |
| `max_azs` | int | AZs for new VPC (ignored if using existing) |
| `nat_gateways` | int | NAT gateways for new VPC |

**Using your existing VPC:**

```json
"network": {
  "existing_vpc_id": "vpc-0abc123def456789",
  "max_azs": 2,
  "nat_gateways": 1
}
```

### Security

| Key | Type | Description |
|---|---|---|
| `existing_secret_arn` | string | `""` = create new secret, `"arn:aws:..."` = use existing |
| `secret_name` | string | Name for new secret (ignored if using existing) |

**Using your existing Secrets Manager secret:**

```json
"security": {
  "existing_secret_arn": "arn:aws:secretsmanager:us-east-1:123456789:secret:my-auth0-secret-AbCdEf",
  "secret_name": ""
}
```

Your secret must contain these JSON keys:
```json
{
  "AUTH0_DOMAIN": "dev-umanda.us.auth0.com",
  "AUTH0_AUDIENCE": "https://api.acme.test",
  "AUTH0_CLIENT_ID": "your-client-id",
  "AUTH0_CLIENT_SECRET": "your-client-secret",
  "AUTH0_REALM": "Username-Password-Authentication"
}
```

### Compute

| Key | Type | Default | Description |
|---|---|---|---|
| `enable_alb` | bool | `true` | `true` = ALB, `false` = direct public IP |
| `cpu` | int | `256` | Fargate CPU units (256 / 512 / 1024 / 2048 / 4096) |
| `memory_mib` | int | `512` | Memory in MiB |
| `desired_count` | int | `1` | Initial tasks |
| `min_capacity` | int | `1` | Min auto-scale |
| `max_capacity` | int | `4` | Max auto-scale |
| `cpu_scaling_target_percent` | int | `70` | CPU % threshold for scaling |
| `container_port` | int | `8000` | Port the app listens on |
| `log_retention_days` | int | `14` | CloudWatch log retention |

**Disable ALB (cheaper for dev):**

```json
"compute": {
  "enable_alb": false,
  "cpu": 256,
  "memory_mib": 512,
  "desired_count": 1,
  "min_capacity": 1,
  "max_capacity": 1,
  "container_port": 8000,
  "log_retention_days": 7
}
```

---

## Example: Using existing VPC + existing secret (no ALB)

```json
{
  "context": {
    "app_name": "dynmodb-crud-api",
    "account": "123456789012",
    "region": "us-east-1",
    "tags": {
      "Project": "dynmodb-crud-api",
      "Environment": "dev",
      "Owner": "umanda",
      "ManagedBy": "cdk"
    },
    "dynamo_tables": ["test-KCRChannel-retored"],
    "network": {
      "existing_vpc_id": "vpc-0abc123def456789"
    },
    "security": {
      "existing_secret_arn": "arn:aws:secretsmanager:us-east-1:123456789:secret:my-auth0-AbCdEf"
    },
    "compute": {
      "enable_alb": false,
      "cpu": 256,
      "memory_mib": 512,
      "desired_count": 1,
      "min_capacity": 1,
      "max_capacity": 1,
      "container_port": 8000,
      "log_retention_days": 7
    }
  }
}
```

---

## Testing Before Deploying

### 1. Install CDK dependencies

```bash
pip install -r requirements-cdk.txt
```

### 2. Synthesize — generate CloudFormation without deploying

```bash
cdk synth
```

This outputs the full CloudFormation YAML to `cdk.out/`. Review it to verify:
- Resource names and types
- IAM policies are least-privilege
- Tags are applied correctly
- No unexpected resources

### 3. Diff — compare against what's already deployed

```bash
cdk diff
```

Shows exactly what will be **added**, **changed**, or **removed**. Safe to run — changes nothing.

### 4. Validate the CloudFormation template

```bash
# After synth, validate with AWS
aws cloudformation validate-template \
  --template-body file://cdk.out/dynmodb-crud-api-compute.template.json
```

### 5. Dry-run with change sets (most thorough)

```bash
cdk deploy --no-execute
```

This creates a CloudFormation **change set** but does NOT execute it. You can review it in the AWS Console under CloudFormation → Change Sets, then approve or delete it.

### 6. Local Docker test (app itself)

The app still works with `docker compose` locally:

```bash
docker compose up --build -d
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

---

## Deploying

### Bootstrap (first time per account/region)

```bash
cdk bootstrap aws://ACCOUNT_ID/us-east-1
```

### Deploy all stacks

```bash
cdk deploy --all
```

### Deploy a single stack

```bash
cdk deploy dynmodb-crud-api-compute
```

CDK auto-includes dependencies (`network` and `security`).

### Access the API

**With ALB (`enable_alb: true`):**

CDK outputs the ALB DNS:
```
Outputs:
  dynmodb-crud-api-compute.LoadBalancerDNS = xxx.us-east-1.elb.amazonaws.com
  dynmodb-crud-api-compute.ServiceURL      = http://xxx.../docs
```

**Without ALB (`enable_alb: false`):**

Find the task public IP in the ECS console, then:
```
http://<TASK_PUBLIC_IP>:8000/docs
```

### Update Auth0 secret (if CDK created a new one)

```bash
aws secretsmanager put-secret-value \
  --secret-id dynmodb-crud-api/auth0 \
  --secret-string '{
    "AUTH0_DOMAIN": "dev-umanda.us.auth0.com",
    "AUTH0_AUDIENCE": "https://api.acme.test",
    "AUTH0_CLIENT_ID": "your-client-id",
    "AUTH0_CLIENT_SECRET": "your-client-secret",
    "AUTH0_REALM": "Username-Password-Authentication"
  }'
```

---

## Adding HTTPS

Requires a domain + ACM certificate. Update `infra/compute_stack.py`:

```python
from aws_cdk import aws_certificatemanager as acm, aws_route53 as route53

zone = route53.HostedZone.from_lookup(self, "Zone", domain_name="example.com")

certificate = acm.Certificate(self, "Cert",
    domain_name="api.example.com",
    validation=acm.CertificateValidation.from_dns(zone),
)

# Add to ApplicationLoadBalancedFargateService:
#   certificate=certificate,
#   domain_name="api.example.com",
#   domain_zone=zone,
#   redirect_http=True,
```

---

## Useful Commands

| Command | Description |
|---|---|
| `cdk synth` | Generate CloudFormation templates (no deploy) |
| `cdk diff` | Preview changes vs. what's deployed |
| `cdk deploy --all` | Deploy all stacks |
| `cdk deploy --no-execute` | Create change set only (dry run) |
| `cdk destroy --all` | Tear down all resources |
| `cdk watch` | Auto-deploy on file changes (dev) |

---

## Tear Down

```bash
cdk destroy --all
```

Removes all AWS resources created by the stacks.
