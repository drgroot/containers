"""
A job is a combination of flights with the execution strategy

<jobname>:
  runs-on:
    - machine

   needs: <jobname>

   defaults:
    run:
      shell: bash

   strategy:
    fail-fast: boolean
    matrix:
      key: ${{ fromJSON(needs.<jobname>.outputs.<name> ) }}

   steps: List[steps] | Flight
"""

from enum import Enum
from typing import Callable, Dict, List, NotRequired, TypedDict

from src.com.actions.step import FLIGHT
from src.com.repo import MODIFIERS, RepoContext


class RUNS_ON(Enum):
    HALF_CORE = "half-core"
    SELF_HOSTED = "self-hosted"


JobStrategy = TypedDict(
    "JobStrategy",
    {
        "fail-fast": bool,
        "matrix": Dict[str, List[str] | str],
    },
)


class JobService(TypedDict):
    image: str
    env: NotRequired[Dict[str, str]]
    ports: NotRequired[List[int | str]]
    options: NotRequired[str]


Job = TypedDict(
    "Job",
    {
        "timeout-minutes": NotRequired[int],
        "name": NotRequired[str],
        "env": NotRequired[Dict[str, str]],
        "services": NotRequired[Dict[str, JobService]],
        "outputs": NotRequired[Dict[str, str]],
        "permissions": NotRequired[Dict[str, str]],
        "runs-on": List[str],
        "needs": NotRequired[str | List[str]],
        "strategy": NotRequired[JobStrategy],
        "steps": FLIGHT,
        "if": NotRequired[str],
    },
)

JOB_GENERATOR = Callable[[RepoContext, MODIFIERS], Job]
