import re
from typing import Dict, List, TypedDict

from src.com.actions.job import JOB_GENERATOR
from src.com.actions.step import STEP_GENERATOR
from src.lib.actions.steps.actions.common import checkout
from src.lib.actions.steps.actions.setup import jq


class FILTER_STEP(TypedDict):
    step: STEP_GENERATOR
    inputs: Dict[str, str]


def matrix_setup_job(name: str, filters: Dict[str, FILTER_STEP]) -> JOB_GENERATOR:
    outputs: Dict[str, str] = {}
    steps: List[STEP_GENERATOR] = []

    for name, step in filters.items():
        id = re.sub(r"[^a-z]+", "", name.lower())
        if id in outputs:
            raise Exception("Duplicate output variable " + name)
        steps.append(
            lambda ctx, m: step["step"](ctx, {**m, **step["inputs"], "id": id})
        )
        outputs[id] = "${{ steps." + id + ".outputs.items }}"

    return lambda ctx, m: {
        "name": name,
        "runs-on": ["ubuntu-latest"],
        "steps": [
            checkout(ctx, m),
            jq(ctx, m),
            *[step(ctx, m) for step in steps],
        ],
        "outputs": outputs,
    }
