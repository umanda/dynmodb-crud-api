"""ECR stack for storing application container images."""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import Stack, aws_ecr as ecr
from constructs import Construct


class EcrStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        app_name: str,
        ecr_config: dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        repository_name = ecr_config.get("repository_name") or app_name
        image_tag_mutability = str(
            ecr_config.get("image_tag_mutability") or "MUTABLE"
        ).upper()

        mutability = (
            ecr.TagMutability.IMMUTABLE
            if image_tag_mutability == "IMMUTABLE"
            else ecr.TagMutability.MUTABLE
        )

        self.repository = ecr.Repository(
            self,
            "ApiRepository",
            repository_name=repository_name,
            image_scan_on_push=bool(ecr_config.get("scan_on_push", True)),
            image_tag_mutability=mutability,
            # Keep data by default to avoid accidental image loss in experiments.
            removal_policy=cdk.RemovalPolicy.RETAIN,
            empty_on_delete=False,
        )

        cdk.CfnOutput(
            self,
            "RepositoryName",
            value=self.repository.repository_name,
            description="ECR repository name for app images",
        )
        cdk.CfnOutput(
            self,
            "RepositoryUri",
            value=self.repository.repository_uri,
            description="ECR repository URI",
        )
