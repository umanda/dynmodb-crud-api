"""
Compute Stack — ECS Fargate service, optionally behind an ALB.

Config (cdk.json → context.compute):
  • enable_alb      : true = ALB + Fargate  |  false = Fargate with public IP
  • cpu / memory_mib / desired_count / min_capacity / max_capacity
  • cpu_scaling_target_percent
  • container_port
  • log_retention_days

Depends on:
  • NetworkStack  → vpc
  • SecurityStack → auth0_secret, dynamo_policy
"""

from __future__ import annotations

from pathlib import Path

import aws_cdk as cdk
from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_iam as iam,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)

# Map config value → logs.RetentionDays enum
_RETENTION_MAP = {
    1: logs.RetentionDays.ONE_DAY,
    3: logs.RetentionDays.THREE_DAYS,
    5: logs.RetentionDays.FIVE_DAYS,
    7: logs.RetentionDays.ONE_WEEK,
    14: logs.RetentionDays.TWO_WEEKS,
    30: logs.RetentionDays.ONE_MONTH,
    60: logs.RetentionDays.TWO_MONTHS,
    90: logs.RetentionDays.THREE_MONTHS,
    180: logs.RetentionDays.SIX_MONTHS,
    365: logs.RetentionDays.ONE_YEAR,
}


class ComputeStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        auth0_secret: secretsmanager.ISecret,
        dynamo_policy: iam.IManagedPolicy,
        dynamo_tables: list[str],
        compute_config: dict,
        app_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── Read config ──────────────────────────────────────────────────────
        cpu = compute_config.get("cpu", 256)
        memory_mib = compute_config.get("memory_mib", 512)
        desired_count = compute_config.get("desired_count", 1)
        min_capacity = compute_config.get("min_capacity", 1)
        max_capacity = compute_config.get("max_capacity", 4)
        scaling_target = compute_config.get("cpu_scaling_target_percent", 70)
        container_port = compute_config.get("container_port", 8000)
        enable_alb = compute_config.get("enable_alb", True)
        retention_days = compute_config.get("log_retention_days", 14)

        log_retention = _RETENTION_MAP.get(
            retention_days, logs.RetentionDays.TWO_WEEKS
        )

        # ── ECS Cluster ──────────────────────────────────────────────────────
        cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=vpc,
            container_insights_v2=ecs.ContainerInsights.ENABLED,
        )

        # ── CloudWatch log group ─────────────────────────────────────────────
        log_group = logs.LogGroup(
            self,
            "ApiLogGroup",
            log_group_name=f"/ecs/{app_name}",
            retention=log_retention,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ── Shared container config ──────────────────────────────────────────
        image = ecs.ContainerImage.from_asset(_REPO_ROOT, file="Dockerfile.prod")

        env_vars = {
            "AWS_DEFAULT_REGION": Stack.of(self).region,
            "ACTIVE_TABLES": ",".join(dynamo_tables),
        }

        secret_vars = {
            "AUTH0_DOMAIN": ecs.Secret.from_secrets_manager(
                auth0_secret, "AUTH0_DOMAIN"
            ),
            "AUTH0_AUDIENCE": ecs.Secret.from_secrets_manager(
                auth0_secret, "AUTH0_AUDIENCE"
            ),
            "AUTH0_CLIENT_ID": ecs.Secret.from_secrets_manager(
                auth0_secret, "AUTH0_CLIENT_ID"
            ),
            "AUTH0_CLIENT_SECRET": ecs.Secret.from_secrets_manager(
                auth0_secret, "AUTH0_CLIENT_SECRET"
            ),
            "AUTH0_REALM": ecs.Secret.from_secrets_manager(
                auth0_secret, "AUTH0_REALM"
            ),
        }

        container_health_check = ecs.HealthCheck(
            command=[
                "CMD-SHELL",
                f"curl -f http://localhost:{container_port}/health || exit 1",
            ],
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
            retries=3,
            start_period=Duration.seconds(15),
        )

        # ── Deploy mode: ALB or direct public IP ─────────────────────────────
        if enable_alb:
            fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
                self,
                "ApiService",
                cluster=cluster,
                cpu=cpu,
                memory_limit_mib=memory_mib,
                desired_count=desired_count,
                public_load_balancer=True,
                task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                    image=image,
                    container_port=container_port,
                    log_driver=ecs.LogDrivers.aws_logs(
                        stream_prefix="api", log_group=log_group
                    ),
                    environment=env_vars,
                    secrets=secret_vars,
                ),
                health_check=container_health_check,
            )

            fargate_service.target_group.configure_health_check(
                path="/health",
                healthy_http_codes="200",
            )

            task_role = fargate_service.task_definition.task_role
            ecs_service = fargate_service.service

            cdk.CfnOutput(
                self,
                "LoadBalancerDNS",
                value=fargate_service.load_balancer.load_balancer_dns_name,
                description="ALB DNS — use this to reach the API",
            )
            cdk.CfnOutput(
                self,
                "ServiceURL",
                value=(
                    f"http://{fargate_service.load_balancer.load_balancer_dns_name}"
                    "/docs"
                ),
                description="Swagger UI URL",
            )
        else:
            # ── No ALB — Fargate task with public IP (cheaper for dev/test) ──
            task_def = ecs.FargateTaskDefinition(
                self,
                "TaskDef",
                cpu=cpu,
                memory_limit_mib=memory_mib,
            )

            task_def.add_container(
                "ApiContainer",
                image=image,
                port_mappings=[
                    ecs.PortMapping(container_port=container_port)
                ],
                logging=ecs.LogDrivers.aws_logs(
                    stream_prefix="api", log_group=log_group
                ),
                environment=env_vars,
                secrets=secret_vars,
                health_check=container_health_check,
            )

            sg = ec2.SecurityGroup(
                self, "FargateSg", vpc=vpc, allow_all_outbound=True
            )
            sg.add_ingress_rule(
                ec2.Peer.any_ipv4(),
                ec2.Port.tcp(container_port),
                f"Allow inbound on port {container_port}",
            )

            fargate_no_alb = ecs.FargateService(
                self,
                "ApiService",
                cluster=cluster,
                task_definition=task_def,
                desired_count=desired_count,
                assign_public_ip=True,
                security_groups=[sg],
                vpc_subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PUBLIC
                ),
            )

            task_role = task_def.task_role
            ecs_service = fargate_no_alb

            cdk.CfnOutput(
                self,
                "Note",
                value=(
                    f"No ALB — connect directly to Fargate task public IP"
                    f" on port {container_port}"
                ),
                description="Access info (check ECS console for task public IP)",
            )

        # ── Auto-scaling ─────────────────────────────────────────────────────
        scaling = ecs_service.auto_scale_task_count(
            min_capacity=min_capacity,
            max_capacity=max_capacity,
        )
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=scaling_target,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )

        # ── IAM: attach DynamoDB policy to the task role ─────────────────────
        task_role.add_managed_policy(dynamo_policy)
