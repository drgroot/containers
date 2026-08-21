import os
from typing import Any

from pydantic import ValidationError
from servc.svc.com.worker.types import RESOLVER_CONTEXT, RESOLVER_RETURN_TYPE
from servc.svc.io.output import InvalidInputsException

from src.com.repo import RepoContext
from src.com.run import (
    add,
    checkout,
    clone,
    commit,
    get_config,
    push,
    submit_pull_request,
)
from src.config import CHANGE_BRANCH
from src.get_workflows import get_workflows
from src.lib.actions.dependabot import DEPENDABOT_AUTO_MERGE_FILENAME
from src.writeyaml import write_dependabot, write_workflow_file


def template_github_actions(
    id: str, payload: Any, context: RESOLVER_CONTEXT
) -> RESOLVER_RETURN_TYPE:
    print("Received payload", payload, flush=True)
    if not isinstance(payload, dict):
        raise InvalidInputsException("Payload must be a dictionary")
    try:
        repo_context = RepoContext.model_validate(payload)
    except ValidationError as e:
        raise InvalidInputsException(str(e))

    repo_owner = repo_context.repo_full_name.split("/")[0]
    repo_context.repo_owner = repo_owner
    target_branch = repo_context.branch
    print("Found context", repo_context.model_dump(), flush=True)

    try:
        local_path = clone(repo_context, target_branch)
    except Exception as e:
        print("Failed to clone repository", e, flush=True)
        return False

    extended_config = get_config(local_path)
    repo_context = RepoContext.model_validate(
        {
            **repo_context.model_dump(),
            **extended_config,
            "local_folder": local_path,
        }
    )
    print("Found context", repo_context.model_dump(), flush=True)

    workflows, dependabot = get_workflows(repo_context)
    print("Found workflows", workflows, "and dependabot", dependabot, flush=True)

    checkout(target_branch)
    changed_files = 0

    auto_merge_file = os.path.join(local_path, DEPENDABOT_AUTO_MERGE_FILENAME)
    if os.path.exists(auto_merge_file):
        os.remove(auto_merge_file)
        changed_files += 1
        print(f"Deleted {DEPENDABOT_AUTO_MERGE_FILENAME}", flush=True)

    for workflow in workflows:
        changed_files += write_workflow_file(repo_context, workflow, local_path)
    changed_files += write_dependabot(repo_context, dependabot, local_path)
    print("Changed files", changed_files, flush=True)

    if changed_files > 0:
        if not context.get("dry_run", False):
            checkout(CHANGE_BRANCH, ["-b"])
            add()
            commit("ci: pushing new workflows")
            push(CHANGE_BRANCH)
            print("Pushed changes to", CHANGE_BRANCH)

            submit_pull_request(target_branch, CHANGE_BRANCH, repo_context)
        return (changed_files, repo_context.repo_name)

    print("No changes to push", flush=True)
    return False
