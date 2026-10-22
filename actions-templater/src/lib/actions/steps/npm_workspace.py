"""Defaults for independent npm libraries sharing root CI scripts and a lockfile."""

import json
from pathlib import Path

from src.com.repo.common import is_monorepo
from src.lib.actions.steps.mono_repo import get_monorepo_modules


def workspace_defaults(ctx, m, *, tests=False):
    if not is_monorepo(ctx, m):
        return m
    settings = dict(m)
    settings.setdefault("node_version", "24")
    settings.setdefault("npm_install_command", "npm install")
    libraries = get_monorepo_modules(ctx, m)
    settings.setdefault("filter_paths", [
        *[(Path(m.get("monorepo-folder", "")) / folder / "**").as_posix() for folder in libraries],
        "common-ci/**", "package.json", "package-lock.json", "angular.json",
        "tsconfig*.json", "karma.conf.js", ".npmrc", ".github/actions.json",
        ".github/workflows/**",
    ])
    if tests:
        angular = Path(ctx.local_folder) / "angular.json"
        projects = json.loads(angular.read_text()).get("projects", {}) if angular.is_file() else {}
        applications = [name for name, project in projects.items()
                        if project.get("projectType") == "application"
                        and "test" in project.get("architect", project.get("targets", {}))]
        extra = m.get("npm_test_projects", applications)
        settings["monorepo-modules"] = list(dict.fromkeys([*libraries, *extra]))
        # Application sources can also consume every sibling library.
        settings["filter_paths"] = [*settings["filter_paths"],
            *[f"{project['root']}/**" for project in projects.values()
              if project.get("projectType") == "application" and project.get("root")]]
    return settings


def with_workspace_defaults(generator, *, tests=False):
    original = generator["function"]
    generator["function"] = lambda ctx, m: original(ctx, workspace_defaults(ctx, m, tests=tests))
    return generator
