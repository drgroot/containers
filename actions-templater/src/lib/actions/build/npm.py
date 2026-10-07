from src.com.actions.step import STEP
from src.lib.actions.build import make_build
from src.lib.actions.steps.actions.setup import nodejs
from src.lib.actions.steps.actions.vault import process_vault_secrets
from src.lib.actions.steps.node import npm_login, npm_install
from src.com.repo import MODIFIERS, RepoContext
from src.com.repo.common import is_monorepo

NPM_VAULT_STEP_ID = "npm_secrets"
NPM_VAULT_PATH = "servc/data/iac/npm"
PUBLISH_IF = "github.ref_type == 'tag' && (github.event_name == 'push' || github.event_name == 'workflow_dispatch')"


def make_npm_build(ctx: RepoContext, m: MODIFIERS) -> list[STEP]:
    mono = is_monorepo(ctx, m)
    build_package_prefix = "@" + ctx.repo_owner.replace("-", "") + "/" if mono else ""
    clean_name = ctx.repo_owner.replace("-", "") + "-" if mono else ""
    npm_secrets, npm_vault = process_vault_secrets(
        NPM_VAULT_STEP_ID,
        [
            {"path": NPM_VAULT_PATH, "key": "npm_write_pass", "value": "NPMPASS"},
            {"path": NPM_VAULT_PATH, "key": "npm_write_user", "value": "NPMUSER"},
        ],
    )
    npm_modifiers = {**m, "npm_pass": npm_secrets["NPMPASS"], "npm_user": npm_secrets["NPMUSER"]}
    auth = [npm_vault(ctx, m), npm_login(ctx, npm_modifiers)]
    auth_after_build = m.get("npm_auth_after_build", False)
    if auth_after_build:
        for step in auth:
            step["if"] = PUBLISH_IF

    steps: list[STEP] = [
        *m.get("npm_setup_steps", []),
        nodejs(ctx, m),
        *(auth if not auth_after_build else []),
        npm_install(ctx, m),
    ]
    if mono:
        steps.append({
            "name": "Settle Depends",
            "working-directory": "",
            "env": {"FULL_NAME": "${{ matrix.package }}"},
            "run": f'''clean_name="${{FULL_NAME#{clean_name}}}"
echo clean_name=$clean_name >> $GITHUB_ENV
npm run-script merge
npm uninstall {build_package_prefix}$clean_name || true''',
        })
    steps.extend([
        {
            "name": "Setup Version",
            "env": {"TAG": "${{ env.current_version }}"},
            "working-directory": m.get("npm_version_directory", ""),
            "run": m.get("npm_version_command", 'npm version "$TAG" --no-git-tag-version --allow-same-version'),
        },
        {
            "name": "Build Package",
            "working-directory": "",
            "env": {"NODE_ENV": "production", **m.get("npm_build_env", {})},
            "run": m.get("npm_build_command", "cp tsconfig.prod.json tsconfig.json\nnpm run-script build ${{ matrix.package }}" if mono else "npm run-script build"),
        },
    ])
    publish_directory = m.get("npm_publish_directory", f"dist/{build_package_prefix}${{{{ env.clean_name }}}}" if mono else "dist")
    if m.get("npm_publish_tarball", False):
        steps.append({
            "id": "npm_package",
            "name": "Pack Package",
            "working-directory": publish_directory,
            "run": '''set -euo pipefail
npm pack --pack-destination "$RUNNER_TEMP" --json > "$RUNNER_TEMP/npm-pack.json"
filename=$(node --input-type=module -e 'import fs from "node:fs"; console.log(JSON.parse(fs.readFileSync(process.argv[1], "utf8"))[0].filename)' "$RUNNER_TEMP/npm-pack.json")
echo "tarball=$RUNNER_TEMP/$filename" >> "$GITHUB_OUTPUT"''',
        })
    if auth_after_build:
        steps.extend(auth)
    publish: STEP = {
        "name": "Publish Package",
        "if": PUBLISH_IF,
        "working-directory": publish_directory,
        "run": "npm publish --registry=https://npm.yusufali.ca",
    }
    if m.get("npm_publish_tarball", False):
        publish["env"] = {
            "NPM_TARBALL": "${{ steps.npm_package.outputs.tarball }}",
            "NPM_DIST_TAG": "${{ env.npm_dist_tag }}",
        }
        publish["run"] = 'npm publish "$NPM_TARBALL" --registry=https://npm.yusufali.ca --tag "$NPM_DIST_TAG"'
    steps.append(publish)
    return steps


npm_build = make_build("npm", make_npm_build, context={"language": ["typescript"]})
