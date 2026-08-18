from src.com.actions.job import JOB_GENERATOR, Job
from src.com.actions.step import FLIGHT_GENERATOR
from src.com.actions.workflow import WORKFLOW_GENERATOR, Workflow
from src.com.repo import CONTEXT_MATCHERS, MODIFIERS, RepoContext
from src.com.repo.common import is_monorepo, is_spark
from src.lib.actions.steps.actions.common import checkout
from src.lib.actions.steps.actions.vault import process_vault_secrets
from src.lib.actions.steps.filter import filter
from src.lib.actions.steps.mono_repo import get_monorepo_modules, transform_steps

DEFAULT_RUNS_ON = ["ubuntu-latest"]
SPARK_RUNS_ON = ["ubuntu-spark"]


def get_runs_on(ctx: RepoContext, m: MODIFIERS) -> list[str]:
    default_runs_on = SPARK_RUNS_ON if is_spark(ctx, m) else DEFAULT_RUNS_ON
    runs_on = m.get("runs-on", default_runs_on)
    if isinstance(runs_on, str):
        return [runs_on]
    if isinstance(runs_on, list) and all(isinstance(item, str) for item in runs_on):
        return runs_on
    return default_runs_on


def make_test_flight(steps: FLIGHT_GENERATOR) -> FLIGHT_GENERATOR:
    def build_flight(ctx: RepoContext, m: MODIFIERS):
        new_modifiers: MODIFIERS = {**m}
        if is_monorepo(ctx, m):
            new_modifiers["tag_prefix"] = "${{ matrix.package }}-"

        steps_simple = [checkout(ctx, new_modifiers)]
        steps_after = [*m.get("ci_steps", []), *steps(ctx, new_modifiers)]

        if is_monorepo(ctx, new_modifiers):
            new_modifiers["append_filter"] = ["  - " + ".github/workflows/unit.yml"]
            steps_simple.append(filter(ctx, new_modifiers))
            transform_steps(steps_after, ctx, new_modifiers)

        if m.get("vault_secrets"):
            _, vault_step = process_vault_secrets(
                "test_vault_secrets", m.get("vault_secrets", [])
            )
            steps_simple.append(vault_step(ctx, new_modifiers))

        return [*steps_simple, *steps_after]

    return build_flight


def make_job(steps: FLIGHT_GENERATOR) -> JOB_GENERATOR:
    def build_job(ctx: RepoContext, m: MODIFIERS) -> Job:
        job: Job = {
            "runs-on": get_runs_on(ctx, m),
            "steps": make_test_flight(steps)(ctx, m),
        }

        ci_services = m.get("ci_services")
        if isinstance(ci_services, dict):
            job["services"] = ci_services

        secret_map, _ = process_vault_secrets(
            "test_vault_secrets", m.get("vault_secrets", [])
        )

        ci_env = m.get("ci_env")
        if isinstance(ci_env, dict):
            job["steps"][-1]["env"] = {
                **job["steps"][-1].get("env", {}),
                **ci_env,
            }
            for key in job["steps"][-1]["env"].keys():
                if key in secret_map:
                    job["steps"][-1]["env"][key] = secret_map[key]

        if is_monorepo(ctx, m):
            modules = get_monorepo_modules(ctx, m)
            job["strategy"] = {"fail-fast": True, "matrix": {"package": modules}}

        return job

    return build_job


def make_test(
    steps: FLIGHT_GENERATOR,
    context: CONTEXT_MATCHERS = {},
    modifiers: MODIFIERS = {},
) -> WORKFLOW_GENERATOR:
    if context is None:
        context = {}

    def build_workflow(ctx: RepoContext, m: MODIFIERS) -> Workflow:
        workflow: Workflow = {
            "name": "Unit Test",
            "on": {
                "pull_request": {},
            },
            "jobs": {
                "unittest": make_job(steps)(ctx, {**modifiers, **m}),
            },
        }
        workflow_env = m.get("workflow_env")
        if isinstance(workflow_env, dict):
            workflow["env"] = workflow_env
        return workflow

    workflow: WORKFLOW_GENERATOR = {
        "context_matchers": {
            **context,
        },
        "negative_matchers": None,
        "filename": ".github/workflows/unit.yml",
        "static": [],
        "function": build_workflow,
    }

    return workflow
