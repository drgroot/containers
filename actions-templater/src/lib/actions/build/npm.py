from src.lib.actions.build import make_build
from src.lib.actions.steps.actions.setup import nodejs
from src.lib.actions.steps.actions.vault import process_vault_secrets
from src.lib.actions.steps.node import npm_login, npm_install
from src.com.repo import MODIFIERS, RepoContext
from src.com.repo.common import is_monorepo

NPM_VAULT_STEP_ID = "npm_secrets"
NPM_VAULT_PATH = "servc/data/iac/npm"


def make_npm_build(ctx: RepoContext, m: MODIFIERS):
    build_package_prefix = ""
    clean_name = ""
    npm_secrets, npm_vault = process_vault_secrets(
        NPM_VAULT_STEP_ID,
        [
            {
                "path": NPM_VAULT_PATH,
                "key": "npm_write_pass",
                "value": "NPMPASS",
            },
            {
                "path": NPM_VAULT_PATH,
                "key": "npm_write_user",
                "value": "NPMUSER",
            },
        ],
    )
    npm_modifiers = {
        **m,
        "npm_pass": npm_secrets["NPMPASS"],
        "npm_user": npm_secrets["NPMUSER"],
    }

    if is_monorepo(ctx, m):
        build_package_prefix = "@" + ctx.repo_owner.replace("-", "") + "/"
        clean_name = ctx.repo_owner.replace("-", "") + "-"

    return [
        nodejs(ctx, m),
        npm_vault(ctx, m),
        npm_login(ctx, npm_modifiers),
        npm_install(ctx, m),
        {
            "name": "Settle Depends",
            "working-directory": "",
            "env": {
                "FULL_NAME": "${{ matrix.package }}" if is_monorepo(ctx, m) else "true",
            },
            "run": f"""\
clean_name="${{FULL_NAME#{clean_name}}}"
echo clean_name=$clean_name >> $GITHUB_ENV

npm run-script merge
npm uninstall {build_package_prefix}$clean_name || true""" if is_monorepo(ctx, m) else "echo hi"
        },
        {
            "name": "Setup Version",
            "env": {
                "TAG": "${{ env.current_version }}",
            },
            "run": "npm version $TAG --no-git-tag-version",
        },
        {
            "name": "Build Package",
            "working-directory": "",
            "env": {
                "NODE_ENV": "production",
            },
            "run": """\
cp tsconfig.prod.json tsconfig.json
npm run-script build ${{ matrix.package }}
""" if is_monorepo(ctx, m) else "npm run-script build",
        },
        {
            "name": "Publish Package",
            "if": "github.ref_type == 'tag'",
            "working-directory": f"dist/{build_package_prefix}${{{{ env.clean_name }}}}" if is_monorepo(ctx, m) else "dist",
            "run": "npm publish --registry=https://npm.yusufali.ca",
        }
    ]


npm_build = make_build(
    "npm",
    make_npm_build,
    context={
        "language": ["typescript"],
    },
)
