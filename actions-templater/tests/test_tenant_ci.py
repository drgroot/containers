"""Scenarios:
- sc1 (normal): armui-true and armetl-true parse into independent boolean flags.
- sc2 (edge): false disables a component and malformed topics are ignored.
- sc3 (normal/edge): each component's ARM flag affects only its own Docker build.
- sc4 (edge): JSON flags override topics and the legacy global ARM default.
- sc5 (normal): pip and Node.js share a version source but use independent credentials.
- sc6 (normal): generated workflow files retain the new jobs and scoped ARM settings.
"""
import copy
import json
import os
import tempfile
import unittest

import yaml

from src.com.repo import RepoContext
from src.com.repo.topics import parse_topic
from src.com.run import get_config
from src.lib.actions.artifact_tenant import artifact_tenant_build
from src.writeyaml import write_workflow_file


def tenant(**extra):
    return RepoContext(
        source="github", repo_full_name="serv-c/tenant-mmm", repo_name="tenant-mmm",
        repo_owner="serv-c", clone_url="https://example.com/tenant-mmm.git", artifact="tenant", **extra,
    )


def named(job, name):
    return next(step for step in job["steps"] if step.get("name") == name)


class TenantCiTest(unittest.TestCase):
    def test_component_topics(self):
        """Scenario: sc1.
        Relevant input: armui-true and armetl-true topics.
        Relevant output: parsed modifier pairs.
        Expected outcome: JSON-compatible armui/armetl names with actual boolean True.
        """
        for component in ("ui", "etl"):
            self.assertEqual(parse_topic(f"arm{component}-true"), (f"arm{component}", True))

    def test_false_and_malformed_topics(self):
        """Scenario: sc2.
        Relevant input: false, uppercase, and unrecognized ARM flag values.
        Relevant output: parsed modifier or None.
        Expected outcome: false is a boolean; malformed values never enable ARM.
        """
        for component in ("ui", "etl"):
            self.assertEqual(parse_topic(f"arm{component}-false"), (f"arm{component}", False))
            for value in ("yes", "True", "", "true-extra"):
                self.assertIsNone(parse_topic(f"arm{component}-{value}"))

    def test_independent_architectures(self):
        """Scenario: sc3.
        Relevant input: UI-only, ETL-only, both, absent, and non-boolean flags.
        Relevant output: platforms and QEMU steps in each Docker job.
        Expected outcome: ARM appears only for components explicitly enabled.
        """
        for flags, expected in [({}, set()), ({"armui": True}, {"ui"}), ({"armetl": True}, {"etl"}), ({"armui": True, "armetl": True}, {"ui", "etl"}), ({"armui": "true", "armetl": False}, set())]:
            with self.subTest(flags=flags):
                original = copy.deepcopy(flags)
                workflow = artifact_tenant_build["function"](tenant(), flags)
                self.assertEqual(flags, original)
                for component in ("ui", "etl"):
                    job = workflow["jobs"][f"build-{component}"]
                    inputs = named(job, "Build and Push")["with"]
                    filters = named(job, "Filter Changes")["with"]["filters"]
                    self.assertIn(".github/actions.json", filters)
                    self.assertIn(".github/workflows/build.yml", filters)
                    self.assertIn("github.event_name == 'workflow_dispatch'", named(job, "Build and Push")["if"])
                    actions = [step.get("uses") for step in job["steps"]]
                    if component in expected:
                        self.assertEqual(inputs["platforms"], "linux/amd64,linux/arm64")
                        self.assertLess(actions.index("docker/setup-qemu-action@v3"), actions.index("docker/setup-buildx-action@v3"))
                    else:
                        self.assertNotIn("platforms", inputs)
                        self.assertNotIn("docker/setup-qemu-action@v3", actions)

    def test_json_precedence(self):
        """Scenario: sc4.
        Relevant input: ARM topics plus explicit JSON armui=false/armetl=true.
        Relevant output: generated UI and ETL platforms.
        Expected outcome: JSON overrides topic flags and explicit false overrides global ARM.
        """
        topics = dict(parse_topic(topic) for topic in ("arm-true", "armui-true", "armetl-false"))
        with tempfile.TemporaryDirectory() as directory:
            os.makedirs(os.path.join(directory, ".github"))
            with open(os.path.join(directory, ".github/actions.json"), "w") as file:
                json.dump({"armui": False, "armetl": True}, file)
            repo = RepoContext.model_validate({**tenant(**topics).model_dump(), **get_config(directory)})
            workflow = artifact_tenant_build["function"](repo, repo.model_dump())
        self.assertNotIn("platforms", named(workflow["jobs"]["build-ui"], "Build and Push")["with"])
        self.assertEqual("linux/amd64,linux/arm64", named(workflow["jobs"]["build-etl"], "Build and Push")["with"]["platforms"])
        global_only = artifact_tenant_build["function"](tenant(), {"arm_enable": True})
        for component in ("ui", "etl"):
            self.assertEqual("linux/amd64,linux/arm64", named(global_only["jobs"][f"build-{component}"], "Build and Push")["with"]["platforms"])

    def test_distribution_job_contracts(self):
        """Scenario: sc5.
        Relevant input: configured Python/Node versions and a tenant repo.
        Relevant output: independent pip/npm setup, build, version, and publish steps.
        Expected outcome: local compilation, same version script, scoped credentials, tag-only publish.
        """
        jobs = artifact_tenant_build["function"](tenant(), {"python_version": "3.12", "node_version": "22"})["jobs"]
        pip = jobs["build-typings-pip"]
        node = jobs["build-typings-nodejs"]
        self.assertNotIn("needs", pip)
        self.assertNotIn("needs", node)
        for job in (pip, node):
            self.assertIn("startsWith(github.ref_name, 'typings-')", job["if"])
            version = next(step for step in job["steps"] if step.get("id") == "get_version")
            expected_path = "pyproject.toml" if job is pip else "../pyproject.toml"
            self.assertEqual(expected_path, version["env"]["VERSION_FILE"])
            self.assertIn("tomllib", version["run"])
            self.assertEqual("typings" if job is pip else "typings/js", version["working-directory"])
            setup = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/setup-python@"))
            self.assertEqual("3.12", setup["with"]["python-version"])
            secrets = next(step for step in job["steps"] if step.get("id") in {"pip_secrets", "npm_secrets"})
            self.assertIn("github.ref_type == 'tag'", secrets["if"])
            filters = named(job, "Filter Changes")["with"]["filters"]
            self.assertIn("typings/**", filters)
            self.assertIn(".github/workflows/build.yml", filters)
            self.assertIn(".github/actions.json", filters)
            for step in job["steps"][2:]:
                if step.get("name") != "Filter Changes":
                    self.assertIn("github.event_name == 'workflow_dispatch'", step["if"])
        self.assertFalse(any(step.get("uses", "").startswith("actions/setup-node@") for step in pip["steps"]))
        pip_secrets = next(step for step in pip["steps"] if step.get("id") in {"pip_secrets", "npm_secrets"})["with"]["secrets"]
        node_secrets = next(step for step in node["steps"] if step.get("id") in {"pip_secrets", "npm_secrets"})["with"]["secrets"]
        self.assertIn("/iac/pip ", pip_secrets)
        self.assertNotIn("/iac/npm ", pip_secrets)
        self.assertIn("/iac/npm ", node_secrets)
        self.assertNotIn("/iac/pip ", node_secrets)
        setup = next(step for step in node["steps"] if step.get("uses", "").startswith("actions/setup-node@"))
        self.assertEqual("22", setup["with"]["node-version"])
        self.assertEqual("typings/js/package-lock.json", setup["with"]["cache-dependency-path"])
        build = named(node, "Build Package")
        self.assertEqual("typings/js", build["working-directory"])
        self.assertIn("npm run build", build["run"])
        self.assertIn("npm test", build["run"])
        self.assertNotIn("typings-adapter", build["run"])
        publish = named(node, "Publish Package")
        self.assertIn('npm publish "$NPM_TARBALL"', publish["run"])
        self.assertIn("npm.yusufali.ca", publish["run"])
        self.assertEqual("typings", named(node, "Install pip dependencies")["working-directory"])
        self.assertNotIn("requirements-dev.txt", named(node, "Install pip dependencies")["run"])
        self.assertEqual("typings", named(node, "Setup Version")["working-directory"])
        self.assertIn("set_version.py", named(node, "Setup Version")["run"])
        stage_names = [step.get("name") for step in node["steps"]]
        self.assertLess(stage_names.index("Build Package"), stage_names.index("Login to NPM"))
        self.assertLess(stage_names.index("Pack Package"), stage_names.index("Login to NPM"))
        self.assertIn("github.ref_type == 'tag'", named(node, "Login to NPM")["if"])

    def test_generated_file(self):
        """Scenario: sc6.
        Relevant input: tenant context with armui=true and armetl=false.
        Relevant output: build.yml written through actions maker's normal writer.
        Expected outcome: four jobs, UI-only ARM, and no workflow drift on a second write.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = tenant(local_folder=directory, armui=True, armetl=False)
            self.assertGreater(write_workflow_file(repo, artifact_tenant_build, directory), 0)
            with open(os.path.join(directory, ".github/workflows/build.yml")) as file:
                generated = yaml.safe_load(file)
            self.assertEqual(set(generated["jobs"]), {"build-ui", "build-etl", "build-typings-pip", "build-typings-nodejs"})
            self.assertIn("platforms", named(generated["jobs"]["build-ui"], "Build and Push")["with"])
            self.assertNotIn("platforms", named(generated["jobs"]["build-etl"], "Build and Push")["with"])
            self.assertEqual(write_workflow_file(repo, artifact_tenant_build, directory), 0)


if __name__ == "__main__":
    unittest.main()
