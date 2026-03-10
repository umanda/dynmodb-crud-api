"""ECS stack using Fargate + ALB with images sourced from ECR."""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
)
from constructs import Construct


class EcsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        app_name: str,
        vpc: ec2.IVpc,
        repository: ecr.IRepository,
        app_config: dict,
        ecs_config: dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        container_port = int(app_config.get("container_port", 8000))
        cpu = int(ecs_config.get("cpu", 256))
        memory_limit_mib = int(ecs_config.get("memory_mib", 512))
        desired_count = int(ecs_config.get("desired_count", 0))
        image_tag = str(ecs_config.get("image_tag", "latest"))
        health_check_path = str(ecs_config.get("health_check_path", "/health"))
        assign_public_ip = bool(ecs_config.get("assign_public_ip", True))

        cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=vpc,
            cluster_name=f"{app_name}-cluster",
        )

        task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDefinition",
            cpu=cpu,
            memory_limit_mib=memory_limit_mib,
        )

        log_group = logs.LogGroup(
            self,
            "AppLogGroup",
            log_group_name=f"/ecs/{app_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        container = task_definition.add_container(
            "ApiContainer",
            image=ecs.ContainerImage.from_ecr_repository(repository, image_tag),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix=app_name,
                log_group=log_group,
            ),
            environment={
                "AWS_DEFAULT_REGION": str(
                    app_config.get("aws_region", cdk.Stack.of(self).region)
                )
            },
        )
        container.add_port_mappings(
            ecs.PortMapping(
                container_port=container_port,
                protocol=ecs.Protocol.TCP,
            )
        )

        alb_sg = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",
            vpc=vpc,
            description="Allow public HTTP to ALB",
            allow_all_outbound=True,
        )
        alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP")

        service_sg = ec2.SecurityGroup(
            self,
            "ServiceSecurityGroup",
            vpc=vpc,
            description="Allow ALB to reach ECS service",
            allow_all_outbound=True,
        )
        service_sg.add_ingress_rule(
            alb_sg,
            ec2.Port.tcp(container_port),
            "ALB to ECS container port",
        )

        alb = elbv2.ApplicationLoadBalancer(
            self,
            "Alb",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_sg,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )

        listener = alb.add_listener(
            "HttpListener",
            port=80,
            open=True,
        )

        service = ecs.FargateService(
            self,
            "Service",
            cluster=cluster,
            task_definition=task_definition,
            service_name=f"{app_name}-service",
            desired_count=desired_count,
            assign_public_ip=assign_public_ip,
            security_groups=[service_sg],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )

        target_group = listener.add_targets(
            "EcsTargets",
            port=container_port,
            targets=[service],
            health_check=elbv2.HealthCheck(
                path=health_check_path,
                healthy_http_codes="200-399",
                interval=cdk.Duration.seconds(30),
            ),
        )

        cdk.CfnOutput(
            self,
            "ClusterName",
            value=cluster.cluster_name,
            description="ECS cluster name",
        )
        cdk.CfnOutput(
            self,
            "ServiceName",
            value=service.service_name,
            description="ECS service name",
        )
        cdk.CfnOutput(
            self,
            "LoadBalancerDNS",
            value=alb.load_balancer_dns_name,
            description="ALB DNS name",
        )
        cdk.CfnOutput(
            self,
            "ServiceURL",
            value=f"http://{alb.load_balancer_dns_name}",
            description="Base URL for ECS deployment",
        )
        cdk.CfnOutput(
            self,
            "TargetGroupArn",
            value=target_group.target_group_arn,
            description="ALB target group ARN",
        )
