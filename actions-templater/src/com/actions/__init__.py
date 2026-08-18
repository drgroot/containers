from typing import Callable, List, NotRequired, Tuple, TypedDict

from src.com.repo import CONTEXT_CHECKER, CONTEXT_MATCHERS, MODIFIERS, RepoContext

STATIC_FILES = List[str | Tuple[str, str]]


class Inventory[T](TypedDict):
    context_matchers: CONTEXT_MATCHERS
    context_checkers: NotRequired[List[CONTEXT_CHECKER]]
    negative_matchers: CONTEXT_MATCHERS
    filename: str
    static: STATIC_FILES
    function: Callable[[RepoContext, MODIFIERS], T | None]
