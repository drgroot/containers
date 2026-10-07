"""Scenarios:
- sc1 (normal): Tenant pip is the standard pip flight with workflow scoping.
- sc2 (normal/edge): Project versions and release tags determine both package versions.
- sc3 (normal): Standard pip version setup writes valid quoted TOML for a prerelease.
- sc4 (normal): Ordinary npm keeps its default install/auth/publish flow.
- sc5 (edge): A compiler-only pip install skips dev dependencies without affecting defaults.
"""
import os
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

from src.com.repo import RepoContext
from src.lib.actions.artifact_tenant import artifact_tenant_build
from src.lib.actions.build.npm import npm_build
from src.lib.actions.build.pip import pip_build
from src.lib.actions.steps.bash.version import get_version_step
from src.lib.actions.steps.python import pip_install


def repo():
    return RepoContext(source="github", repo_full_name="serv-c/tenant-mmm", repo_name="tenant-mmm", repo_owner="serv-c", clone_url="https://example.com/tenant-mmm.git", artifact="tenant")


class SharedPackageBuildTest(unittest.TestCase):
    def test_pip_flight_is_shared(self):
        """Scenario: sc1.
        Relevant input: Tenant and standard pip generators with the same release settings.
        Relevant output: Commands, actions, inputs, environment, and step IDs.
        Expected outcome: Every stage is identical apart from working directories/guards/filter.
        """
        settings = {"artifact": "pip", "mono": False, "tag_prefix": "typings-", "version_file": "pyproject.toml"}
        standard = pip_build["function"](repo(), settings)["jobs"]["build-pip"]
        scoped = artifact_tenant_build["function"](repo(), {})["jobs"]["build-typings-pip"]
        def flight(job):
            return [{key: value for key, value in step.items() if key not in {"if", "working-directory"}} for step in job["steps"] if step.get("name") != "Filter Changes"]
        self.assertEqual(flight(standard), flight(scoped))
        self.assertFalse(any("set_version.py" in step.get("run", "") for step in scoped["steps"]))
        self.assertFalse(any("npm" in str(step.get("uses", "")) for step in scoped["steps"]))
        python_index = next(i for i, s in enumerate(scoped["steps"]) if s.get("uses", "").startswith("actions/setup-python@"))
        version_index = next(i for i, s in enumerate(scoped["steps"]) if s.get("id") == "get_version")
        self.assertLess(python_index, version_index)

    def test_shared_version_resolution(self):
        """Scenario: sc2.
        Relevant input: Main/PR refs and stable/prerelease tags plus a Python project version.
        Relevant output: current_version and npm dist-tag written by the shared version step.
        Expected outcome: Pip/npm resolve the same version; non-release builds avoid 'latest'.
        """
        for ref, expected in [("refs/heads/main", "0.3.4"), ("refs/pull/1/merge", "0.3.4"), ("refs/tags/typings-1.2.3", "1.2.3"), ("refs/tags/typings-1.2.3-rc.1", "1.2.3-rc.1")]:
            for artifact in ("pip", "npm"):
                with self.subTest(ref=ref, artifact=artifact), tempfile.TemporaryDirectory() as directory:
                    path = Path(directory)
                    (path / "pyproject.toml").write_text('[project]\nversion = "0.3.4"\n')
                    step = get_version_step(repo(), {"version_file": "pyproject.toml", "artifact": artifact, "tag_prefix": "typings-"})
                    env = {**os.environ, **step["env"], "REF_LONG": ref, "GITHUB_ENV": str(path / "env")}
                    subprocess.run(["bash", "-e", "-c", step["run"]], cwd=path, env=env, check=True, capture_output=True, text=True)
                    values = dict(line.split("=", 1) for line in (path / "env").read_text().splitlines())
                    self.assertEqual(expected, values["current_version"])
                    if artifact == "npm": self.assertEqual("next" if "-" in expected else "latest", values["npm_dist_tag"])

    def test_pip_version_setup(self):
        """Scenario: sc3.
        Relevant input: The standard Setup Version command and a prerelease TAG.
        Relevant output: pyproject.toml parsed after running the shell command.
        Expected outcome: The exact release version is written as valid TOML.
        """
        steps = pip_build["function"](repo(), {})["jobs"]["build-pip"]["steps"]
        step = next(s for s in steps if s.get("name") == "Setup Version")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pyproject.toml"
            path.write_text('[project]\nversion = "0.3.4"\n')
            subprocess.run(["bash", "-e", "-c", step["run"]], cwd=directory, env={**os.environ, "TAG": "1.2.3-rc.1"}, check=True, capture_output=True, text=True)
            self.assertEqual("1.2.3-rc.1", tomllib.loads(path.read_text())["project"]["version"])

    def test_npm_defaults_are_preserved(self):
        """Scenario: sc4.
        Relevant input: An ordinary single-package npm repository.
        Relevant output: Standard auth, install, build, and publish stages.
        Expected outcome: Private dependency auth precedes install; defaults publish from dist.
        """
        steps = npm_build["function"](repo(), {})["jobs"]["build-npm"]["steps"]
        names = [s.get("name") for s in steps]
        self.assertLess(names.index("Login to NPM"), names.index("Install dependencies"))
        self.assertEqual("npm install", next(s for s in steps if s.get("name") == "Install dependencies")["run"])
        self.assertEqual("npm run-script build", next(s for s in steps if s.get("name") == "Build Package")["run"])
        publish = next(s for s in steps if s.get("name") == "Publish Package")
        self.assertEqual("dist", publish["working-directory"])
        self.assertEqual("npm publish --registry=https://npm.yusufali.ca", publish["run"])
        self.assertNotIn("Pack Package", names)

    def test_compiler_install_skips_dev_dependencies(self):
        """Scenario: sc5.
        Relevant input: Default and compiler-only pip installation modifiers.
        Relevant output: Generated requirement installation commands.
        Expected outcome: Only compiler-only mode omits requirements-dev.txt.
        """
        self.assertIn("requirements-dev.txt", pip_install(repo(), {})["run"])
        compiler = pip_install(repo(), {"install_dev_dependencies": False})["run"]
        self.assertNotIn("requirements-dev.txt", compiler)
        self.assertIn("requirements.txt", compiler)
        self.assertIn("pip-options.txt", compiler)


if __name__ == "__main__":
    unittest.main()
