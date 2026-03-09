"""
Network Stack — creates a new VPC or imports an existing one.

Config (cdk.json → context.network):
  • existing_vpc_id : "" = create new  |  "vpc-xxx" = import existing
  • max_azs         : AZs for new VPC  (default 2)
  • nat_gateways    : NAT gateways     (default 1)

Exports:
  • vpc: ec2.IVpc
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
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        existing_vpc_id = network_config.get("existing_vpc_id", "")

        if existing_vpc_id:
            self.vpc = ec2.Vpc.from_lookup(
                self, "ImportedVpc", vpc_id=existing_vpc_id
            )
        else:
            self.vpc = ec2.Vpc(
                self,
                "Vpc",
                max_azs=network_config.get("max_azs", 2),
                nat_gateways=network_config.get("nat_gateways", 1),
            )

