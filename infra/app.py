#!/usr/bin/env python3
"""
AWS CDK entry point — reads all config from cdk.json and wires stacks.

Stacks:
  NetworkStack  → VPC (new or existing)
  SecurityStack → Secrets Manager + IAM DynamoDB policy
  ComputeStack  → ECS Fargate (with or without ALB)
"""

import aws_cdk as cdk

from infra.compute_stack import ComputeStack
from infra.network_stack import NetworkStack
from infra.security_stack import SecurityStack

app = cdk.App()

# ── Config from cdk.json context ─────────────────────────────────────────────
app_name = app.node.try_get_context("app_name") or "dynmodb-crud-api"
tags: dict = app.node.try_get_context("tags") or {}
dynamo_tables: list = app.node.try_get_context("dynamo_tables") or []
network_config: dict = app.node.try_get_context("network") or {}
security_config: dict = app.node.try_get_context("security") or {}
compute_config: dict = app.node.try_get_context("compute") or {}

env = cdk.Environment(
    account=app.node.try_get_context("account") or None,
    region=app.node.try_get_context("region") or "us-east-1",
)

# ── Apply tags to every resource in every stack ──────────────────────────────
for key, value in tags.items():
    cdk.Tags.of(app).add(key, value)

# ── 1. Network ───────────────────────────────────────────────────────────────
network = NetworkStack(
    app,
    f"{app_name}-network",
    network_config=network_config,
    env=env,
)

# ── 2. Security ──────────────────────────────────────────────────────────────
security = SecurityStack(
    app,
    f"{app_name}-security",
    dynamo_tables=dynamo_tables,
    security_config=security_config,
    app_name=app_name,
    env=env,
)

# ── 3. Compute ───────────────────────────────────────────────────────────────
compute = ComputeStack(
    app,
    f"{app_name}-compute",
    vpc=network.vpc,
    auth0_secret=security.auth0_secret,
    dynamo_policy=security.dynamo_policy,
    dynamo_tables=dynamo_tables,
    compute_config=compute_config,
    app_name=app_name,
    env=env,
)
compute.add_dependency(network)
compute.add_dependency(security)

app.synth()
