"""Scenarios:
- Normal: arm_enable=true sets up QEMU and builds AMD64 and ARM64 images.
- Normal: arm_enable=false keeps the existing single-platform build.
- Edge: missing arm_enable keeps the existing single-platform build.
- Normal: actions.json arm_enable=true reaches the generated Docker workflow.
"""

import json
import os
import tempfile
import unittest

from src.com.repo import RepoContext
from src.com.run import get_config
from src.lib.actions.build.docker import docker, docker_build_steps


class DockerArmBuildTests(unittest.TestCase):
    def setUp(self):
        self.repo = RepoContext(
            source="github",
            repo_full_name="example/app",
            repo_name="app",
            clone_url="https://example.com/app.git",
        )

    def test_arm_enabled(self):
        """True adds QEMU before Buildx and both platforms to Build and Push."""
        steps = docker_build_steps(self.repo, {"arm_enable": True})
        uses = [step.get("uses") for step in steps]

        self.assertLess(
            uses.index("docker/setup-qemu-action@v3"),
            uses.index("docker/setup-buildx-action@v3"),
        )
        self.assertEqual(
            "linux/amd64,linux/arm64",
            steps[-1]["with"]["platforms"],
        )
        self.assertEqual("docker/build-push-action@v5", steps[-1]["uses"])

    def test_arm_disabled(self):
        """False omits QEMU and leaves Build and Push without platforms."""
        self.assert_single_platform_build({"arm_enable": False})

    def test_arm_missing(self):
        """A missing flag omits QEMU and leaves Build and Push without platforms."""
        self.assert_single_platform_build({})

    def test_actions_json_enables_arm_workflow(self):
        """A true JSON flag produces a workflow with both Docker platforms."""
        with tempfile.TemporaryDirectory() as repo_dir:
            os.makedirs(os.path.join(repo_dir, ".github"))
            with open(os.path.join(repo_dir, ".github", "actions.json"), "w") as config:
                json.dump({"arm_enable": True}, config)

            repo = RepoContext.model_validate(
                {**self.repo.model_dump(), **get_config(repo_dir)}
            )
            workflow = docker["function"](repo, repo.model_dump())

        steps = workflow["jobs"]["build-docker"]["steps"]
        self.assertEqual("linux/amd64,linux/arm64", steps[-1]["with"]["platforms"])

    def assert_single_platform_build(self, modifiers):
        steps = docker_build_steps(self.repo, modifiers)

        self.assertNotIn("docker/setup-qemu-action@v3", [step.get("uses") for step in steps])
        self.assertNotIn("platforms", steps[-1]["with"])
        self.assertEqual("docker/build-push-action@v5", steps[-1]["uses"])
