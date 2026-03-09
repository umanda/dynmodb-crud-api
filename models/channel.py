from __future__ import annotations

from pynamodb.attributes import ListAttribute, MapAttribute, UnicodeAttribute
from pynamodb.models import Model

from config import AWS_ACCESS_KEY_ID, AWS_REGION, AWS_SECRET_ACCESS_KEY


class ChannelModel(Model):
    """
    PynamoDB model for a Channel item.

    The table has a composite key:
      - Partition key : id       (String)
      - Sort key      : service  (String)

    Other attributes are non-key and may be absent on older items.
    """

    class Meta:
        # Overridden at runtime per table — see ChannelModelFactory below
        table_name = "test-KCRChannel-retored"
        region = AWS_REGION
        aws_access_key_id = AWS_ACCESS_KEY_ID
        aws_secret_access_key = AWS_SECRET_ACCESS_KEY

    # Keys
    id = UnicodeAttribute(hash_key=True)
    service = UnicodeAttribute(range_key=True)

    # Optional attributes
    client = UnicodeAttribute(null=True)
    tv = UnicodeAttribute(null=True)
    label = UnicodeAttribute(null=True)
    project = UnicodeAttribute(null=True)
    url = ListAttribute(null=True)          # stored as list of {"S": "..."} or plain strings


def make_channel_model(table_name: str) -> type[ChannelModel]:
    """
    Dynamically create a ChannelModel subclass bound to a specific table.
    This lets us support multiple tables with the same schema without
    re-defining the model each time.
    """

    class DynamicChannelModel(ChannelModel):
        class Meta(ChannelModel.Meta):
            pass

    DynamicChannelModel.Meta.table_name = table_name
    DynamicChannelModel.__name__ = f"ChannelModel[{table_name}]"
    return DynamicChannelModel