import unittest

from src.com.repo import RepoContext
from src.lib.actions.build.npm import npm_build


class NpmBuildWorkflowTests(unittest.TestCase):
    def test_npm_login_uses_vault_secrets(self):
        repo = RepoContext(
            source="github",
            repo_full_name="serv-c/typescript-package",
            repo_name="typescript-package",
            repo_owner="serv-c",
            clone_url="https://example.com/typescript-package.git",
        )

        workflow = npm_build["function"](repo, {})
        steps = workflow["jobs"]["build-npm"]["steps"]

        vault_step = next(step for step in steps if step.get("id") == "npm_secrets")
        self.assertEqual("hashicorp/vault-action@v2", vault_step["uses"])
        self.assertEqual(
            "\n".join(
                [
                    "servc/data/iac/npm npm_write_pass | NPMPASS ;",
                    "servc/data/iac/npm npm_write_user | NPMUSER ;",
                ]
            ),
            vault_step["with"]["secrets"],
        )

        login_step = next(step for step in steps if step.get("name") == "Login to NPM")
        self.assertEqual(
            {
                "NPMPASS": "${{ steps.npm_secrets.outputs.NPMPASS }}",
                "NPMUSER": "${{ steps.npm_secrets.outputs.NPMUSER }}",
            },
            login_step["env"],
        )
