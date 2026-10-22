"""Scenarios:
- Normal: workspace libraries install with manifest/lockfile reconciliation, build
  from the root, and publish their own tagged dist.
- Normal: applications join tests, while shared files and siblings trigger checks.
- Edge: explicit module/command overrides and non-npm directory discovery survive.
- Edge: private packages and unrelated directories do not become release jobs.
"""

import json
from pathlib import Path
import tempfile
import unittest

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

    def test_build_root_and_release_guard(self):
        """Normal input: workspace with mismatched folder/name; expect root commands,
        npm install for manifest/lockfile reconciliation, release helper after build,
        and publication limited to the matching tag.
        Observed workflow fields are compared directly with those expectations.
        """
        job = npm_build["function"](self.repo, {"mono": True})["jobs"]["build-npm"]
        self.assertEqual(job["strategy"]["matrix"]["package"], ["servc-api", "servc-chart"])
        steps = {step.get("name"): step for step in job["steps"]}
        self.assertEqual(steps["Login to NPM"]["working-directory"], ".")
        self.assertEqual(steps["Install dependencies"]["run"], "npm install")
        self.assertEqual(steps["Build Package"]["run"],
                         "npm run check:dependencies\nnpm run build -- ${{ matrix.package }}")
        release = steps["Locate built package and set release version"]
        self.assertEqual(release["run"], "node common-ci/release.mjs")
        self.assertEqual(release["env"]["PROJECT"], "${{ matrix.package }}")
        self.assertGreater(job["steps"].index(release), job["steps"].index(steps["Build Package"]))
        for name in ("Install dependencies", "Build Package", "Locate built package and set release version"):
            self.assertNotIn("working-directory", steps[name])
        publish = steps["Publish Package"]
        self.assertEqual(publish["working-directory"], "${{ env.package_dir }}")
        self.assertTrue(publish["if"].startswith("github.ref_type == 'tag'"))
        self.assertIn("&& startsWith(github.ref,format('refs/tags/{0}-', matrix.package))", publish["if"])
        self.assertNotIn("Setup Version", steps)
        self.assertNotIn("Settle Depends", steps)
        setup = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/setup-node@"))
        self.assertEqual(setup["with"]["node-version"], "24")

    def test_tests_include_application_and_shared_changes(self):
        """Normal input: Angular application and two siblings. Expect all three test
        projects and root/shared/sibling filters; compare emitted matrix and paths.
        """
        job = npm_test["function"](self.repo, {"mono": True})["jobs"]["unittest"]
        self.assertEqual(job["strategy"]["matrix"]["package"], ["servc-api", "servc-chart", "ui"])
        steps = {step.get("name"): step for step in job["steps"]}
        self.assertEqual(steps["Login to NPM"]["working-directory"], ".")
        self.assertEqual(steps["Install dependencies"]["run"], "npm install")
        self.assertEqual(steps["Run Tests"]["run"], "npm run check:dependencies\nnpm test ${{ matrix.package }}")
        self.assertNotIn("working-directory", steps["Run Tests"])
        filters = steps["Filter Changes"]["with"]["filters"]
        for path in ("common-ci/**", "package-lock.json", "package.json", "servc-api/**", "servc-chart/**", "demo/**"):
            self.assertIn(path, filters)

    def test_overrides(self):
        """Edge input: explicit modules, Node version and custom commands. Expect
        these settings preserved; compare generated job and step values.
        """
        job = npm_build["function"](self.repo, {"mono": True, "monorepo-modules": ["servc-api"],
            "node_version": "22", "npm_install_command": "npm ci --ignore-scripts",
            "npm_build_command": "npm run custom-build"})["jobs"]["build-npm"]
        self.assertEqual(job["strategy"]["matrix"]["package"], ["servc-api"])
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
