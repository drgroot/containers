from src.com.actions.workflow import WORKFLOW_GENERATOR
from src.com.repo import MODIFIERS, RepoContext


def _python_pip_options(_: RepoContext, __: MODIFIERS) -> None:
    return None


python_pip_options_static: WORKFLOW_GENERATOR = {
    "context_matchers": {
        "language": ["python"],
    },
    "negative_matchers": None,
    "filename": ".github/workflows/python-pip-options.yml",
    "static": [("python/pip-options.txt", "pip-options.txt")],
    "function": _python_pip_options,
}
