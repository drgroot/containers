from typing import Any, Dict, NotRequired, TypedDict

from src.com.actions import Inventory
from src.com.actions.job import Job

Workflow = TypedDict(
    "Workflow",
    {
        "name": str,
        "env": NotRequired[Dict[str, str]],
        "run-name": NotRequired[str],
        "on": Dict[str, Any],
        "jobs": Dict[str, Job],
        "permissions": NotRequired[Dict[str, str]],
    },
)

WORKFLOW_GENERATOR = Inventory[Workflow]
