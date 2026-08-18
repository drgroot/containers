from typing import List

from src.com.actions import CONTEXT_MATCHERS
from src.com.actions.dependabot import GENERATE_DEPENDABOT
from src.lib import ACTION_DEFAULT_DEPENDABOT_INTERVAL


def generic_step(package: str, matchers: CONTEXT_MATCHERS) -> GENERATE_DEPENDABOT:
    return {
        "context_matchers": matchers,
        "negative_matchers": None,
        "filename": f".github/dependabot{package}.yml",
        "static": [],
        "function": lambda ctx, m: {
            "package-ecosystem": package,
            "directory": m.get("module_directory", "/"),
            "commit-message": {
                "prefix": "fix",
            },
            "schedule": {
                "interval": m.get(
                    "dependabot_interval", ACTION_DEFAULT_DEPENDABOT_INTERVAL
                ),
            },
        },
    }


# DOCKER = generic_step("docker", {"artifact": ["docker"]})

NPM = generic_step("npm", {"language": ["node", "javascript", "typescript"]})

PIP = generic_step("pip", {"language": ["python"]})

GITHUB_ACTIONS = generic_step("github-actions", {})

TERRAFORM = generic_step("terraform", {"language": ["hcl", "terraform"]})

MAVEN = generic_step("maven", {"build_type": ["maven"], "build": ["maven"]})

DEPENDABOT_INVENTORY: List[GENERATE_DEPENDABOT] = [
    # DOCKER,
    NPM,
    PIP,
    GITHUB_ACTIONS,
    TERRAFORM,
    MAVEN,
]
