"""CI defaults for independently installed npm packages in a monorepo."""

import json
from pathlib import Path

from src.com.repo.common import is_monorepo
from src.lib.actions.steps.mono_repo import get_monorepo_modules, get_working_path


def workspace_defaults(ctx, m, *, tests=False):
    if not is_monorepo(ctx, m):
        return m
    settings = dict(m)
    directory = get_working_path(ctx, m)
    settings.setdefault("node_version", "24")
    settings.setdefault("npm_working_directory", directory)
    settings.setdefault("npm_install_command", "npm install --prefix . --workspaces=false --include=dev")
    settings.setdefault("filter_paths", [
        f"{directory}/**", "common-ci/**", ".github/actions.json", ".github/workflows/**",
    ])
    if tests:
        angular = Path(ctx.local_folder) / "angular.json"
        projects = json.loads(angular.read_text()).get("projects", {}) if angular.is_file() else {}
        applications = [project["root"] for project in projects.values()
                        if project.get("projectType") == "application"
                        and "test" in project.get("architect", project.get("targets", {}))
                        and project.get("root")
                        and (Path(ctx.local_folder) / project["root"] / "package.json").is_file()]
        extra = m.get("npm_test_projects", applications)
        settings["monorepo-modules"] = list(dict.fromkeys([*get_monorepo_modules(ctx, m), *extra]))
    return settings


def with_workspace_defaults(generator, *, tests=False):
    original = generator["function"]
    def generate(ctx, m):
        workflow = original(ctx, workspace_defaults(ctx, m, tests=tests))
        if is_monorepo(ctx, m):
            for job in workflow["jobs"].values():
                if "strategy" in job:
                    job["strategy"]["fail-fast"] = False
        return workflow

    generator["function"] = generate
    return generator
