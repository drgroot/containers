"""Scenarios:
- sc1 (normal/edge): Docker build arguments support secrets, empty input, and Vault values.
- sc2 (normal/edge): Valid schedules preserve triggers; invalid schedules are ignored.
- sc3 (normal): Serv-C TypeScript builds receive npm read credentials.
- sc4 (normal): All Docker repositories use the current Vault registry/mirror output names.
"""
import unittest

from src.com.repo import RepoContext
from src.lib.actions.build import merge_schedule
from src.lib.actions.build.docker import docker, docker_build_steps, format_secret_build_args


class FormatSecretBuildArgsTests(unittest.TestCase):
    def test_none_when_secrets_missing(self):
        """Scenario: sc1. Relevant input: absent or empty secrets. Relevant output: formatted args. Expected outcome: None."""
        self.assertIsNone(format_secret_build_args({}, None))
        self.assertIsNone(format_secret_build_args({}, ""))

    def test_formats_dot_separated_string(self):
        """Scenario: sc1. Relevant input: two dot-separated secret names. Relevant output: Docker build args. Expected outcome: both values reference GitHub secrets."""
        self.assertEqual(
            [
                "my_secret=${{ secrets.my_secret }}",
                "api_key=${{ secrets.api_key }}",
            ],
            format_secret_build_args({}, "my_secret.api_key"),
        )

    def test_ignores_empty_segments(self):
        """Scenario: sc1. Relevant input: secret names separated by empty segments. Relevant output: args. Expected outcome: empty names are omitted."""
        self.assertEqual(
            [
                "token=${{ secrets.token }}",
                "id=${{ secrets.id }}",
            ],
            format_secret_build_args({}, "token..id"),
        )

    def test_accepts_iterable_inputs(self):
        """Scenario: sc1. Relevant input: iterable secret names. Relevant output: args. Expected outcome: names and case are preserved."""
        self.assertEqual(
            [
                "first=${{ secrets.first }}",
                "Second=${{ secrets.Second }}",
            ],
            format_secret_build_args({}, ["first", "Second"]),
        )

    def test_adds_vault_build_secrets_from_modifiers(self):
        """Scenario: sc1. Relevant input: GitHub secret plus configured Vault secret. Relevant output: args. Expected outcome: each references its corresponding credential source."""
        self.assertEqual(
            [
                "token=${{ secrets.token }}",
                "API_KEY=${{ steps.build_secrets.outputs.API_KEY }}",
            ],
            format_secret_build_args(
                {
                    "build_secrets": [
                        {
                            "path": "servc/data/app",
                            "key": "api_key",
                            "value": "API_KEY",
                        },
                    ],
                },
                ["token"],
            ),
        )


class BuildWorkflowScheduleTests(unittest.TestCase):
    def test_merge_schedule_keeps_existing_triggers(self):
        """Scenario: sc2. Relevant input: push/PR triggers and cron. Relevant output: merged triggers. Expected outcome: all original triggers remain."""
        workflow_on = {
            "pull_request": {},
            "push": {"branches": ["main"], "tags": ["*"]},
            "workflow_dispatch": {},
        }

        self.assertEqual(
            {
                "pull_request": {},
                "push": {"branches": ["main"], "tags": ["*"]},
                "workflow_dispatch": {},
                "schedule": [{"cron": "30 1 */15 * *"}],
            },
            merge_schedule(workflow_on, [{"cron": "30 1 */15 * *"}]),
        )

    def test_merge_schedule_ignores_invalid_values(self):
        """Scenario: sc2. Relevant input: malformed schedules. Relevant output: workflow triggers. Expected outcome: no schedule is added."""
        workflow_on = {"pull_request": {}}

        self.assertEqual(workflow_on, merge_schedule(workflow_on, None))
        self.assertEqual(workflow_on, merge_schedule(workflow_on, {}))
        self.assertEqual(
            workflow_on,
            merge_schedule(workflow_on, [{"foo": "bar"}, {"cron": ""}, "bad"]),
        )

    def test_docker_workflow_uses_schedule_from_modifiers(self):
        """Scenario: sc2. Relevant input: valid cron modifier. Relevant output: generated Docker workflow. Expected outcome: schedule is present."""
        repo = RepoContext(
            source="github",
            repo_full_name="example/docker-images",
            repo_name="docker-images",
            clone_url="https://example.com/docker-images.git",
        )

        workflow = docker["function"](repo, {"schedule": [{"cron": "30 1 */15 * *"}]})

        self.assertIsNotNone(workflow)
        self.assertEqual(
            [{"cron": "30 1 */15 * *"}],
            workflow["on"]["schedule"],
        )


class DockerBuildStepsTests(unittest.TestCase):
    def test_servc_typescript_docker_build_adds_npm_build_args(self):
        """Scenario: sc3. Relevant input: Serv-C TypeScript Docker repo. Relevant output: npm build args. Expected outcome: Vault read credentials reach the build."""
        repo = RepoContext(
            source="github",
            repo_full_name="serv-c/tenant-ui",
            repo_name="tenant-ui",
            repo_owner="serv-c",
            clone_url="https://example.com/tenant-ui.git",
        )

        steps = docker_build_steps(repo, {"artifact": "docker", "language": "typescript"})

        self.assertEqual(
            "NPMPASS=${{ steps.build_secrets.outputs.NPMPASS }}\n"
            "NPMUSER=${{ steps.build_secrets.outputs.NPMUSER }}",
            steps[-1]["with"]["build-args"],
        )

    def test_non_servc_repo_uses_vault_docker_secrets(self):
        """Scenario: sc4. Relevant input: non-Serv-C Docker repo. Relevant output: Vault registry/mirror outputs and artifact name. Expected outcome: current output names are used and the registry username supplies the artifact prefix."""
        repo = RepoContext(
            source="github",
            repo_full_name="example/docker-images",
            repo_name="docker-images",
            repo_owner="example",
            clone_url="https://example.com/docker-images.git",
        )

        steps = docker_build_steps(repo, {})

        self.assertEqual("docker_secrets", steps[0]["id"])
        self.assertEqual("hashicorp/vault-action@v2", steps[0]["uses"])
        self.assertEqual("userpass", steps[0]["with"]["method"])
        self.assertEqual("${{ secrets.VAULT_USERNAME }}", steps[0]["with"]["username"])
        self.assertEqual("${{ secrets.VAULT_PASSWORD }}", steps[0]["with"]["password"])
        self.assertEqual(
            "\n".join(
                [
                    "servc/data/iac/docker host | DOCKER_REGISTRY_HOST ;",
                    "servc/data/iac/docker username | DOCKER_USERNAME ;",
                    "servc/data/iac/docker password | DOCKER_PASSWORD ;",
                    "servc/data/iac/docker host-mirror | DOCKER_MIRROR_HOST ;",
                    "servc/data/iac/docker mirror-username | DOCKER_MIRROR_USERNAME ;",
                    "servc/data/iac/docker mirror-password | DOCKER_MIRROR_PASSWORD ;",
                ]
            ),
            steps[0]["with"]["secrets"],
        )
        self.assertEqual("Set Docker Artifact", steps[1]["name"])
        self.assertEqual("${{ steps.docker_secrets.outputs.DOCKER_REGISTRY_HOST }}", steps[1]["env"]["DOCKER_REGISTRY_HOST"])
        self.assertEqual("docker-images", steps[1]["env"]["PACKAGE_NAME"])
        self.assertEqual("Login to Mirror", steps[2]["name"])
        self.assertEqual("${{ steps.docker_secrets.outputs.DOCKER_MIRROR_HOST }}", steps[2]["with"]["registry"])
        self.assertEqual("${{ steps.docker_secrets.outputs.DOCKER_MIRROR_USERNAME }}", steps[2]["with"]["username"])
        self.assertEqual("${{ steps.docker_secrets.outputs.DOCKER_MIRROR_PASSWORD }}", steps[2]["with"]["password"])

    def test_servc_repo_uses_vault_docker_secrets(self):
        """Scenario: sc4. Relevant input: Serv-C Docker repo. Relevant output: Vault credentials and login inputs. Expected outcome: current registry/mirror output names are used."""
        repo = RepoContext(
            source="github",
            repo_full_name="serv-c/docker-images",
            repo_name="docker-images",
            repo_owner="serv-c",
            clone_url="https://example.com/docker-images.git",
        )

        steps = docker_build_steps(repo, {})

        self.assertEqual("docker_secrets", steps[0]["id"])
        self.assertEqual("hashicorp/vault-action@v2", steps[0]["uses"])
        self.assertEqual("userpass", steps[0]["with"]["method"])
        self.assertEqual("${{ secrets.VAULT_USERNAME }}", steps[0]["with"]["username"])
        self.assertEqual("${{ secrets.VAULT_PASSWORD }}", steps[0]["with"]["password"])
        self.assertEqual(
            "\n".join(
                [
                    "servc/data/iac/docker host | DOCKER_REGISTRY_HOST ;",
                    "servc/data/iac/docker username | DOCKER_USERNAME ;",
                    "servc/data/iac/docker password | DOCKER_PASSWORD ;",
                    "servc/data/iac/docker host-mirror | DOCKER_MIRROR_HOST ;",
                    "servc/data/iac/docker mirror-username | DOCKER_MIRROR_USERNAME ;",
                    "servc/data/iac/docker mirror-password | DOCKER_MIRROR_PASSWORD ;",
                ]
            ),
            steps[0]["with"]["secrets"],
        )
        self.assertEqual("Set Docker Artifact", steps[1]["name"])
        self.assertEqual("Login to Mirror", steps[2]["name"])
        self.assertEqual(
            "${{ steps.docker_secrets.outputs.DOCKER_MIRROR_HOST }}",
            steps[2]["with"]["registry"],
        )
        self.assertEqual(
            "${{ steps.docker_secrets.outputs.DOCKER_MIRROR_USERNAME }}",
            steps[2]["with"]["username"],
        )
        self.assertEqual(
            "${{ steps.docker_secrets.outputs.DOCKER_MIRROR_PASSWORD }}",
            steps[2]["with"]["password"],
        )
        self.assertEqual(
            "${{ steps.docker_secrets.outputs.DOCKER_USERNAME }}",
            steps[3]["with"]["username"],
        )
        self.assertEqual(
            "${{ steps.docker_secrets.outputs.DOCKER_PASSWORD }}",
            steps[3]["with"]["password"],
        )
