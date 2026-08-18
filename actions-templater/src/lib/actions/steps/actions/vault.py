from typing import Dict, List, Tuple

from pydantic import BaseModel

from src.com.actions.step import STEP, STEP_GENERATOR
from src.com.repo import MODIFIERS, RepoContext
from src.com.repo.common import is_servc
from src.lib import VAULT_VERSION

GIT_TOKEN_VAULT_STEP_ID = "gitea_secrets"
GIT_TOKEN_VAULT_PATH = "servc/data/iac/gitea"
GIT_TOKEN_OUTPUT = "PAT_TOKEN"


class Secret(BaseModel):
    path: str
    key: str
    value: str


def process_vault_secrets(
    name: str, secrets: List[Dict[str, str] | Secret]
) -> Tuple[Dict[str, str], STEP_GENERATOR]:
    input_secrets = []
    d = {}
    for ds in secrets:
        s = Secret.model_validate(ds) if not isinstance(ds, Secret) else ds
        input_secrets.append(s)
        d[s.value] = f"${{{{ steps.{name}.outputs.{s.value} }}}}"

    return d, get_vault(name, input_secrets)


def get_git_token_steps(
    ctx: RepoContext, m: MODIFIERS, fallback_token: str
) -> Tuple[str, List[STEP]]:
    if not is_servc(ctx, m):
        return fallback_token, []

    git_secrets, git_vault = process_vault_secrets(
        GIT_TOKEN_VAULT_STEP_ID,
        [
            {
                "path": GIT_TOKEN_VAULT_PATH,
                "key": "token",
                "value": GIT_TOKEN_OUTPUT,
            },
        ],
    )

    return git_secrets[GIT_TOKEN_OUTPUT], [git_vault(ctx, m)]


def get_vault(name: str, input_secrets: List[Secret]) -> STEP_GENERATOR:
    secrets = []
    for s in input_secrets:
        secrets.append(f"{s.path} {s.key} | {s.value} ;")

    vault: STEP_GENERATOR = lambda ctx, m: {
        "id": name,
        "uses": f"hashicorp/vault-action@{m.get('vault_version', VAULT_VERSION)}",
        "with": {
            "url": m.get("vault_url", "${{ secrets.VAULT_ADDR }}"),
            "method": "userpass",
            "username": "${{ secrets.VAULT_USERNAME }}",
            "password": "${{ secrets.VAULT_PASSWORD }}",
            "secrets": "\n".join(secrets),
        },
    }

    return vault
