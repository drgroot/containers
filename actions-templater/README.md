Actions Templater generates GitHub Actions workflows and Dependabot configs from repository metadata. It picks the best-suited templates from the inventory in `src/lib/actions` based on the `RepoContext` passed to `template_github_actions` and writes them with `src/writeyaml.py`.

## Workflow Catalog
- `.github/workflows/commit.yml` (`src/lib/actions/common/commit.py`): enabled everywhere unless repo context includes `commitlint: "false"`; runs commitlint on pushes/PRs to enforce Conventional Commits.
- `.github/workflows/issue-agent.yml` (`src/lib/actions/common/agent.py`): requires repo context `agent: "enabled"`; on issue comments containing `@bot`, dispatches to the shared automation action (`https://git.yusufali.ca/automation/action@main`) with `AGENT_API_URL`, `AGENT_TOKEN`, `GITHUB_TOKEN`, and the `codebot` route.
- `.github/workflows/dependabot-auto-merge.yml` (`src/lib/actions/dependabot.py`): always available; on Dependabot, Renovate, or PRs titled with `PR_TITLE`, auto-merges via GH CLI.
- `.github/workflows/build-docker.yml` (`src/lib/actions/build/docker.py` via `make_build`): requires `artifact: "docker"`; logs in to the registry, sets up Docker Buildx, and builds/pushes with `docker/build-push-action@v5`, using repo/env metadata for image naming. Optional `secrets` (dot-separated string) becomes uppercased build args (`KEY=${{ secrets.KEY }}`) that are passed through the Docker build.
- `.github/workflows/build-docker.yml` (python flavor): requires `artifact: "docker"` and `language: "python"`; same as docker build with python-specific context tagging.
- `.github/workflows/build-docker.yml` (node flavor): requires `artifact: "docker"` and `language: "node"`; also drops `src/static/node/Dockerfile` into `Dockerfile` before building.
- `.github/workflows/build-docker.yml` (monorepo): requires `artifact: "docker"` and `type: "monorepo"`; matrixes over modules containing a `Dockerfile` and builds each image with `${{ matrix.module }}` appended to the artifact name.
- `.github/workflows/build-pip.yml` (`src/lib/actions/build/pip.py`): requires `language: "python"`; sets the package version from `env.current_version`, builds with `python -m build`, and publishes on `main`.
- `.github/workflows/changelog.yml` (`src/lib/actions/common/semver.py`): enabled unless `changelog: "false"`; manual `workflow_dispatch` that generates the next semver tag using `TriPSs/conventional-changelog-action`.

## Dependabot Templates (`src/lib/dependabot.py`)
- `npm`: applied when `language` is `node`, `javascript`, or `typescript`.
- `pip`: applied when `language` is `python`.
- `github-actions`: always added to keep actions up to date.
- `terraform`: applied when `language` is `hcl` or `terraform`.
- `maven`: applied when `build_type` or `build` is `maven`.

Each template writes to `.github/dependabot.yml` with the interval defaulting to `ACTION_DEFAULT_DEPENDABOT_INTERVAL` (env, defaults to `daily`) and the module directory from `module_directory` (defaults to `/`).

## Static Assets
- `src/static/node/Dockerfile` -> `Dockerfile` for Node Docker builds; additional static paths can be attached per workflow generator via its `static` field.
