#!/usr/bin/env python

import os

from pyarr import RadarrAPI, SonarrAPI

from src.radarr import get_radarr_items, search_radarr_item
from src.sonarr import get_sonarr_items, search_sonarr_item
from src.table import get_items, upsert_row

servers = [
    {
        "host_url": os.environ.get("RADARR_HOST"),
        "api_key": os.environ.get("RADARR_API_KEY", "fbab53fa0a474e28a4a4f31443a057ca"),
        "class": RadarrAPI,
        "get_items": get_radarr_items,
        "search_item": search_radarr_item,
    },
    {
        "host_url": os.environ.get("SONARR_HOST"),
        "api_key": os.environ.get("SONARR_API_KEY", "dfc4b7ca2bc8498f9c679d5021c16a2c"),
        "class": SonarrAPI,
        "get_items": get_sonarr_items,
        "search_item": search_sonarr_item,
    },
]

for server in servers:
    host_url = server["host_url"]
    if not host_url:
        continue
    narr = server["class"](host_url, server["api_key"])

    indexers = len(narr.get_indexer())

    for item in server["get_items"](narr):
        upsert_row(host_url, item["name"], item["id"], item["percent"], indexers)

    search = 0
    for item in narr.get_queue()["records"]:
        if item["status"].lower() not in ["unknown", "warning", "queued"]:
            search += 1
            print(item["status"])

    if search >= 5:
        continue

    for row in get_items(host_url, indexers):
        id, searchcount, percentfound, name = row

        item = {"id": id, "name": name, "percent": percentfound}
        server["search_item"](narr, item)
        upsert_row(host_url, name, id, percentfound, indexers, increment=1)
        print("searched for", name)
