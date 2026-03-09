"""
Network Stack — creates a new VPC or imports an existing one.

Config (cdk.json → context.network):
  • existing_vpc_id    : "" = create new  |  "vpc-xxx" = import
  • existing_subnet_id : "" = auto-select |  "subnet-xxx" = use specific
  • existing_sg_id     : "" = create new  |  "sg-xxx" = import
  • max_azs / nat_gateways : for new VPC only

Exports: vpc, subnet, security_group
"""

from __future__ import annotations

from aws_cdk import Stack, aws_ec2 as ec2
from constructs import Construct


class NetworkStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        network_config: dict,
        ec2_config: dict,
        app_config: dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        existing_vpc_id = network_config.get("existing_vpc_id", "")
        existing_subnet_id = network_config.get("existing_subnet_id", "")
        existing_sg_id = network_config.get("existing_sg_id", "")

        # ── VPC ──────────────────────────────────────────────────────────────
        if existing_vpc_id:
            self.vpc = ec2.Vpc.from_lookup(
                self, "ImportedVpc", vpc_id=existing_vpc_id
            )
        else:
            self.vpc = ec2.Vpc(
                self,
                "Vpc",
                max_azs=network_config.get("max_azs", 2),
                nat_gateways=network_config.get("nat_gateways", 0),
                subnet_configuration=[
                    ec2.SubnetConfiguration(
                        name="Public",
                        subnet_type=ec2.SubnetType.PUBLIC,
                        cidr_mask=24,
                    ),
                ],
            )

        # ── Subnet ───────────────────────────────────────────────────────────
        if existing_subnet_id:
            self.subnet = ec2.Subnet.from_subnet_id(
                self, "ImportedSubnet", existing_subnet_id
            )
        else:
            self.subnet = self.vpc.public_subnets[0]

        # ── Security Group ───────────────────────────────────────────────────
        if existing_sg_id:
            self.security_group = ec2.SecurityGroup.from_security_group_id(
                self, "ImportedSg", existing_sg_id
            )
        else:
            self.security_group = ec2.SecurityGroup(
                self,
                "Ec2Sg",
                vpc=self.vpc,
                description="Allow SSH + HTTP/HTTPS",
                allow_all_outbound=True,
            )

            allowed_ssh_cidrs = ec2_config.get("allowed_ssh_cidrs", ["0.0.0.0/0"])
            for cidr in allowed_ssh_cidrs:
                self.security_group.add_ingress_rule(
                    ec2.Peer.ipv4(cidr),
                    ec2.Port.tcp(22),
                    f"SSH from {cidr}",
                )

            self.security_group.add_ingress_rule(
                ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP"
            )
            self.security_group.add_ingress_rule(
                ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "HTTPS"
            )
