from src.com.repo import MODIFIERS, RepoContext
from src.com.repo.common import is_monorepo
from src.lib.actions.steps.actions.vault import process_vault_secrets
from src.lib.actions.steps.actions.setup import nodejs
from src.lib.actions.steps.node import npm_install, npm_login
from src.lib.actions.test import make_test

NPM_VAULT_STEP_ID = "npm_secrets"
NPM_VAULT_PATH = "servc/data/iac/npm"


def make_npm_test(ctx: RepoContext, m: MODIFIERS):
    npm_secrets, npm_vault = process_vault_secrets(
        NPM_VAULT_STEP_ID,
        [
            {
                "path": NPM_VAULT_PATH,
                "key": "npm_read_pass",
                "value": "NPMPASS",
            },
            {
                "path": NPM_VAULT_PATH,
                "key": "npm_read_user",
                "value": "NPMUSER",
            },
        ],
    )
    npm_modifiers = {
        **m,
        "npm_pass": npm_secrets["NPMPASS"],
        "npm_user": npm_secrets["NPMUSER"],
    }

    return [
        nodejs(ctx, m),
        npm_vault(ctx, m),
        npm_login(ctx, npm_modifiers),
        npm_install(ctx, m),
        {
            "name": "Settle Depends",
            "working-directory": "",
            "run": "npm run-script merge" if is_monorepo(ctx, m) else "echo hi",
        },
        {
            "name": "Run Tests",
            "working-directory": "",
            "run": (
                "npm test ${{ matrix.package }}" if is_monorepo(ctx, m) else "npm test"
            ),
        },
    ]


npm_test = make_test(
    make_npm_test,
    context={
        "language": ["typescript"],
    },
)
