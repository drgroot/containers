import os
from typing import cast

from src.com.actions.step import STEP, STEP_GENERATOR
from src.com.repo import MODIFIERS, RepoContext
from src.com.repo.common import is_monorepo

"""
Determine the version of the commit
considerations:
    ref is a tag
    ref is a branch that is not main (no tag exists)
    ref is a sha/event (pull_request)
"""


def get_version_f(ctx: RepoContext, m: MODIFIERS) -> STEP:
    tag_prefix = m.get("tag_prefix", "")
    artifact_name = f"{m.get('artifactname', ctx.repo_full_name)}"
    if is_monorepo(ctx, m):
        artifact_name = os.path.join(ctx.repo_owner, "${{ matrix.package }}")

    step = {
        "name": "Get Version",
        "id": "get_version",
        "env": {
            "PREFIX": tag_prefix,
            "REF_LONG": "${{ github.ref }}",
            "REF_SHORT": "${{ github.ref_name }}",
            "PROD_REPOSITORY": str(m.get("prod_repository", m.get("repository", ""))),
            "NONPROD_REPOSITORY": str(
                m.get("nonprod_repository", m.get("repository", ""))
            ),
            "ARTIFACT_NAME": artifact_name,
        },
        "run": """\
REPO=$NONPROD_REPOSITORY
CURRENT_VERSION="0.0.1"
if [[ "$REF_LONG" == "refs/tags/${PREFIX}"[0-9.-]* ]]; then
    CURRENT_VERSION="${REF_LONG#refs/tags/${PREFIX}}"
    REPO=$PROD_REPOSITORY
elif [[ $REF_SHORT == "main" ]]; then
    git fetch --prune
    CURRENT_VERSION="latest"
    REPO=$PROD_REPOSITORY
fi

echo $CURRENT_VERSION
echo $REPO

echo artifactname=$ARTIFACT_NAME >> $GITHUB_ENV
echo repository=$REPO >> $GITHUB_ENV
echo current_version=$CURRENT_VERSION >> $GITHUB_ENV""",
    }

    return cast(STEP, step)


def get_docker_base_image_version_step(
    ctx: RepoContext,
    m: MODIFIERS,
    base_image: str,
    expected_version: object,
    version_label: str,
) -> STEP:
    step = {
        "name": f"Verify Docker {version_label} Version",
        "env": {
            "DOCKERFILE": str(m.get("dockerfile", "Dockerfile")),
            "DOCKER_BASE_IMAGE": base_image,
            "EXPECTED_VERSION": str(expected_version),
            "VERSION_LABEL": version_label,
        },
        "run": r"""\
set -euo pipefail

minor_version() {
  local version="$1"
  if [[ "$version" =~ ^([0-9]+)\.([0-9]+)(\.[0-9]+)?$ ]]; then
    printf '%s.%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    return 0
  fi

  return 1
}

base_image_version="$(
  awk -v base="$DOCKER_BASE_IMAGE" '
    function version_from_tag(tag, candidate, pattern) {
      candidate = tag
      sub(/-.*/, "", candidate)
      if (candidate ~ /^[0-9]+(\.[0-9]+){1,2}$/) {
        return candidate
      }

      pattern = "^" base "[-_]?([0-9]+(\\.[0-9]+){1,2})"
      if (match(tag, pattern)) {
        candidate = substr(tag, RSTART + length(base), RLENGTH - length(base))
        sub(/^[-_]/, "", candidate)
        return candidate
      }

      return ""
    }

    tolower($1) == "from" {
      for (i = 2; i <= NF; i++) {
        if ($i ~ /^--/) {
          continue
        }

        image = $i
        tag = ""
        prefix = base ":"
        marker = "/" base ":"

        if (index(image, prefix) == 1) {
          tag = substr(image, length(prefix) + 1)
        } else if (index(image, marker) > 0) {
          tag = substr(image, index(image, marker) + length(marker))
        }

        if (tag != "") {
          version = version_from_tag(tag)
          if (version != "") {
            print version
            exit
          }
        }

        break
      }
    }
  ' "$DOCKERFILE"
)"

if [[ -z "$base_image_version" ]]; then
  echo "No $VERSION_LABEL Docker base image version found in $DOCKERFILE; skipping check"
  exit 0
fi

if ! expected_minor="$(minor_version "$EXPECTED_VERSION")"; then
  echo "$VERSION_LABEL version must be X.Y or X.Y.Z, got: $EXPECTED_VERSION"
  exit 1
fi

if ! base_minor="$(minor_version "$base_image_version")"; then
  echo "Docker base $VERSION_LABEL version must be X.Y or X.Y.Z, got: $base_image_version"
  exit 1
fi

if [[ "$expected_minor" != "$base_minor" ]]; then
  echo "$VERSION_LABEL version $EXPECTED_VERSION does not match Docker base $VERSION_LABEL version $base_image_version"
  exit 1
fi
""",
    }

    return cast(STEP, step)


get_version_step: STEP_GENERATOR = get_version_f
