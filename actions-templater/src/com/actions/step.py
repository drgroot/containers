from typing import Callable, Dict, List, NotRequired, TypedDict

from src.com.repo import MODIFIERS, RepoContext

# there are a finite classifications of types of steps
# that can be seen in github actions
#
#  uses step   -> uses an action and has a with clause (or not)
#                 the with clause is a dictionary of key value pairs
#                 these are inputs into the action
#  run step    -> runs a command and can be multiline


BasicStep = TypedDict(
    "BasicStep",
    {
        "id": NotRequired[str],
        "if": NotRequired[str],
        "name": NotRequired[str],
        "env": NotRequired[Dict[str, str]],
        "continue-on-error": NotRequired[bool],
        "working-directory": NotRequired[str],
    },
)


class RunStep(BasicStep):
    run: str


UsesStepF = TypedDict(
    "UsesStepF", {"uses": str, "with": NotRequired[Dict[str, str | int | bool]]}
)


class UsesStep(BasicStep, UsesStepF):
    pass


STEP = RunStep | UsesStep

STEP_GENERATOR = Callable[[RepoContext, MODIFIERS], STEP]


"""
A flight is a collection of steps to achieve a specific task. For example a docker build has the following steps:

1. checkout code
2. build docker image
3. push docker image

The inputs of the steps will change based on context (for example) the matrix. Flights can be combined to form another flight.
"""

FLIGHT = List[STEP]

FLIGHT_GENERATOR = Callable[[RepoContext, MODIFIERS], FLIGHT]
