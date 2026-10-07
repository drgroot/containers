# Actions templater

For repositories with `artifact-tenant`, actions maker generates one `build.yml`
with independent UI, ETL, pip typings, and Node.js typings jobs. Pip and npm use
the same `typings-<version>` release tag and publish only their own distribution.
Main-branch pushes and pull requests build without publishing. Each typings job
runs on changes under `typings/**`, `build.yml`, or `.github/actions.json`,
typings tags, and manual runs. UI/ETL builds also run after configuration or
workflow changes, so architecture changes take effect on the next pipeline run.

The pip typings job reuses the standard pip generator: dependency installation,
version setup, build, distribution checks, Vault credentials, and publication.
Only its folder, release prefix, and workflow guards are scoped to the tenant.
It reads `typings/pyproject.toml` for non-release builds and needs no JavaScript
package or compiler script. Both package generators support `version_file` to
read a committed Python project version instead of the Docker `latest` label.

The Node.js job reuses the standard npm generator, including setup, registry
login, dependency installation, version setup, build, packing, and publication.
Its extra settings install the Python compiler dependencies, run the compiler
and parity tests, delay registry credentials until after the public dependency
build, and publish a tarball from `typings/js/` instead of a `dist` package root.
These are reusable npm generator options rather than a separate tenant pipeline.

The tenant repository supplies its Python requirements and the JavaScript build
package under `typings/js/`. The JavaScript package provides `build`, `check:python`,
and `test` npm scripts, a package lockfile, and `js/scripts/set_version.py` relative
to `typings/`. The Node.js version setup uses that script to synchronize its Python
and npm manifests before compilation. The library compiles local Python sources
without fetching a typings adapter or a published tenant wheel. Python/Node setup
and Vault action settings follow the normal actions-maker configuration.

Enable ARM64 alongside x86/AMD64 for the tenant UI and ETL independently in the
repository's `.github/actions.json`:

```json
{
  "armui": true,
  "armetl": true
}
```

The repository topics `armui-true` and `armetl-true` enable the corresponding
build. `armui-false` and `armetl-false` disable it. Enabled jobs set up QEMU before
Buildx and build `linux/amd64,linux/arm64`. The JSON settings override topics;
only boolean `true` enables ARM, so a string such as `"true"` does not enable it.

For other Docker repositories, the existing `"arm_enable": true` setting or
`arm-true` topic still enables AMD64 and ARM64. Tenant components inherit this
global setting when their own flag is absent. An explicit `armui` or `armetl`
value overrides the global setting for that component. When no ARM flag is set,
the existing single-platform build remains.

Run the generator tests from `actions-templater`:

```sh
python -m unittest discover -s tests -p 'test_*.py'
```
