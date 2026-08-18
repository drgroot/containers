import unittest

from src.com.repo import RepoContext
from src.lib.actions.build.pip import pip_build


class PipBuildWorkflowTests(unittest.TestCase):
    def test_pip_publish_uses_vault_secrets(self):
        repo = RepoContext(
            source="github",
            repo_full_name="serv-c/python-package",
            repo_name="python-package",
            repo_owner="serv-c",
            clone_url="https://example.com/python-package.git",
        )

        workflow = pip_build["function"](repo, {})
        steps = workflow["jobs"]["build-pip"]["steps"]

        build_step = next(step for step in steps if step.get("name") == "Build Package")
        self.assertEqual(".venv/bin/python -m build", build_step["run"])

        vault_step = next(step for step in steps if step.get("id") == "pip_secrets")
        self.assertEqual("hashicorp/vault-action@v2", vault_step["uses"])
        self.assertEqual(
            "\n".join(
                [
                    "servc/data/iac/pip username | PYPI_USERNAME ;",
                    "servc/data/iac/pip token | PYPI_TOKEN ;",
                    "servc/data/iac/pip url | PYPI_URL ;",
                ]
            ),
            vault_step["with"]["secrets"],
        )

        publish_step = next(
            step for step in steps if step.get("name") == "Publish Package"
        )
        self.assertTrue(publish_step["run"].startswith(".venv/bin/python -m twine "))
        self.assertIn(
            "-u${{ steps.pip_secrets.outputs.PYPI_USERNAME }}",
            publish_step["run"],
        )
        self.assertIn(
            "-p${{ steps.pip_secrets.outputs.PYPI_TOKEN }}",
            publish_step["run"],
        )
        self.assertIn(
            "--repository-url ${{ steps.pip_secrets.outputs.PYPI_URL }}",
            publish_step["run"],
        )
