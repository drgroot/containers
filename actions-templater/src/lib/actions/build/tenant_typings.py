"""Tenant pip and Node.js builds sharing the typings-* release version.

Tenant repositories own the compiler and npm package under typings/js. Compile
checked-out sources without fetching an adapter or a published tenant wheel.
"""
from typing import cast

from src.com.actions.job import Job
from src.com.actions.step import STEP, RunStep, UsesStep
from src.com.repo import MODIFIERS, RepoContext
from src.lib.actions.steps.actions.common import checkout
from src.lib.actions.steps.actions.setup import nodejs, python
from src.lib.actions.steps.actions.vault import process_vault_secrets
from src.lib.actions.steps.filter import filter

BUILD_IF = (
    "steps.changes.outputs.src == 'true' || github.ref_type == 'tag' || "
    "github.event_name == 'workflow_dispatch'"
)
PUBLISH_IF = (
    "github.ref_type == 'tag' && startsWith(github.ref_name, 'typings-') && "
    "(github.event_name == 'push' || github.event_name == 'workflow_dispatch')"
)


def _run(name: str, command: str, directory: str = "typings") -> RunStep:
    return {"name": name, "run": command, "working-directory": directory}


def _version(node: bool) -> RunStep:
    step = _run(
        "Set Shared Python and npm Version" if node else "Set Python Release Version",
        'set -euo pipefail\n'
        'version=$(python js/scripts/set_version.py "$REF_LONG")\n'
        'echo "current_version=$version" >> "$GITHUB_ENV"',
    )
    step["id"] = "get_version"
    step["env"] = {"REF_LONG": "${{ github.ref }}"}
    if node:
        step["run"] += (
            '\nif [[ "$version" == *-* ]]; then\n'
            '  echo "npm_dist_tag=next" >> "$GITHUB_ENV"\n'
            'else\n'
            '  echo "npm_dist_tag=latest" >> "$GITHUB_ENV"\n'
            'fi'
        )
    return step


def _vault(ctx: RepoContext, m: MODIFIERS, registry: str) -> tuple[dict[str, str], STEP]:
    keys = (
        [("username", "PYPI_USERNAME"), ("token", "PYPI_TOKEN"), ("url", "PYPI_URL")]
        if registry == "pip" else [("npm_write_user", "NPMUSER"), ("npm_write_pass", "NPMPASS")]
    )
    values, factory = process_vault_secrets(
        "publish_secrets",
        [{"path": f"servc/data/iac/{registry}", "key": key, "value": name} for key, name in keys],
    )
    step = factory(ctx, m)
    step["if"] = PUBLISH_IF
    return values, step


def _job(ctx: RepoContext, m: MODIFIERS, name: str, steps: list[STEP]) -> Job:
    scoped: list[STEP] = [
        checkout(ctx, m),
        filter(ctx, {"filter_paths": ["typings/**", ".github/workflows/build.yml", ".github/actions.json"]}),
        python(ctx, m),
        *steps,
    ]
    for step in scoped[2:]:
        if "if" not in step:
            step["if"] = BUILD_IF
    return {
        "name": name,
        "if": "github.ref_type != 'tag' || startsWith(github.ref_name, 'typings-')",
        "runs-on": ["ubuntu-latest"],
        "permissions": {"contents": "read", "pull-requests": "read"},
        "steps": scoped,
    }


def tenant_typings_jobs(ctx: RepoContext, m: MODIFIERS) -> dict[str, Job]:
    pip_secrets, pip_vault = _vault(ctx, m, "pip")
    pip_publish = _run("Publish Python Package", ".venv/bin/python -m twine upload --non-interactive dist/*")
    pip_publish["if"] = PUBLISH_IF
    pip_publish["env"] = {
        "TWINE_USERNAME": pip_secrets["PYPI_USERNAME"],
        "TWINE_PASSWORD": pip_secrets["PYPI_TOKEN"],
        "TWINE_REPOSITORY_URL": pip_secrets["PYPI_URL"],
    }
    pip = _job(ctx, m, "Build Typings Pip", [
        _version(False),
        _run("Install Python Build Dependencies", "python -m venv .venv\n.venv/bin/python -m pip install -r pip-options.txt -r requirements.txt build twine"),
        _run("Test Python Typings", 'if [ -d tests ]; then\n  .venv/bin/python -m unittest discover -s tests -p "test_*.py"\nfi'),
        _run("Build and Check Python Distribution", ".venv/bin/python -m build\n.venv/bin/python -m twine check dist/*"),
        pip_vault,
        pip_publish,
    ])

    npm_secrets, npm_vault = _vault(ctx, m, "npm")
    node_setup = cast(UsesStep, nodejs(ctx, {**m, "node_version": m.get("node_version", "24")}))
    node_setup["with"].update({"cache": "npm", "cache-dependency-path": "typings/js/package-lock.json"})
    compile_step = _run(
        "Compile All Python Modules to JavaScript and Declarations",
        'export PATH="$VIRTUAL_ENV/bin:$PATH"\nnpm run build\nnpm run check:python\nnpm test',
        "typings/js",
    )
    compile_step["env"] = {"VIRTUAL_ENV": "${{ github.workspace }}/typings/.venv"}
    pack = _run("Pack JavaScript Distribution", '''set -euo pipefail
npm pack --pack-destination "$RUNNER_TEMP" --json > "$RUNNER_TEMP/typings-pack.json"
filename=$(node --input-type=module -e 'import fs from "node:fs"; console.log(JSON.parse(fs.readFileSync(process.argv[1], "utf8"))[0].filename)' "$RUNNER_TEMP/typings-pack.json")
echo "tarball=$RUNNER_TEMP/$filename" >> "$GITHUB_OUTPUT"''', "typings/js")
    pack["id"] = "npm_package"
    npm_publish = _run("Publish JavaScript Package at the Same Version", '''set -euo pipefail
trap 'rm -f "$NPM_CONFIG_USERCONFIG"' EXIT
umask 077
auth=$(printf '%s' "$NPMUSER:$NPMPASS" | base64 | tr -d '\\n')
echo "::add-mask::$auth"
printf 'registry=https://npm.yusufali.ca/\\n@servc:registry=https://npm.yusufali.ca/\\n//npm.yusufali.ca/:_auth=%s\\n' "$auth" > "$NPM_CONFIG_USERCONFIG"
npm publish "$NPM_TARBALL" --registry=https://npm.yusufali.ca --tag "$NPM_DIST_TAG"''', "typings/js")
    npm_publish["if"] = PUBLISH_IF
    npm_publish["env"] = {
        **npm_secrets,
        "NPM_CONFIG_USERCONFIG": "${{ runner.temp }}/typings.npmrc",
        "NPM_TARBALL": "${{ steps.npm_package.outputs.tarball }}",
        "NPM_DIST_TAG": "${{ env.npm_dist_tag }}",
    }
    node = _job(ctx, m, "Build Typings Node.js", [
        node_setup,
        _version(True),
        _run("Install Python Compiler Dependencies", "python -m venv .venv\n.venv/bin/python -m pip install -r pip-options.txt -r requirements.txt"),
        _run("Install JavaScript Build Dependencies", "npm ci --ignore-scripts --registry=https://registry.npmjs.org", "typings/js"),
        compile_step,
        pack,
        npm_vault,
        npm_publish,
    ])
    return {"build-typings-pip": pip, "build-typings-nodejs": node}
