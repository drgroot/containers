import unittest

from src.com.repo import RepoContext
from src.lib.actions.steps.bash.version import get_version_step


class GetVersionStepTests(unittest.TestCase):
    def test_monorepo_uses_matrix_package_for_artifact_name(self):
        repo = RepoContext(
            source="github",
            repo_full_name="example-org/example",
            repo_name="example",
            repo_owner="example-org",
            clone_url="https://example.com/example.git",
        )

        step = get_version_step(repo, {"mono": True})

        self.assertEqual("example-org/${{ matrix.package }}", step["env"]["ARTIFACT_NAME"])

    def test_non_monorepo_keeps_default_artifact_name(self):
        repo = RepoContext(
            source="github",
            repo_full_name="example-org/example",
            repo_name="example",
            clone_url="https://example.com/example.git",
        )

        step = get_version_step(repo, {})

        self.assertEqual("example-org/example", step["env"]["ARTIFACT_NAME"])
