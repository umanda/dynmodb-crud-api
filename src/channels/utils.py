from src.channels.schemas import ChannelWrite


def extract_string(value) -> str:
    """Unwrap a DynamoDB typed value like {"S": "..."} or return plain string."""
    if isinstance(value, dict) and "S" in value:
        return value["S"]
    return str(value) if value is not None else ""


def normalize_item(item: dict, pk: str = "id") -> dict:
    """Convert a raw DynamoDB item into a normalized API response dict."""
    raw_urls = item.get("url") or item.get("urls")

    if isinstance(raw_urls, list):
        urls = []
        for u in raw_urls:
            if isinstance(u, dict):
                if "S" in u:
                    urls.append(u["S"])
                elif "url" in u:
                    urls.append(u["url"])
                else:
                    urls.append(str(u))
            else:
                urls.append(str(u))
    elif isinstance(raw_urls, dict):
        if "S" in raw_urls:
            urls = [raw_urls["S"]]
        elif "url" in raw_urls:
            urls = [raw_urls["url"]]
        else:
            urls = []
    elif isinstance(raw_urls, str):
        urls = [raw_urls]
    else:
        urls = []

    return {
        "ChannelCode": item.get(pk),
        "Client": item.get("client"),
        "TVorRadio": item.get("tv"),
        "Label": item.get("label"),
        "Project": item.get("project"),
        "Service": item.get("service"),
        "URLs": urls,
    }


def model_to_dynamo(model: ChannelWrite, pk: str = "id", sk: str | None = None) -> dict:
    """Convert a ChannelWrite Pydantic model into a DynamoDB item dict."""
    item = {
        pk: model.ChannelCode,
        "client": model.Client,
        "tv": model.TVorRadio,
        "label": model.Label,
        "project": model.Project,
        "service": model.Service,
        "url": model.URLs,
    }
    # Remove None values so we don't write nulls
    item = {k: v for k, v in item.items() if v is not None}
    # If table has a sort key and it's not already in the item, add it explicitly
    if sk and sk not in item and model.Service:
        item[sk] = model.Service
    return item
