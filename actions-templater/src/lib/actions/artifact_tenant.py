import copy
import os
from typing import cast

from src.com.actions.job import Job
from src.com.actions.workflow import WORKFLOW_GENERATOR, Workflow
from src.com.repo import CONTEXT_MATCHERS, MODIFIERS, RepoContext
from src.lib import PYTHON_VERSION
from src.lib.actions.build import merge_schedule
from src.lib.actions.build.docker import docker, docker_on, node_docker
from src.lib.actions.build.pip import pip_build
from src.lib.actions.build.npm import npm_build
from src.lib.actions.steps.actions.setup import python
from src.lib.actions.steps.python import pip_install
from src.lib.actions.common.semver import changelog
from src.lib.actions.steps.filter import filter
from src.lib.actions.test.npm import npm_test
from src.lib.actions.test.python import python_test

ARTIFACT_TENANT_CONTEXT: CONTEXT_MATCHERS = {"artifact": ["tenant"]}
BUILD_WORKFLOW = ".github/workflows/build.yml"
UNIT_WORKFLOW = ".github/workflows/unit.yml"


def tenant_name(ctx: RepoContext) -> str:
    """Return the tenant name used by artifacts and the typings package."""
    return ctx.repo_name


def component_path(ctx: RepoContext, component: str) -> str:
    return component


def component_filter_path(ctx: RepoContext, component: str) -> str:
    return os.path.join(component, "**")


def _job_from(
    generator: WORKFLOW_GENERATOR,
    ctx: RepoContext,
    modifiers: MODIFIERS,
    job_name: str,
) -> Job:
    workflow = generator["function"](ctx, copy.deepcopy(modifiers))
    if workflow is None:
        raise ValueError(f"Standard workflow did not generate job {job_name}")
    return copy.deepcopy(workflow["jobs"][job_name])


def _scope_job(
    ctx: RepoContext,
    job: Job,
    component: str,
    workflow_file: str,
    tag_prefix: str | None = None,
    working_directory: str | None = None,
) -> Job:
    """Scope a standard single-repository job to one tenant component."""
    paths = [component_filter_path(ctx, component)]
    if workflow_file in {BUILD_WORKFLOW, UNIT_WORKFLOW}:
        paths.append(workflow_file)
    if workflow_file == BUILD_WORKFLOW:
        paths.append(".github/actions.json")

    change_filter = filter(ctx, {"filter_paths": paths})
    steps = job["steps"]
    checkout_index = next(
        (
            index
            for index, step in enumerate(steps)
            if str(step.get("uses", "")).startswith("actions/checkout@")
        ),
        -1,
    )
    filter_index = checkout_index + 1
    steps.insert(filter_index, change_filter)

    condition = "steps.changes.outputs.src == 'true'"
    if tag_prefix is not None:
        condition = " || ".join(
            [condition, f"startsWith(github.ref, 'refs/tags/{tag_prefix}')"]
        )
    if workflow_file == BUILD_WORKFLOW:
        condition += " || github.event_name == 'workflow_dispatch'"
    condition = f"({condition})"
    working_directory = working_directory or component_path(ctx, component)

    for step in steps[filter_index + 1 :]:
        step["if"] = " && ".join(
            [value for value in [step.get("if", ""), condition] if value]
        )
        if "run" in step and not step.get("working-directory"):
            step["working-directory"] = working_directory

    return job


def _build_modifiers(
    ctx: RepoContext, m: MODIFIERS, component: str, artifact: str
) -> MODIFIERS:
    path = component_path(ctx, component)
    modifiers = {
        **copy.deepcopy(m),
        "mono": False,
        "artifact": artifact,
        "tag_prefix": f"{component}-",
    }
    if artifact == "docker":
        modifiers.update(
            {
                "artifactname": f"{tenant_name(ctx)}-{component}",
                "context": path,
                "dockerfile": os.path.join(path, m.get("dockerfile", "Dockerfile")),
                "arm_enable": m.get(f"arm{component}", m.get("arm_enable", False)),
            }
        )
    return modifiers


def artifact_tenant_build_workflow(ctx: RepoContext, m: MODIFIERS) -> Workflow:
    ui_modifiers = {
        **_build_modifiers(ctx, m, "ui", "docker"),
        "language": "node",
    }
    etl_modifiers = _build_modifiers(ctx, m, "etl", "docker")

    ui = _scope_job(
        ctx,
        _job_from(node_docker, ctx, ui_modifiers, "build-docker"),
        "ui",
        BUILD_WORKFLOW,
        "ui-",
    )
    etl = _scope_job(
        ctx,
        _job_from(docker, ctx, etl_modifiers, "build-docker"),
        "etl",
        BUILD_WORKFLOW,
        "etl-",
    )
    pip_modifiers = {
        **_build_modifiers(ctx, m, "typings", "pip"),
        "version_file": "pyproject.toml",
    }
    compiler_dependencies = pip_install(ctx, {**m, "install_dev_dependencies": False})
    compiler_dependencies["working-directory"] = "typings"
    npm_modifiers = {
        **_build_modifiers(ctx, m, "typings", "npm"),
        "version_file": "../pyproject.toml",
        "node_version": m.get("node_version", "24"),
        "npm_cache_path": "typings/js/package-lock.json",
        "npm_setup_steps": [python(ctx, m), compiler_dependencies],
        "npm_install_command": "npm ci --ignore-scripts --registry=https://registry.npmjs.org",
        "npm_version_directory": "typings",
        "npm_version_command": '.venv/bin/python js/scripts/set_version.py "$GITHUB_REF"',
        "npm_build_env": {"VIRTUAL_ENV": "${{ github.workspace }}/typings/.venv"},
        "npm_build_command": 'export PATH="$VIRTUAL_ENV/bin:$PATH"\nnpm run build\nnpm run check:python\nnpm test',
        "npm_auth_after_build": True,
        "npm_publish_directory": "typings/js",
        "npm_publish_tarball": True,
    }
    pip = _scope_job(ctx, _job_from(pip_build, ctx, pip_modifiers, "build-pip"), "typings", BUILD_WORKFLOW, "typings-")
    node = _scope_job(ctx, _job_from(npm_build, ctx, npm_modifiers, "build-npm"), "typings", BUILD_WORKFLOW, "typings-", "typings/js")
    for job, name in [(pip, "Build Typings Pip"), (node, "Build Typings Node.js")]:
        job["name"] = name
        job["if"] = "github.ref_type != 'tag' || startsWith(github.ref_name, 'typings-')"
        job["permissions"] = {"contents": "read", "pull-requests": "read"}
    ui["name"] = "Build UI"
    etl["name"] = "Build ETL"
    return {
        "name": "Build",
        "on": merge_schedule(docker_on, m.get("schedule")),
        "jobs": {
            "build-ui": ui,
            "build-etl": etl,
            "build-typings-pip": pip,
            "build-typings-nodejs": node,
        },
    }


def artifact_tenant_unit_workflow(ctx: RepoContext, m: MODIFIERS) -> Workflow:
    # actions.json is the ETL service configuration. The UI follows the normal
    # TypeScript defaults, while typings only shares its configured Python version.
    ui = _scope_job(
        ctx,
        _job_from(npm_test, ctx, {"mono": False}, "unittest"),
        "ui",
        UNIT_WORKFLOW,
    )

    etl_modifiers = {
        **copy.deepcopy(m),
        "mono": False,
        "artifact": "docker",
        "dockerfile": m.get("dockerfile", "Dockerfile"),
    }
    etl = _scope_job(
        ctx,
        _job_from(python_test, ctx, etl_modifiers, "unittest"),
        "etl",
        UNIT_WORKFLOW,
    )
    if isinstance(m.get("workflow_env"), dict):
        etl["env"] = copy.deepcopy(m["workflow_env"])

    typings_modifiers = {
        "mono": False,
        "artifact": "pip",
        "python_version": m.get("python_version", PYTHON_VERSION),
        "ci_folder_typecheck": tenant_name(ctx).replace("-", "_"),
        "ci_typecheck_only": True,
    }
    typings = _scope_job(
        ctx,
        _job_from(python_test, ctx, typings_modifiers, "unittest"),
        "typings",
        UNIT_WORKFLOW,
    )

    ui["name"] = "Test UI"
    etl["name"] = "Test ETL"
    typings["name"] = "Test Typings"
    return {
        "name": "Unit Test",
        "on": {"pull_request": {}},
        "jobs": {
            "unit-ui": ui,
            "unit-etl": etl,
            "unit-typings": typings,
        },
    }


def artifact_tenant_changelog_workflow(ctx: RepoContext, m: MODIFIERS) -> Workflow:
    workflow = changelog["function"](
        ctx,
        {
            **copy.deepcopy(m),
            "mono": True,
            "monorepo-folder": "",
            "monorepo-modules": ["ui", "etl", "typings"],
        },
    )
    if workflow is None:
        raise ValueError("Standard changelog workflow did not generate a workflow")
    return cast(Workflow, workflow)


artifact_tenant_build: WORKFLOW_GENERATOR = {
    "context_matchers": ARTIFACT_TENANT_CONTEXT,
    "negative_matchers": None,
    "filename": BUILD_WORKFLOW,
    "static": [
        ("python/pip-options.txt", "etl/pip-options.txt"),
        ("python/pip-options.txt", "typings/pip-options.txt"),
    ],
    "function": artifact_tenant_build_workflow,
}

artifact_tenant_unit: WORKFLOW_GENERATOR = {
    "context_matchers": ARTIFACT_TENANT_CONTEXT,
    "negative_matchers": None,
    "filename": UNIT_WORKFLOW,
    "static": [],
    "function": artifact_tenant_unit_workflow,
}

artifact_tenant_changelog: WORKFLOW_GENERATOR = {
    "context_matchers": ARTIFACT_TENANT_CONTEXT,
    "negative_matchers": None,
    "filename": ".github/workflows/changelog.yml",
    "static": [],
    "function": artifact_tenant_changelog_workflow,
}
