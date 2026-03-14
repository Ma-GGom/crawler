from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
}


def normalize_url(url: str | None) -> str:
    if url is None:
        return ""

    raw = url.strip()
    if not raw:
        return ""
    if raw.lower() == "링크 없음":
        return ""
    if raw.startswith("//"):
        raw = f"https:{raw}"

    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw.lower()

    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return raw.lower()

    port = parsed.port
    if port is None:
        netloc = hostname
    elif (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        netloc = hostname
    else:
        netloc = f"{hostname}:{port}"

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS
    ]
    query = urlencode(sorted(filtered_query), doseq=True)

    return urlunparse((scheme, netloc, path, "", query, ""))
