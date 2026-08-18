from typing import Dict, List, Tuple

from src.com.actions import Inventory
from src.com.actions.workflow import WORKFLOW_GENERATOR
from src.com.repo import RepoContext
from src.lib.actions import GITHUB_ACTIONS_INVENTORY
from src.lib.dependabot import DEPENDABOT_INVENTORY, GENERATE_DEPENDABOT


def find_inventory(repo: RepoContext, inventory: List[Inventory]) -> List[Inventory]:
    inventory_files_candidates: Dict[str, List[Tuple[Inventory, int]]] = {}
    repo_context = repo.model_dump()

    for item in inventory:
        filename = item["filename"]
        if filename not in inventory_files_candidates:
            inventory_files_candidates[filename] = []
        if (
            item["context_matchers"] is not None
            and len(item["context_matchers"].keys()) == 0
        ):
            item["context_matchers"] = None

        # if a negative matcher is found. Ignore this item at all costs
        ignore = False
        if item["negative_matchers"] is not None:
            for key, values in item["negative_matchers"].items():
                if key not in repo_context:
                    continue
                if values is None or str(repo_context[key]) in values:
                    ignore = True
                    break
        if ignore:
            continue

        workflow_context = item["context_matchers"]
        # check if all context matchers keys are present and match
        found = True
        score = (
            1 if workflow_context is None and not item.get("context_checkers") else 0
        )
        if workflow_context is not None:
            for key, values in workflow_context.items():
                if key not in repo_context:
                    found = False
                    break
                if values is None or str(repo_context[key]) in values:
                    score += 1
                else:
                    found = False
                    break
        if found:
            for checker in item.get("context_checkers", []):
                if checker(repo, {}):
                    score += 1
                else:
                    found = False
                    break
        if found:
            inventory_files_candidates[item["filename"]].append((item, score))

    final_list: Dict[str, Inventory] = {}
    for key, value in inventory_files_candidates.items():
        top_score: int = -1
        if len(value) == 0:
            continue
        best_item: Inventory = value[0][0]

        for inventory_item, item_score in value:
            if item_score > top_score:
                top_score = item_score
                best_item = inventory_item

        if best_item:
            final_list[key] = best_item

    final_inventory: List[Inventory] = []
    for key, value in final_list.items():  # type: ignore
        final_inventory.append(value)  # type: ignore
    return final_inventory


def get_workflows(
    context: RepoContext,
) -> Tuple[List[WORKFLOW_GENERATOR], List[GENERATE_DEPENDABOT]]:
    return (
        find_inventory(context, GITHUB_ACTIONS_INVENTORY),
        find_inventory(context, DEPENDABOT_INVENTORY),
    )
