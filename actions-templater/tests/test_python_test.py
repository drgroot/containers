import os
import subprocess
import tempfile
import unittest

from src.com.repo import RepoContext
from src.lib.actions.steps.bash.version import get_docker_base_image_version_step
from src.lib.actions.test.python import python_test, python_test_steps


class PythonDockerTestWorkflowTests(unittest.TestCase):
    def test_test_workflow_defaults_to_ubuntu_latest(self):
        repo = RepoContext(
            source="github",
            repo_full_name="example/python-api",
            repo_name="python-api",
            clone_url="https://example.com/python-api.git",
        )

        workflow = python_test["function"](repo, {})

        self.assertEqual(["ubuntu-latest"], workflow["jobs"]["unittest"]["runs-on"])

    def test_test_workflow_uses_configured_runs_on(self):
        repo = RepoContext(
            source="github",
            repo_full_name="example/python-api",
            repo_name="python-api",
            clone_url="https://example.com/python-api.git",
        )

        workflow = python_test["function"](
            repo,
            {
                "runs-on": [
                    "self-hosted",
                    "linux",
                    "x64",
                ]
            },
        )

        self.assertEqual(
            ["self-hosted", "linux", "x64"],
            workflow["jobs"]["unittest"]["runs-on"],
        )

    def test_test_workflow_accepts_string_runs_on(self):
        repo = RepoContext(
            source="github",
            repo_full_name="example/python-api",
            repo_name="python-api",
            clone_url="https://example.com/python-api.git",
        )

        workflow = python_test["function"](repo, {"runs-on": "ubuntu-24.04"})

        self.assertEqual(["ubuntu-24.04"], workflow["jobs"]["unittest"]["runs-on"])

    def test_docker_artifact_adds_python_base_image_version_check(self):
        repo = RepoContext(
            source="github",
            repo_full_name="example/python-api",
            repo_name="python-api",
            clone_url="https://example.com/python-api.git",
        )

        steps = python_test_steps(
            repo,
            {
                "artifact": "docker",
                "python_version": "3.13.2",
                "dockerfile": "containers/api/Dockerfile",
            },
        )

        check_step = steps[1]
        self.assertEqual("Verify Docker Python Version", check_step["name"])
        self.assertEqual(
            {
                "DOCKERFILE": "containers/api/Dockerfile",
                "DOCKER_BASE_IMAGE": "python",
                "EXPECTED_VERSION": "3.13.2",
                "VERSION_LABEL": "Python",
            },
            check_step["env"],
        )
        self.assertIn("minor_version", check_step["run"])
        self.assertIn("expected_minor\" != \"$base_minor", check_step["run"])

    def test_non_docker_python_artifact_skips_base_image_version_check(self):
        repo = RepoContext(
            source="github",
            repo_full_name="example/python-package",
            repo_name="python-package",
            clone_url="https://example.com/python-package.git",
        )

        steps = python_test_steps(repo, {"artifact": "pip", "python_version": "3.13"})

        step_names = [step.get("name") for step in steps]
        self.assertNotIn("Verify Docker Python Version", step_names)

    def test_python_checks_use_an_isolated_virtual_environment(self):
        repo = RepoContext(
            source="github",
            repo_full_name="example/python-api",
            repo_name="python-api",
            clone_url="https://example.com/python-api.git",
        )

        steps = python_test_steps(repo, {})
        install_step = next(
            step for step in steps if step.get("name") == "Install pip dependencies"
        )
        type_check_step = next(
            step for step in steps if step.get("name") == "Type Check"
        )
        test_step = next(step for step in steps if step.get("name") == "Run Tests")

        self.assertIn("python -m venv .venv", install_step["run"])
        self.assertIn(
            ".venv/bin/python -m pip install -r requirements.txt",
            install_step["run"],
        )
        self.assertIn(
            ".venv/bin/python -m pip install -r requirements-dev.txt",
            install_step["run"],
        )
        self.assertNotIn("|| true", install_step["run"])
        self.assertTrue(type_check_step["run"].startswith(".venv/bin/python -m mypy"))
        self.assertIn(".venv/bin/python -m coverage run", test_step["run"])
        self.assertIn(".venv/bin/python -m coverage report", test_step["run"])

    def test_docker_base_image_version_check_supports_other_images(self):
        repo = RepoContext(
            source="github",
            repo_full_name="example/javascript-app",
            repo_name="javascript-app",
            clone_url="https://example.com/javascript-app.git",
        )

        step = get_docker_base_image_version_step(
            repo,
            {"dockerfile": "Dockerfile"},
            base_image="node",
            expected_version="22.16.0",
            version_label="JavaScript",
        )

        self.assertEqual("Verify Docker JavaScript Version", step["name"])
        self.assertEqual(
            {
                "DOCKERFILE": "Dockerfile",
                "DOCKER_BASE_IMAGE": "node",
                "EXPECTED_VERSION": "22.16.0",
                "VERSION_LABEL": "JavaScript",
            },
            step["env"],
        )
        self.assertIn('base="$DOCKER_BASE_IMAGE"', step["run"])

    def test_docker_base_image_version_check_skips_missing_base_image(self):
        repo = RepoContext(
            source="github",
            repo_full_name="example/python-api",
            repo_name="python-api",
            clone_url="https://example.com/python-api.git",
        )
        step = get_docker_base_image_version_step(
            repo,
            {"dockerfile": "Dockerfile"},
            base_image="python",
            expected_version="3.13.2",
            version_label="Python",
        )

        with tempfile.TemporaryDirectory() as repo_dir:
            with open(os.path.join(repo_dir, "Dockerfile"), "w") as f:
                f.write(
                    "FROM registry.yusufali.ca/serv-c/servc-coder-templates AS app\n"
                    "RUN eval \"$(pyenv init -)\" && pyenv global 3.12\n"
                )

            result = subprocess.run(
                ["bash", "-c", step["run"]],
                cwd=repo_dir,
                env={**os.environ, **step["env"]},
                capture_output=True,
                text=True,
            )

        self.assertEqual("", result.stderr)
        self.assertIn(
            "No Python Docker base image version found in Dockerfile; skipping check",
            result.stdout,
        )
        self.assertEqual(0, result.returncode)

    def test_monorepo_docker_version_check_runs_inside_matrix_package(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            os.makedirs(os.path.join(repo_dir, "api"))
            repo = RepoContext(
                source="github",
                repo_full_name="example/python-api",
                repo_name="python-api",
                clone_url="https://example.com/python-api.git",
                local_folder=repo_dir,
            )

            workflow = python_test["function"](
                repo,
                {"mono": True, "artifact": "docker", "python_version": "3.13.2"},
            )

        steps = workflow["jobs"]["unittest"]["steps"]
        check_step = next(
            step for step in steps if step.get("name") == "Verify Docker Python Version"
        )
        self.assertEqual("Dockerfile", check_step["env"]["DOCKERFILE"])
        self.assertEqual("${{ matrix.package }}", check_step["working-directory"])
