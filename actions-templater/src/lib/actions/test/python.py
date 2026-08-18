from src.com.actions.step import FLIGHT
from src.com.repo import MODIFIERS, RepoContext
from src.lib import PYTHON_VERSION
from src.lib.actions.steps.actions.setup import python
from src.lib.actions.steps.bash.version import get_docker_base_image_version_step
from src.lib.actions.steps.python import pip_install
from src.lib.actions.test import make_test


def get_docker_python_version_step(ctx: RepoContext, m: MODIFIERS):
    return get_docker_base_image_version_step(
        ctx,
        m,
        base_image="python",
        expected_version=m.get("python_version", PYTHON_VERSION),
        version_label="Python",
    )


def docker_python_version_check(ctx: RepoContext, m: MODIFIERS) -> FLIGHT:
    if m.get("artifact") != "docker":
        return []

    return [get_docker_python_version_step(ctx, m)]


def python_test_steps(ctx: RepoContext, m: MODIFIERS) -> FLIGHT:
    return [
        python(ctx, m),
        *docker_python_version_check(ctx, m),
        pip_install(ctx, m),
        {
            "name": "Type Check",
            "run": f".venv/bin/python -m mypy {m.get("ci_folder_typecheck", "*.py")} --check-untyped-defs",
        },
        {
            "name": "Run Tests",
            "run": """\
.venv/bin/python -m coverage run -m unittest discover -s tests -p "test_*.py"
.venv/bin/python -m coverage report -m --fail-under=70
""",
        },
    ]


python_test = make_test(
    python_test_steps,
    context={
        "language": ["python"],
    },
)
