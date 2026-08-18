import json
import os
import shutil
from subprocess import run
from typing import Any, Dict, List

import requests

from src.com.repo import RepoContext
from src.config import GIT_LOCAL_PATH, PR_TITLE, REPO_SOURCE_MAP

GIT_PATH = os.getenv("GIT_PATH", "git")


def git(cmd: List[str], cwd=None):
    return run([GIT_PATH, *cmd], cwd=cwd)


def get_config(local_path: str) -> Dict[str, Any]:
    config_path = os.path.join(local_path, ".github", "actions.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.loads(f.read())
    return {}


def get_children(local_path: str, folders_only=True, ignore_dot=True) -> List[str]:
    folders: List[str] = []
    if os.path.exists(local_path):
        for f in os.listdir(local_path):
            fname = os.path.join(local_path, f)
            if not os.path.isdir(fname) and folders_only:
                continue
            if ignore_dot and f.startswith("."):
                continue

            folders.append(f)
    folders.sort()
    return folders


def clone(repo: RepoContext, branch: str) -> str:
    if repo.source not in REPO_SOURCE_MAP:
        raise Exception("Unknown repository source")
    source = REPO_SOURCE_MAP[repo.source]
    token = source["token"]
    url = repo.clone_url.replace("https://", f"https://user:{token}@")

    if os.path.exists(GIT_LOCAL_PATH):
        shutil.rmtree(GIT_LOCAL_PATH)
    os.makedirs(GIT_LOCAL_PATH, exist_ok=True)

    print("Cloning repository", url, flush=True)
    if git(["clone", "-b", branch, "--single-branch", url, GIT_LOCAL_PATH]).returncode:
        raise Exception("Failed to clone repository")
    git(["fetch", "origin"], GIT_LOCAL_PATH)

    return GIT_LOCAL_PATH


def checkout(branch: str, args=None):
    if args is None:
        args = []
    if git(["checkout", *args, branch], GIT_LOCAL_PATH).returncode:
        raise Exception("Failed to checkout branch")


def add():
    git(["add", "."], GIT_LOCAL_PATH)


def commit(message: str):
    git(["commit", "-m", message], GIT_LOCAL_PATH)


def push(branch: str, args=None):
    if args is None:
        args = []
    if git(["push", "origin", branch, *args], GIT_LOCAL_PATH).returncode:
        print("Failed to push changes")


def submit_pull_request(base: str, branch: str, repo: RepoContext):
    if repo.source not in REPO_SOURCE_MAP:
        raise Exception("Unknown repository source")
    source = REPO_SOURCE_MAP[repo.source]
    token = source["token"]
    api_url = source["api_url"]

    r = requests.post(
        f"{api_url}/repos/{repo.repo_full_name}/pulls",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={
            "title": PR_TITLE,
            "body": "This PR was created by devopsbot!",
            "head": branch,
            "base": base,
        },
    )
    if r.status_code != 201 and "A pull request already exists for" not in r.text:
        print(f"Failed to create PR: {r.text}")
