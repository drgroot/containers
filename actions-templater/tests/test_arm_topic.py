"""Scenarios:
- Normal: arm-true enables the AMD64 and ARM64 Docker build.
- Normal: arm-false disables the ARM Docker build.
- Edge: invalid ARM topic values do not enable the ARM Docker build.
"""

import unittest

from src.com.repo import RepoContext
from src.com.repo.topics import parse_topic
from src.lib.actions.build.docker import docker_build_steps


class ArmTopicTests(unittest.TestCase):
    def setUp(self):
        self.repo = RepoContext(
            source="github",
            repo_full_name="example/app",
            repo_name="app",
            clone_url="https://example.com/app.git",
        )

    def test_arm_true_enables_both_platforms(self):
        """arm-true parses to a boolean that enables both Docker platforms."""
        key, value = parse_topic("arm-true")
        steps = docker_build_steps(self.repo, {key: value})

        self.assertIs(value, True)
        self.assertEqual("linux/amd64,linux/arm64", steps[-1]["with"]["platforms"])

    def test_arm_false_keeps_single_platform(self):
        """arm-false parses to false and omits the platforms setting."""
        key, value = parse_topic("arm-false")
        steps = docker_build_steps(self.repo, {key: value})

        self.assertIs(value, False)
        self.assertNotIn("platforms", steps[-1]["with"])

    def test_invalid_arm_value_is_ignored(self):
        """An invalid ARM topic has no effect on Docker build settings."""
        self.assertIsNone(parse_topic("arm-maybe"))
