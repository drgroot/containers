from typing import Any, Callable, Dict, List

from pydantic import BaseModel, ConfigDict

MODIFIERS = Dict[str, Any]
CONTEXT_MATCHERS = Dict[str, List[str] | None] | None
CONTEXT_CHECKER = Callable[["RepoContext", MODIFIERS], bool]


class RepoContext(BaseModel):
    source: str
    repo_full_name: str
    repo_name: str
    repo_owner: str = ""
    clone_url: str
    branch: str = "main"
    local_folder: str = ""

    model_config = ConfigDict(
        extra="allow",
    )
