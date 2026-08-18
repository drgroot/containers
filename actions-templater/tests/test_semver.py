import unittest

from src.com.repo import RepoContext
from src.lib.actions.common.semver import changelog


class ChangelogWorkflowTests(unittest.TestCase):
    def test_servc_changelog_uses_vault_gitea_token(self):
        repo = RepoContext(
            source="github",
            repo_full_name="serv-c/service",
            repo_name="service",
            repo_owner="serv-c",
            clone_url="https://example.com/service.git",
        )

        workflow = changelog["function"](repo, {})
        steps = workflow["jobs"]["changelog"]["steps"]

        self.assertEqual("gitea_secrets", steps[0]["id"])
        self.assertEqual("hashicorp/vault-action@v2", steps[0]["uses"])
        self.assertEqual(
            "servc/data/iac/gitea token | PAT_TOKEN ;",
            steps[0]["with"]["secrets"],
        )
        self.assertEqual(
            "${{ steps.gitea_secrets.outputs.PAT_TOKEN }}",
            steps[1]["with"]["token"],
        )

        changelog_step = next(step for step in steps if step.get("id") == "changelog")
        self.assertEqual(
            "${{ steps.gitea_secrets.outputs.PAT_TOKEN }}",
            changelog_step["with"]["github-token"],
        )

    def test_non_servc_changelog_uses_github_token(self):
        repo = RepoContext(
            source="github",
            repo_full_name="example/service",
            repo_name="service",
            repo_owner="example",
            clone_url="https://example.com/service.git",
        )

        workflow = changelog["function"](repo, {})
        steps = workflow["jobs"]["changelog"]["steps"]

        self.assertNotEqual("gitea_secrets", steps[0].get("id"))
        self.assertNotIn("token", steps[0]["with"])

        changelog_step = next(step for step in steps if step.get("id") == "changelog")
        self.assertEqual("${{ github.token }}", changelog_step["with"]["github-token"])
