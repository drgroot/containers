TOPIC_MAP = {
    "lang": "language",
    "vp": "version_prefix",
    "arm": "arm_enable",
}


def parse_topic(topic: str) -> tuple[str, str | bool] | None:
    if "-" not in topic:
        return None

    key, value = topic.split("-", 1)
    key = TOPIC_MAP.get(key, key)
    if key == "arm_enable":
        if value not in ("true", "false"):
            return None
        return key, value == "true"

    return key, value
