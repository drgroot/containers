from src.com.actions.step import STEP
from src.com.repo import MODIFIERS, RepoContext
from src.com.repo.common import is_monorepo
from src.lib.actions.build import default_on, make_build
from src.lib.actions.steps.actions.vault import process_vault_secrets
from src.lib.actions.steps.mono_repo import get_working_path


def make_terraform_build(ctx: RepoContext, m: MODIFIERS) -> list[STEP]:
    module_path = get_working_path(ctx, m) if is_monorepo(ctx, m) else "."
    package_name = "${{ matrix.package }}" if is_monorepo(ctx, m) else ctx.repo_name
    secrets, vault = process_vault_secrets(
        "docker_secrets",
        [
            {"path": "servc/data/iac/docker", "key": key, "value": value}
            for key, value in [
                ("host", "DOCKER_REGISTRY"),
                ("username", "DOCKER_USERNAME"),
                ("password", "DOCKER_PASSWORD"),
            ]
        ],
    )
    steps: list[STEP] = [
        {
            "name": "Package Module",
            "env": {
                "MODULE_PATH": module_path,
                "MODULE_NAME": package_name,
                "MODULE_VERSION": "${{ env.current_version }}",
            },
            "run": '''set -euo pipefail
MODULE_NAME="${MODULE_NAME##*/}"
dist="$RUNNER_TEMP/terraform-modules"
mkdir -p "$dist"
archive="$dist/$MODULE_NAME-$MODULE_VERSION.zip"
rm -f "$archive"
cd "$MODULE_PATH"
zip -r "$archive" . -x \\
    '.git' '.git/*' '*/.git' '*/.git/*' \\
    '.terraform/*' '*/.terraform/*' \\
    '.terraform.lock.hcl' '*/.terraform.lock.hcl' \\
    '*.tfstate' '*.tfstate.*' \\
    'dist/*' '*/dist/*'
ls -l "$archive"''',
        },
        vault(ctx, m),
        {
            "id": "oci_metadata",
            "name": "Set OCI Metadata",
            "env": {
                "MODULE_NAME": package_name,
                "MODULE_VERSION": "${{ env.current_version }}",
                "VAULT_REGISTRY": secrets["DOCKER_REGISTRY"],
                "VAULT_USERNAME": secrets["DOCKER_USERNAME"],
            },
            "run": '''set -euo pipefail
registry="${VAULT_REGISTRY#*://}"
registry="${registry%/}"
username="${VAULT_USERNAME#/}"
username="${username%/}"
MODULE_NAME="${MODULE_NAME##*/}"
if [[ -z "$registry" || -z "$username" || "$registry" == */* || "$username" == */* ]]; then
    echo "Vault returned an invalid registry host or username"
    exit 1
fi
echo "repository=$registry" >> "$GITHUB_ENV"
echo "oci_repository=$registry/$username" >> "$GITHUB_ENV"
echo "oci_artifact=$registry/$username/$MODULE_NAME:$MODULE_VERSION" >> "$GITHUB_ENV"
echo "module_archive=$MODULE_NAME-$MODULE_VERSION.zip" >> "$GITHUB_ENV"''',
        },
        {
            "name": "Install ORAS",
            "run": """set -euo pipefail
ORAS_VERSION="1.2.2"
install_dir="$(mktemp -d)"
trap 'rm -rf "$install_dir"' EXIT
curl -fsSL "https://github.com/oras-project/oras/releases/download/v${ORAS_VERSION}/oras_${ORAS_VERSION}_linux_amd64.tar.gz" -o "$install_dir/oras.tar.gz"
tar -xzf "$install_dir/oras.tar.gz" -C "$install_dir"
sudo install "$install_dir/oras" /usr/local/bin/oras
oras version""",
        },
        {
            "name": "Login to OCI Registry",
            "env": {
                "REGISTRY_USERNAME": secrets["DOCKER_USERNAME"],
                "REGISTRY_PASSWORD": secrets["DOCKER_PASSWORD"],
            },
            "run": """set -euo pipefail
echo "$REGISTRY_PASSWORD" | oras login "$repository" --username "$REGISTRY_USERNAME" --password-stdin""",
        },
        {
            "name": "Push Module",
            "working-directory": "${{ runner.temp }}/terraform-modules",
            "run": '''set -euo pipefail
oras push --artifact-type application/vnd.opentofu.modulepkg \\
    "$oci_artifact" "$module_archive:archive/zip"''',
        },
        {
            "name": "Verify OpenTofu OCI Artifact",
            "run": """set -euo pipefail
oras manifest fetch "$oci_artifact" | jq -e '
  .mediaType == "application/vnd.oci.image.manifest.v1+json"
  and .artifactType == "application/vnd.opentofu.modulepkg"
  and (.layers | length) == 1
  and .layers[0].mediaType == "archive/zip"
' """,
        },
    ]
    # Commands refer to paths from the checkout root, even for matrix packages.
    for step in steps:
        if "run" in step:
            step.setdefault("working-directory", "")
    return steps


terraform_build = make_build(
    "terraform",
    make_terraform_build,
    on={**default_on, "push": {"branches": ["main"], "tags": ["*"]}},
)
