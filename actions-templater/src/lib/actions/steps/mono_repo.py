import os
from typing import List

from src.com.actions.step import STEP
from src.com.repo import MODIFIERS, RepoContext
from src.com.run import get_children


def get_monorepo_modules(ctx: RepoContext, m: MODIFIERS) -> List[str]:
    module_path = os.path.join(ctx.local_folder, m.get("monorepo-folder", ""))
    return get_children(module_path)


def get_working_path(ctx: RepoContext, m: MODIFIERS) -> str:
    return os.path.join(m.get("monorepo-folder", ""), "${{ matrix.package }}")


def transform_steps(steps: List[STEP], ctx: RepoContext, m: MODIFIERS):
    if_cond = "steps.changes.outputs.src == 'true'"
    if m.get("workflow_action", "build"):
        if_cond = " || ".join(
            [if_cond, "startsWith(github.ref,format('refs/tags/{0}-', matrix.package))"]
        )
    if_cond = f"({if_cond})"

    for step in steps:
        step["if"] = " && ".join([x for x in (step.get("if", ""), if_cond) if x])

        if "run" in step.keys():
            step["working-directory"] = step.get(
                "working-directory", get_working_path(ctx, m)
            ).strip()

            if step["working-directory"] == "":
                del step["working-directory"]
