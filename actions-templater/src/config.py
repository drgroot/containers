import os

COMPONENT_NAME = "actions"
PREFIX = os.environ.get("QUEUE_PREFIX", "")
QUEUE_NAME = os.environ.get("QUEUE_NAME", f"{PREFIX}{COMPONENT_NAME}")


GIT_LOCAL_PATH = os.environ.get("GIT_LOCAL_PATH", "/tmp/workingdir")
CHANGE_BRANCH = os.environ.get("CHANGE_BRANCH", "feature/devops")

GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GH_API_URL = os.getenv("API_URL", "https://api.github.com")
GITEA_TOKEN = os.getenv("GITEA_TOKEN", "asds")
GITEA_API_URL = os.getenv("GITEA_API_URL", "https://git.yusufali.ca/api/v1")
PR_TITLE = os.getenv("GH_PR_TITLE", "devopsbot update")

REPO_SOURCE_MAP = {
    # "github": {"api_url": GH_API_URL, "token": GH_TOKEN},
    "gitea": {"api_url": GITEA_API_URL, "token": GITEA_TOKEN},
}
