from src.lib.actions.build import make_build
from src.lib.actions.steps.actions.setup import python
from src.lib.actions.steps.actions.vault import process_vault_secrets
from src.lib.actions.steps.python import pip_install
from src.com.repo import MODIFIERS, RepoContext

PIP_VAULT_STEP_ID = "pip_secrets"
PIP_VAULT_PATH = "servc/data/iac/pip"


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

    return [
        python(ctx, m),
        pip_install(ctx, m),
        {
            "name": "Setup Version",
            "env": {
                "TAG": "${{ env.current_version }}",
            },
            "run": 'sed -i "s/version = .*/version = \\\"$TAG\\\"/g" pyproject.toml && cat pyproject.toml',
        },
        {
            "name": "Build Package",
            "run": ".venv/bin/python -m build",
        },
        pip_vault(ctx, m),
        {
            "name": "Publish Package",
            "if": "github.ref_type == 'tag'",
            "run": (
                ".venv/bin/python -m twine upload --verbose dist/* --non-interactive "
                f"-u{pip_secrets['PYPI_USERNAME']} "
                f"-p{pip_secrets['PYPI_TOKEN']} "
                f"--repository-url {pip_secrets['PYPI_URL']}"
            ),
        },
    ]


pip_build = make_build(
    "pip",
    make_pip_build,
    context={
        "language": ["python"],
    },
)
