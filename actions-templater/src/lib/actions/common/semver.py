import os
from typing import List

from src.com.actions.job import Job
from src.com.actions.step import FLIGHT, STEP
from src.com.actions.workflow import WORKFLOW_GENERATOR
from src.com.repo import MODIFIERS, RepoContext
from src.com.repo.common import is_monorepo
from src.lib.actions.steps.actions.common import checkout
from src.lib.actions.steps.actions.vault import get_git_token_steps
from src.lib.actions.steps.bash.git import get_latest_tag
from src.lib.actions.steps.filter import filter
from src.lib.actions.steps.mono_repo import get_monorepo_modules, get_working_path

CHANGELOG_ACTION_VERSION = os.getenv("CHANGELOG_ACTION_VERSION", "v6")
CREATE_RELEASE_ACTION_VERSION = os.getenv("CREATE_RELEASE_ACTION_VERSION", "v1")


def make_steps(ctx: RepoContext, m: MODIFIERS) -> FLIGHT:
    is_mono = is_monorepo(ctx, m)

    git_token, setup_steps = get_git_token_steps(
        ctx, m, m.get("token", "${{ github.token }}")
    )
    if setup_steps:
        m["token"] = git_token
    if is_mono:
        m["tag_prefix"] = "${{ matrix.package }}-"

    setup_steps.append(checkout(ctx, m))
    steps: List[STEP] = [
        get_latest_tag(id="previoustag")(ctx, m),
        {
            "name": "Generate new Tag",
            "id": "changelog",
            "if": "github.ref_name == 'main'",
            "uses": f"TriPSs/conventional-changelog-action@{m.get('CHANGELOG_ACTION_VERSION', CHANGELOG_ACTION_VERSION)}",
            "with": {
                "github-token": git_token,
                "git-url": "${{ github.server_url != 'https://github.com' && 'git.yusufali.ca' || 'github.com' }}",
                "output-file": False,
                "skip-version-file": True,
                "skip-commit": True,
                "skip-ci": False,
                "tag-prefix": m.get("tag_prefix", ""),
                "git-path": get_working_path(ctx, m) if is_mono else "",
                "fallback-version": "${{ env.last_tag }}",
            },
        },
    ]

    if is_mono:
        setup_steps.append(filter(ctx, m))
        for step in steps:
            step["if"] = " && ".join(
                [
                    x
                    for x in [
                        step.get("if", ""),
                        "steps.changes.outputs.src == 'true'",
                    ]
                    if x
                ]
            )

    return [*setup_steps, *steps]


def build_job(ctx: RepoContext, m: MODIFIERS):
    job: Job = {
        "name": "changelog",
        "runs-on": ["ubuntu-latest"],
        "steps": make_steps(ctx, m),
    }

    if is_monorepo(ctx, m):
        modules = get_monorepo_modules(ctx, m)
        job["strategy"] = {"fail-fast": True, "matrix": {"package": modules}}

    return job


changelog: WORKFLOW_GENERATOR = {
    "context_matchers": None,
    "negative_matchers": {
        "changelog": ["false"],
    },
    "filename": ".github/workflows/changelog.yml",
    "static": [],
    "function": lambda ctx, m: {
        "name": "CHANGELOG",
        "run-name": "CHANGELOG",
        "on": {
            "workflow_dispatch": {},
        },
        "permissions": {
            "contents": "write",
        },
        "jobs": {"changelog": build_job(ctx, m)},
    },
}
