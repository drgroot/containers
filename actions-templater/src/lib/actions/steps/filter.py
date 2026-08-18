import os

from src.com.actions.step import STEP_GENERATOR
from src.com.repo import MODIFIERS, RepoContext


def filter_f(ctx: RepoContext, m: MODIFIERS):
    prefix = os.path.join(m.get("monorepo-folder", ""), "${{ matrix.package }}")
    sub_folders = []
    for folder in m.get("sub_folders", "").split(";"):
        sub_folders.append("  - " + os.path.join(prefix, folder, "**"))
    sub_folders.extend(m.get("append_filter", []))

    step = {
        "name": "Filter Changes",
        "uses": "dorny/paths-filter@v3",
        "id": "changes",
        "with": {"filters": f"""\
src:
{"\n".join(sub_folders)}
"""},
    }

    return step


filter: STEP_GENERATOR = filter_f
