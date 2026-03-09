"""
Compute Stack — EC2 instance with auto-recovery.

Config (cdk.json → context.ec2):
  • instance_type       : e.g. "t3.micro"
  • volume_size_gb      : root EBS size
  • key_pair_name       : SSH key pair (must exist in the region)
  • ami_name            : AMI name pattern for lookup
  • associate_public_ip : true/false

Exports: instance, public_ip, instance_id
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
)
from constructs import Construct


class ComputeStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        subnet: ec2.ISubnet,
        security_group: ec2.ISecurityGroup,
        ec2_config: dict,
        app_config: dict,
        app_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        instance_type_str = ec2_config.get("instance_type", "t3.micro")
        volume_size_gb = ec2_config.get("volume_size_gb", 20)
        key_pair_name = ec2_config.get("key_pair_name", "")
        ami_name = ec2_config.get("ami_name", "al2023-ami-2023.*-x86_64")
        associate_public_ip = ec2_config.get("associate_public_ip", True)

        # ── AMI lookup ───────────────────────────────────────────────────────
        ami = ec2.MachineImage.lookup(
            name=ami_name,
            owners=["amazon"],
        )

        # ── IAM role for the instance ────────────────────────────────────────
        role = iam.Role(
            self,
            "Ec2Role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
            ],
        )

        # ── Key pair (optional) ──────────────────────────────────────────────
        key_pair = None
        if key_pair_name:
            key_pair = ec2.KeyPair.from_key_pair_name(
                self, "KeyPair", key_pair_name
            )

        # ── EC2 Instance ─────────────────────────────────────────────────────
        self.instance = ec2.Instance(
            self,
            "ApiInstance",
            instance_type=ec2.InstanceType(instance_type_str),
            machine_image=ami,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[subnet]),
            security_group=security_group,
            role=role,
            key_pair=key_pair,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size_gb,
                        volume_type=ec2.EbsDeviceVolumeType.GP3,
                        delete_on_termination=True,
                    ),
                )
            ],
            associate_public_ip_address=associate_public_ip,
        )

        # ── EC2 Auto-Recovery (CloudWatch alarm) ─────────────────────────────
        recovery_alarm = cw.Alarm(
            self,
            "AutoRecoveryAlarm",
            metric=cw.Metric(
                namespace="AWS/EC2",
                metric_name="StatusCheckFailed_System",
                dimensions_map={"InstanceId": self.instance.instance_id},
                period=cdk.Duration.minutes(1),
                statistic="Maximum",
            ),
            evaluation_periods=2,
            threshold=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description=f"Auto-recover {app_name} EC2 on system failure",
        )
        recovery_alarm.add_alarm_action(
            cw_actions.Ec2Action(cw_actions.Ec2InstanceAction.RECOVER)
        )

        # ── Outputs ──────────────────────────────────────────────────────────
        cdk.CfnOutput(
            self,
            "InstanceId",
            value=self.instance.instance_id,
            description="EC2 instance ID",
        )
        cdk.CfnOutput(
            self,
            "PublicIP",
            value=self.instance.instance_public_ip,
            description="Public IP — use this to reach the API",
        )
        cdk.CfnOutput(
            self,
            "PublicURL",
            value=f"http://{self.instance.instance_public_ip}/docs",
            description="Swagger UI URL",
        )
        cdk.CfnOutput(
            self,
            "SSHCommand",
            value=f"ssh -i <key>.pem ec2-user@{self.instance.instance_public_ip}",
            description="SSH connection string",
        )
        cdk.CfnOutput(
            self,
            "AnsibleTarget",
            value=self.instance.instance_public_ip,
            description="Use this IP in ansible/inventory.ini",
        )
