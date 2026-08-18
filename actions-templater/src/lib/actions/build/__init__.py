from src.com.actions import STATIC_FILES
from src.com.actions.job import JOB_GENERATOR, Job
from src.com.actions.step import FLIGHT_GENERATOR
from src.com.actions.workflow import WORKFLOW_GENERATOR
from src.com.repo import CONTEXT_MATCHERS, MODIFIERS, RepoContext
from src.com.repo.common import is_monorepo
from src.lib.actions.steps.actions.common import checkout
from src.lib.actions.steps.actions.vault import process_vault_secrets
from src.lib.actions.steps.bash.version import get_version_step
from src.lib.actions.steps.filter import filter
from src.lib.actions.steps.mono_repo import get_monorepo_modules, transform_steps

SETUP_BUILD: FLIGHT_GENERATOR = lambda ctx, m: [
    x
    for x in [
        checkout(ctx, m),
        filter(ctx, m) if is_monorepo(ctx, m) else "",
        (
            process_vault_secrets("build_secrets", m.get("build_secrets", []))[1](ctx, m)
            if m.get("build_secrets")
            else ""
        ),
        # output: env.current_version, env.repository. id: get_version
    ]
    if not isinstance(x, str)
]

default_on = {
    "pull_request": {},
    "push": {
        "tags": ["*"],
    },
    "workflow_dispatch": {},
}


def merge_schedule(on: dict, schedule: object) -> dict:
    if not isinstance(schedule, list):
        return on

    normalized_schedule = []
    for item in schedule:
        if not isinstance(item, dict):
            continue
        cron = item.get("cron")
        if not isinstance(cron, str) or not cron.strip():
            continue
        normalized_schedule.append({"cron": cron})

    if not normalized_schedule:
        return on

    return {
        **on,
        "schedule": normalized_schedule,
    }


def make_build_flight(steps: FLIGHT_GENERATOR) -> FLIGHT_GENERATOR:
    def build_flight(ctx: RepoContext, m: MODIFIERS):
        new_modifiers: MODIFIERS = {**m}
        if is_monorepo(ctx, m):
            new_modifiers["tag_prefix"] = "${{ matrix.package }}-"

        steps_build = [get_version_step(ctx, new_modifiers), *steps(ctx, new_modifiers)]

        if is_monorepo(ctx, new_modifiers):
            transform_steps(steps_build, ctx, new_modifiers)

        return [*SETUP_BUILD(ctx, new_modifiers), *steps_build]

    return build_flight


def make_job(steps: FLIGHT_GENERATOR) -> JOB_GENERATOR:
    def build_job(ctx: RepoContext, m: MODIFIERS):
        job: Job = {
            "runs-on": ["ubuntu-latest"],
            "steps": make_build_flight(steps)(ctx, m),
        }

        if is_monorepo(ctx, m):
            modules = get_monorepo_modules(ctx, m)
            job["strategy"] = {"fail-fast": True, "matrix": {"package": modules}}

        return job

    return build_job


def make_build(
    name: str,
    steps: FLIGHT_GENERATOR,
    context: CONTEXT_MATCHERS = {},
    static: STATIC_FILES = [],
    modifiers: MODIFIERS = {},
    on=default_on,
) -> WORKFLOW_GENERATOR:
    if context is None:
        context = {}
    modifiers = {
        **modifiers,
        "workflow_action": "build",
        "artifact": name,
    }

    workflow: WORKFLOW_GENERATOR = {
        "context_matchers": {
            "artifact": [name],
            **context,
        },
        "negative_matchers": None,
        "filename": f".github/workflows/build-{name}.yml",
        "static": static,
        "function": lambda ctx, m: {
            "name": f"build-{name}",
            "on": merge_schedule(on, m.get("schedule")),
            "jobs": {
                f"build-{name}": make_job(steps)(ctx, {**modifiers, **m}),
            },
        },
    }

    return workflow
