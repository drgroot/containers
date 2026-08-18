from typing import cast

from src.com.actions.step import STEP_GENERATOR, UsesStep
from src.com.repo import MODIFIERS, RepoContext
from src.lib.actions.steps.actions import CHECKOUT_VERSION


def checkout_f(ctx: RepoContext, m: MODIFIERS):
    withObj = {
        "submodules": True,
        "token": m.get("token", ""),
        "fetch-depth": 0 if m.get("fetch", "") else "",
        "fetch-tags": True if m.get("fetch", "") else "",
    }
    action = {
        "uses": f"actions/checkout@{m.get('CHECKOUT_VERSION', CHECKOUT_VERSION)}",
    }
    for key in [*withObj.keys()]:
        if withObj[key] == "":
            del withObj[key]

    return cast(UsesStep, {**action, "with": withObj})


checkout: STEP_GENERATOR = checkout_f
