from src.lib.actions.build import make_build
from src.lib.actions.steps.actions.setup import python
from src.lib.actions.steps.actions.vault import process_vault_secrets
from src.lib.actions.steps.python import pip_install
from src.com.repo import MODIFIERS, RepoContext

PIP_VAULT_STEP_ID = "pip_secrets"
PIP_VAULT_PATH = "servc/data/iac/pip"
PUBLISH_IF = "github.ref_type == 'tag' && (github.event_name == 'push' || github.event_name == 'workflow_dispatch')"


def make_pip_build(ctx: RepoContext, m: MODIFIERS):
    pip_secrets, pip_vault = process_vault_secrets(
        PIP_VAULT_STEP_ID,
        [
            {
                "path": PIP_VAULT_PATH,
                "key": "username",
                "value": "PYPI_USERNAME",
            },
            {
                "path": PIP_VAULT_PATH,
                "key": "token",
                "value": "PYPI_TOKEN",
            },
            {
                "path": PIP_VAULT_PATH,
                "key": "url",
                "value": "PYPI_URL",
            },
        ],
    )

    vault = pip_vault(ctx, m)
    vault["if"] = PUBLISH_IF
    return [
        python(ctx, m),
        pip_install(ctx, m),
        {
            "name": "Setup Version",
            "env": {
                "TAG": "${{ env.current_version }}",
            },
            "run": 'sed -i "s/^version = .*/version = \\"$TAG\\"/" pyproject.toml',
        },
        {
            "name": "Build Package",
            "run": ".venv/bin/python -m build",
        },
        {
            "name": "Check Package",
            "run": ".venv/bin/python -m twine check dist/*",
        },
        vault,
        {
            "name": "Publish Package",
            "if": PUBLISH_IF,
            "env": {
                "TWINE_USERNAME": pip_secrets["PYPI_USERNAME"],
                "TWINE_PASSWORD": pip_secrets["PYPI_TOKEN"],
                "TWINE_REPOSITORY_URL": pip_secrets["PYPI_URL"],
            },
            "run": ".venv/bin/python -m twine upload --non-interactive dist/*",
        },
    ]


pip_build = make_build(
    "pip",
    make_pip_build,
    context={
        "language": ["python"],
    },
)
