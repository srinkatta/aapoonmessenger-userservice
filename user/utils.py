def s3_url_extract(url):
    if "socialchain-dev" in url or "mediadev" in url:
        return "https://mediadev.aapoon.com"
    elif "socialchain-prod" in url or "media.aapoon.com" in url:
        return "https://media.aapoon.com"
    else:
        return "https://media.aapoon.com"


def clear_bucket_from_path(path):
    if "socialchain-dev" in path:
        path = path.replace("/socialchain-dev", "")
        return path
    elif "socialchain-prod" in path:
        path = path.replace("/socialchain-prod", "")
        return path
    else:
        return path
