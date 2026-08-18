import requests

from src.config import REPO_SOURCE_MAP
from src.domains.template import template_github_actions
from src.lib import NODEJS_VERSION, PYTHON_VERSION

ORG_MAP = {
    "gitea": ["serv-c"],
    "github": ["serv-c"],
}
TOPIC_MAP = {
    "lang": "language",
    "vp": "version_prefix",
}

defaults = {
    "python_version": PYTHON_VERSION,
    "node_version": NODEJS_VERSION,
    "repository": "registry.yusufali.ca",
    "dockerfolder": "src",
    "tag": "latest",
}


def process_repo(repo):
    context = {
        "source": source,
        "repo_full_name": repo["full_name"],
        "repo_name": repo["name"],
        "clone_url": repo["clone_url"],
        **defaults,
    }

    topics = repo.get("topics")
    if "ignore" in topics:
        return None
    for topic in topics:
        if "-" in topic:
            key, value = topic.split("-")
            if key in TOPIC_MAP:
                key = TOPIC_MAP[key]
            context[key] = value
    return context


def get(url: str, token: str, path: str, params={}):
    return requests.get(
        url + path,
        params=params,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )


def get_paginated(url: str, token: str, path: str, params=None, limit: int = 100):
    page = 1
    items = []
    base_params = params or {}
    while True:
        page_params = {**base_params, "page": page, "limit": limit}
        response = get(url, token, path, page_params)
        response.raise_for_status()
        page_items = response.json()
        if not isinstance(page_items, list) or len(page_items) == 0:
            break
        items.extend(page_items)
        if len(page_items) < limit:
            break
        page += 1
    return items


jobs = []
for source, info in REPO_SOURCE_MAP.items():
    print("Processing source:", source)
    token = info.get("token")
    url = info.get("api_url")

    # get a list of personal repos
    repos = get_paginated(url, token, "/user/repos")
    for repo in repos:
        jobs.append(process_repo(repo))

    # list orgs
    for org in ORG_MAP.get(source, []):
        print("Processing org:", org)
        org_repos = get_paginated(url, token, f"/orgs/{org}/repos")
        for repo in org_repos:
            jobs.append(process_repo(repo))

for job in jobs:
    if not job:
        continue
    if "drgroot" in job["repo_full_name"] and job["source"] == "github":
        continue
    template_github_actions("id", job, {})
