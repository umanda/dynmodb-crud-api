import boto3

from src.config import settings


def get_dynamodb_resource():
    """Create and return a boto3 DynamoDB resource."""
    return boto3.resource(
        "dynamodb",
        region_name=settings.AWS_DEFAULT_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
