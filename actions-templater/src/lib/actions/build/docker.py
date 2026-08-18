import os
from typing import Iterable, List, cast

from src.com.actions import STATIC_FILES
from src.com.actions.step import STEP, UsesStep
from src.com.repo import MODIFIERS, RepoContext
from src.com.repo.common import is_monorepo, is_servc
from src.lib.actions.build import default_on, make_build
from src.lib.actions.steps.actions.vault import process_vault_secrets
from src.lib.actions.test.npm import NPM_VAULT_PATH

docker_on = {**default_on, "push": {**default_on.get("push", {}), "branches": ["main"]}}
DOCKER_VAULT_STEP_ID = "docker_secrets"
DOCKER_VAULT_PATH = "servc/data/iac/docker"
DOCKER_REGISTRY_HOST_OUTPUT = "DOCKER_REGISTRY_HOST"
DOCKER_USERNAME_OUTPUT = "DOCKER_USERNAME"
DOCKER_PASSWORD_OUTPUT = "DOCKER_PASSWORD"
DOCKER_MIRROR_HOST_OUTPUT = "DOCKER_MIRROR_HOST"
DOCKER_MIRROR_USERNAME_OUTPUT = "DOCKER_MIRROR_USERNAME"
DOCKER_MIRROR_PASSWORD_OUTPUT = "DOCKER_MIRROR_PASSWORD"
DOCKER_ARTIFACT_STEP_ID = "docker_artifact"


def format_secret_build_args(
    m: MODIFIERS, secrets: str | Iterable[str] | None
) -> list[str] | None:
    """
    Convert a dot-separated string (or iterable) of secret names into Docker
    build-args that pass the secrets through to the build.
    """
    if secrets is None:
        return None
    build_secrets, _ = process_vault_secrets(
        "build_secrets", m.get("build_secrets", [])
    )

    if isinstance(secrets, str):
        secret_names = secrets.split(".")
    else:
        secret_names = list(secrets)
    secret_names.extend([x for x in build_secrets.keys() if x not in secret_names])

    build_args = []
    for secret in secret_names:
        secret_name = str(secret).strip()
        if not secret_name:
            continue
        secret_upper = secret_name
        secret_value = (
            f"${{{{ secrets.{secret_upper} }}}}"
            if secret_upper not in build_secrets
            else build_secrets[secret_upper]
        )
        build_args.append(f"{secret_upper}={secret_value}")

    return build_args if len(build_args) > 0 else None


def docker_build_steps(ctx: RepoContext, m: MODIFIERS) -> List[STEP]:
    if (
        is_servc(ctx, m)
        and m.get("language", "") in ("node", "typescript")
        and "npmpass" not in m.get("secrets", [])
    ):
        m.setdefault("build_secrets", []).extend(
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
            ]
        )

    build_args = format_secret_build_args(m, m.get("secrets", []))
    docker_secrets, docker_vault = process_vault_secrets(
        DOCKER_VAULT_STEP_ID,
        [
            {
                "path": DOCKER_VAULT_PATH,
                "key": "host",
                "value": DOCKER_REGISTRY_HOST_OUTPUT,
            },
            {
                "path": DOCKER_VAULT_PATH,
                "key": "username",
                "value": DOCKER_USERNAME_OUTPUT,
            },
            {
                "path": DOCKER_VAULT_PATH,
                "key": "password",
                "value": DOCKER_PASSWORD_OUTPUT,
            },
            {
                "path": DOCKER_VAULT_PATH,
                "key": "host-mirror",
                "value": DOCKER_MIRROR_HOST_OUTPUT,
            },
            {
                "path": DOCKER_VAULT_PATH,
                "key": "mirror-username",
                "value": DOCKER_MIRROR_USERNAME_OUTPUT,
            },
            {
                "path": DOCKER_VAULT_PATH,
                "key": "mirror-password",
                "value": DOCKER_MIRROR_PASSWORD_OUTPUT,
            },
        ],
    )
    docker_registry = docker_secrets[DOCKER_REGISTRY_HOST_OUTPUT]
    docker_mirror = docker_secrets[DOCKER_MIRROR_HOST_OUTPUT]
    docker_username = docker_secrets[DOCKER_USERNAME_OUTPUT]
    docker_password = docker_secrets[DOCKER_PASSWORD_OUTPUT]
    docker_mirror_username = docker_secrets[DOCKER_MIRROR_USERNAME_OUTPUT]
    docker_mirror_password = docker_secrets[DOCKER_MIRROR_PASSWORD_OUTPUT]
    steps: List[STEP] = [docker_vault(ctx, m)]

    package_name = (
        "${{ matrix.package }}" if is_monorepo(ctx, m) else ctx.repo_name
    )
    steps.append(
        {
            "id": DOCKER_ARTIFACT_STEP_ID,
            "name": "Set Docker Artifact",
            "env": {
                "DOCKER_REGISTRY_HOST": docker_registry,
                "DOCKER_USERNAME": docker_username,
                "PACKAGE_NAME": package_name,
            },
            "run": """\
set -euo pipefail

host="${DOCKER_REGISTRY_HOST#*://}"
host="${host%/}"
artifact_name="${DOCKER_USERNAME}/${PACKAGE_NAME}"

echo "repository=${host}" >> "$GITHUB_ENV"
echo "artifactname=${artifact_name}" >> "$GITHUB_ENV"
""",
        }
    )

    matrix_prefix = "${{ matrix.package }}" if is_monorepo(ctx, m) else ""
    build_push_inputs = {
        "context": matrix_prefix if is_monorepo(ctx, m) else m.get("context", "."),
        "file": (
            os.path.join(matrix_prefix, m.get("dockerfile", "Dockerfile"))
            if matrix_prefix
            else m.get("dockerfile", "Dockerfile")
        ),
        "push": "${{ (github.ref_name == 'main' || github.ref_type == 'tag') && 'true' || 'false' }}",
        "tags": "${{ env.repository }}/${{ env.artifactname }}:${{ env.current_version }}",
    }

    if build_args:
        build_push_inputs["build-args"] = "\n".join(build_args)

    steps.extend(
        [
            cast(
                UsesStep,
                {
                    "name": "Login to Mirror",
                    "uses": "docker/login-action@v3",
                    "with": {
                        "registry": docker_mirror,
                        "username": docker_mirror_username,
                        "password": docker_mirror_password,
                    },
                },
            ),
            cast(
                UsesStep,
                {
                    "name": "Login to ACR",
                    "uses": "docker/login-action@v3",
                    "with": {
                        "registry": "${{ env.repository }}",
                        "username": docker_username,
                        "password": docker_password,
                    },
                },
            ),
            cast(
                UsesStep,
                {
                    "name": "Set up Docker Buildx",
                    "uses": "docker/setup-buildx-action@v3",
                    "with": {
                        "driver": "docker-container",
                        "buildkitd-config-inline": f"""
[registry."docker.io"]
  mirrors = ["https://{docker_mirror}"]
""".strip(),
                    },
                },
            ),
            cast(
                UsesStep,
                {
                    "name": "Build and Push",
                    "uses": "docker/build-push-action@v5",
                    "with": build_push_inputs,
                },
            ),
        ]
    )
    return steps


def make_docker_language(language: str, files: STATIC_FILES):
    return make_build(
        "docker",
        docker_build_steps,
        context={
            "language": [language],
        },
        static=files,
        on=docker_on,
    )


docker = make_build(
    "docker",
    docker_build_steps,
    on=docker_on,
)

python_docker = make_docker_language("python", [])

node_docker = make_docker_language("node", [("node/Dockerfile", "Dockerfile")])
