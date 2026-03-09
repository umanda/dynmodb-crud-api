"""
Security Stack — Secrets Manager and IAM policies for DynamoDB access.

Config (cdk.json → context.security):
  • existing_secret_arn : "" = create new  |  "arn:..." = import existing
  • secret_name         : name for new secret (default "dynmodb-crud-api/auth0")

Exports:
  • auth0_secret : secretsmanager.ISecret
  • dynamo_policy: iam.ManagedPolicy (DynamoDB read/write for configured tables)
"""

from __future__ import annotations

from aws_cdk import Stack, aws_iam as iam, aws_secretsmanager as secretsmanager
from constructs import Construct


class SecurityStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        dynamo_tables: list[str],
        security_config: dict,
        app_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── Secrets Manager: Auth0 credentials ───────────────────────────────
        existing_secret_arn = security_config.get("existing_secret_arn", "")

        if existing_secret_arn:
            self.auth0_secret = secretsmanager.Secret.from_secret_complete_arn(
                self, "ImportedAuth0Secret", secret_complete_arn=existing_secret_arn
            )
        else:
            secret_name = security_config.get("secret_name", f"{app_name}/auth0")
            self.auth0_secret = secretsmanager.Secret(
                self,
                "Auth0Secret",
                secret_name=secret_name,
                description=f"Auth0 credentials for {app_name}",
                generate_secret_string=secretsmanager.SecretStringGenerator(
                    secret_string_template=(
                        '{"AUTH0_DOMAIN":"",'
                        '"AUTH0_AUDIENCE":"",'
                        '"AUTH0_CLIENT_ID":"",'
                        '"AUTH0_REALM":"Username-Password-Authentication"}'
                    ),
                    generate_string_key="AUTH0_CLIENT_SECRET",
                ),
            )

        # ── IAM managed policy: DynamoDB access ──────────────────────────────
        statements = []
        for table_name in dynamo_tables:
            table_arn = Stack.of(self).format_arn(
                service="dynamodb",
                resource="table",
                resource_name=table_name,
            )
            statements.append(
                iam.PolicyStatement(
                    actions=[
                        "dynamodb:BatchGetItem",
                        "dynamodb:BatchWriteItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "dynamodb:UpdateItem",
                    ],
                    resources=[table_arn, f"{table_arn}/index/*"],
                )
            )

        self.dynamo_policy = iam.ManagedPolicy(
            self,
            "DynamoDbAccessPolicy",
            managed_policy_name=f"{app_name}-dynamodb-access",
            statements=statements,
        )
