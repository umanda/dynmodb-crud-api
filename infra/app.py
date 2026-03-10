#!/usr/bin/env python3
"""AWS CDK entry point supporting EC2 and ECS deployment paths."""

import aws_cdk as cdk

from infra.compute_stack import ComputeStack
from infra.ecr_stack import EcrStack
from infra.ecs_stack import EcsStack
from infra.network_stack import NetworkStack

app = cdk.App()

# ── Config from cdk.json ─────────────────────────────────────────────────────
app_name: str = app.node.try_get_context("app_name") or "dynmodb-crud-api"
tags: dict = app.node.try_get_context("tags") or {}
network_config: dict = app.node.try_get_context("network") or {}
ec2_config: dict = app.node.try_get_context("ec2") or {}
app_config: dict = app.node.try_get_context("app") or {}
deploy_config: dict = app.node.try_get_context("deploy") or {}
deploy_mode_override = app.node.try_get_context("deploy.mode")

deploy_mode = str(
    deploy_mode_override or deploy_config.get("mode") or "ec2"
).lower()
if deploy_mode not in {"ec2", "ecs", "both"}:
    raise ValueError(
        "Invalid deploy.mode. Use one of: ec2, ecs, both"
    )

deploy_ecs_config: dict = deploy_config.get("ecs") or {}
deploy_ecr_config: dict = deploy_config.get("ecr") or {}

env = cdk.Environment(
    account=app.node.try_get_context("account") or None,
    region=app.node.try_get_context("region") or "us-east-1",
)

# ── Tags ─────────────────────────────────────────────────────────────────────
for key, value in tags.items():
    cdk.Tags.of(app).add(key, value)

# ── 1. Network (shared) ──────────────────────────────────────────────────────
network = NetworkStack(
    app,
    f"{app_name}-network",
    network_config=network_config,
    ec2_config=ec2_config,
    app_config=app_config,
    env=env,
)

# ── 2A. EC2 path ─────────────────────────────────────────────────────────────
if deploy_mode in {"ec2", "both"}:
    compute = ComputeStack(
        app,
        f"{app_name}-compute",
        vpc=network.vpc,
        subnet=network.subnet,
        security_group=network.security_group,
        ec2_config=ec2_config,
        app_config=app_config,
        app_name=app_name,
        env=env,
    )
    compute.add_dependency(network)

# ── 2B. ECS path ─────────────────────────────────────────────────────────────
if deploy_mode in {"ecs", "both"}:
    ecr_stack = EcrStack(
        app,
        f"{app_name}-ecr",
        app_name=app_name,
        ecr_config=deploy_ecr_config,
        env=env,
    )

    ecs_stack = EcsStack(
        app,
        f"{app_name}-ecs",
        app_name=app_name,
        vpc=network.vpc,
        repository=ecr_stack.repository,
        app_config=app_config,
        ecs_config=deploy_ecs_config,
        env=env,
    )
    ecr_stack.add_dependency(network)
    ecs_stack.add_dependency(network)
    ecs_stack.add_dependency(ecr_stack)

app.synth()
