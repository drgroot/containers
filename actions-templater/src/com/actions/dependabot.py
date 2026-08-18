from typing import TypedDict

from src.com.actions import Inventory


class CommitMessage(TypedDict):
    prefix: str


class Schedule(TypedDict):
    interval: str


Dependabot_Entry = TypedDict(
    "Dependabot_Entry",
    {
        "package-ecosystem": str,
        "directory": str,
        "commit-message": CommitMessage,
        "schedule": Schedule,
    },
)


GENERATE_DEPENDABOT = Inventory[Dependabot_Entry]
