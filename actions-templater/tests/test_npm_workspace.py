"""Scenarios:
- Normal: workspace libraries install with manifest/lockfile reconciliation, build
  in their own folders, and publish their own tagged dist.
- Normal: standalone applications join tests; package/shared files trigger checks.
- Edge: broken root/sibling dependencies cannot affect a package-only install.
- Normal: release versioning modifies only the built package manifest.
- Edge: explicit module/command overrides and non-npm directory discovery survive.
- Edge: private packages and unrelated directories do not become release jobs.
"""

import json
from pathlib import Path
import tempfile
import unittest
import shutil
import shlex
import subprocess

from src.com.repo import RepoContext
from src.lib.actions.build.npm import npm_build
from src.lib.actions.test.npm import npm_test
from src.lib.actions.steps.mono_repo import get_monorepo_modules


class NpmWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = RepoContext(source="github", repo_full_name="serv-c/ui",
                                repo_name="ui", repo_owner="serv-c",
                                clone_url="https://example.com/ui.git", local_folder=str(self.root))
        self.write("package.json", {"private": True, "workspaces": ["servc-*", "demo"]})
        self.write("servc-api/package.json", {"name": "@servc/api"})
        self.write("servc-chart/package.json", {"name": "@servc/different-name"})
        self.write("demo/package.json", {"private": True})
        for folder in ("common-ci", "node_modules", "dist"):
            (self.root / folder).mkdir()
        self.write("angular.json", {"projects": {"ui": {
            "projectType": "application", "root": "demo", "architect": {"test": {}}}}})

    def write(self, filename, value):
        path = self.root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    def test_package_directory_and_release_guard(self):
        """Normal input: workspace with mismatched folder/name; expect package-local commands,
        npm install for manifest/lockfile reconciliation, built-manifest versioning after build,
        and publication limited to the matching tag.
        Observed workflow fields are compared directly with those expectations.
        """
        job = npm_build["function"](self.repo, {"mono": True})["jobs"]["build-npm"]
        self.assertEqual(job["strategy"]["matrix"]["package"], ["servc-api", "servc-chart"])
        self.assertFalse(job["strategy"]["fail-fast"])
        steps = {step.get("name"): step for step in job["steps"]}
        self.assertEqual(steps["Login to NPM"]["working-directory"], "${{ matrix.package }}")
        self.assertEqual(steps["Install dependencies"]["run"], "npm install --prefix . --workspaces=false --include=dev")
        self.assertEqual(steps["Build Package"]["run"],
                         "npm --prefix . --workspaces=false run build")
        release = steps["Set built package release version"]
        self.assertEqual(release["run"], 'npm --prefix dist --workspaces=false version "$TAG" --no-git-tag-version --allow-same-version')
        self.assertIn("github.ref_type == 'tag'", release["if"])
        self.assertIn("&& startsWith(github.ref,format('refs/tags/{0}-', matrix.package))", release["if"])
        self.assertGreater(job["steps"].index(release), job["steps"].index(steps["Build Package"]))
        for name in ("Install dependencies", "Build Package", "Set built package release version"):
            self.assertEqual(steps[name]["working-directory"], "${{ matrix.package }}")
        publish = steps["Publish Package"]
        self.assertEqual(publish["working-directory"], "${{ matrix.package }}/dist")
        self.assertTrue(publish["if"].startswith("github.ref_type == 'tag'"))
        self.assertIn("&& startsWith(github.ref,format('refs/tags/{0}-', matrix.package))", publish["if"])
        self.assertNotIn("Setup Version", steps)
        self.assertNotIn("Settle Depends", steps)
        setup = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/setup-node@"))
        self.assertEqual(setup["with"]["node-version"], "24")

    def test_tests_include_application_and_shared_changes(self):
        """Normal input: Angular application and two siblings. Expect all three test
        directories and package/shared filters; compare emitted matrix and paths.
        """
        job = npm_test["function"](self.repo, {"mono": True})["jobs"]["unittest"]
        self.assertEqual(job["strategy"]["matrix"]["package"], ["servc-api", "servc-chart", "demo"])
        self.assertFalse(job["strategy"]["fail-fast"])
        steps = {step.get("name"): step for step in job["steps"]}
        self.assertEqual(steps["Login to NPM"]["working-directory"], "${{ matrix.package }}")
        self.assertEqual(steps["Install dependencies"]["run"], "npm install --prefix . --workspaces=false --include=dev")
        self.assertEqual(steps["Run Tests"]["run"], "npm --prefix . --workspaces=false test")
        self.assertEqual(steps["Run Tests"]["working-directory"], "${{ matrix.package }}")
        filters = steps["Filter Changes"]["with"]["filters"]
        for path in ("common-ci/**", "${{ matrix.package }}/**", ".github/workflows/**"):
            self.assertIn(path, filters)

    def test_overrides(self):
        """Edge input: explicit modules, Node version and custom commands. Expect
        these settings preserved; compare generated job and step values.
        """
        job = npm_build["function"](self.repo, {"mono": True, "monorepo-modules": ["servc-api"],
            "node_version": "22", "npm_install_command": "npm ci --ignore-scripts",
            "npm_build_command": "npm run custom-build"})["jobs"]["build-npm"]
        self.assertEqual(job["strategy"]["matrix"]["package"], ["servc-api"])
        self.assertFalse(job["strategy"]["fail-fast"])
        steps = {step.get("name"): step for step in job["steps"]}
        self.assertEqual(steps["Install dependencies"]["run"], "npm ci --ignore-scripts")
        self.assertEqual(steps["Build Package"]["run"], "npm run custom-build")
        setup = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/setup-node@"))
        self.assertEqual(setup["with"]["node-version"], "22")

    def test_workspace_discovery_and_fallback(self):
        """Edge input: object-form workspaces, private app and unrelated folders.
        Expect only libraries; without a manifest, expect original folder discovery.
        Compare discovered lists to the expected directory names.
        """
        self.write("package.json", {"workspaces": {"packages": ["servc-*", "demo"]}})
        self.assertEqual(get_monorepo_modules(self.repo, {}), ["servc-api", "servc-chart"])
        (self.root / "package.json").unlink()
        self.assertEqual(get_monorepo_modules(self.repo, {}),
                         ["common-ci", "demo", "dist", "node_modules", "servc-api", "servc-chart"])


    @unittest.skipUnless(shutil.which("npm"), "npm is required for the installation isolation regression")
    def test_install_ignores_broken_root_and_sibling(self):
        """Edge input: an impossible root dependency and a sibling's impossible peer.
        Output: install exit status, package-local lockfile and manifest contents.
        Expected versus observed: the generated install succeeds offline, writes
        only the selected package lockfile, and leaves sibling/root manifests alone.
        """
        self.write("package.json", {"private": True, "workspaces": ["servc-*"],
            "dependencies": {"unrelated-root-dependency-do-not-install": "999.0.0"}})
        self.write("servc-chart/package.json", {"name": "@servc/chart", "version": "0.1.0",
            "peerDependencies": {"unrelated-sibling-peer-do-not-install": "999.0.0"}})
        self.write("servc-api/package.json", {"name": "@servc/api", "version": "1.2.1"})
        job = npm_build["function"](self.repo, {"mono": True})["jobs"]["build-npm"]
        command = next(s for s in job["steps"] if s.get("name") == "Install dependencies")["run"]
        result = subprocess.run([*shlex.split(command), "--offline", "--ignore-scripts", "--no-audit", "--no-fund"],
            cwd=self.root / "servc-api", capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lock = json.loads((self.root / "servc-api/package-lock.json").read_text())
        self.assertEqual(set(lock["packages"]), {""})
        self.assertFalse((self.root / "package-lock.json").exists())
        self.assertFalse((self.root / "servc-chart/package-lock.json").exists())

    def test_nested_package_directory(self):
        """Edge input: libraries under packages/. Output: generated run directories.
        Expected versus observed: install/build/version/publish use packages/<matrix>.
        """
        job = npm_build["function"](self.repo, {"mono": True, "monorepo-folder": "packages",
            "monorepo-modules": ["api"]})["jobs"]["build-npm"]
        for step in job["steps"]:
            if step.get("name") in ("Login to NPM", "Install dependencies", "Build Package", "Set built package release version"):
                self.assertEqual(step["working-directory"], "packages/${{ matrix.package }}")
            if step.get("name") == "Publish Package":
                self.assertEqual(step["working-directory"], "packages/${{ matrix.package }}/dist")

    @unittest.skipUnless(shutil.which("npm"), "npm is required for the release version regression")
    def test_release_changes_only_built_manifest(self):
        """Normal input: source/built packages with different versions and a release tag.
        Output: source and built manifests after the generated version command.
        Expected versus observed: only dist gets the prerelease version; the source
        version and unrelated sibling metadata are unchanged.
        """
        import os
        self.write("servc-api/package.json", {"name": "@servc/api", "version": "1.2.1"})
        self.write("servc-api/dist/package.json", {"name": "@servc/api", "version": "1.2.1"})
        job = npm_build["function"](self.repo, {"mono": True})["jobs"]["build-npm"]
        step = next(s for s in job["steps"] if s.get("name") == "Set built package release version")
        result = subprocess.run(["bash", "-e", "-c", step["run"]], cwd=self.root / "servc-api",
            env={**os.environ, "TAG": "2.0.0-rc.1"}, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads((self.root / "servc-api/package.json").read_text())["version"], "1.2.1")
        self.assertEqual(json.loads((self.root / "servc-api/dist/package.json").read_text())["version"], "2.0.0-rc.1")
