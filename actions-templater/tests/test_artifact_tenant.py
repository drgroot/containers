"""Scenarios:
- sc1 (normal): Tenant context selects the composite workflows.
- sc2 (normal): UI, ETL, pip, and Node.js builds have independent scoped jobs.
- sc3 (normal): Standard pip index files are written without replacing Dockerfiles.
- sc4 (normal): Component unit-test jobs apply configuration only where requested.
- sc5 (edge): Hyphenated repository names become underscored typings modules.
- sc6 (normal): Changelog releases share the UI, ETL, and typings tag prefixes.
"""
import os
import tempfile
import unittest

from src.com.repo import RepoContext
from src.get_workflows import get_workflows
from src.lib.actions.artifact_tenant import (
    artifact_tenant_build,
    artifact_tenant_changelog,
    artifact_tenant_unit,
)
from src.writeyaml import write_workflow_file


def make_repo(local_folder: str = "", **extra) -> RepoContext:
    return RepoContext(
        source="github",
        repo_full_name="serv-c/acme",
        repo_name="acme",
        repo_owner="serv-c",
        clone_url="https://example.com/acme.git",
        local_folder=local_folder,
        artifact="tenant",
        **extra,
    )


def named_step(job, name: str):
    return next(step for step in job["steps"] if step.get("name") == name)


class ArtifactTenantSelectionTests(unittest.TestCase):
    def test_artifact_tenant_topic_selects_composite_workflows(self):
        """Scenario: sc1. Relevant input: artifact=tenant context. Relevant output: selected workflow inventory. Expected outcome: tenant build/unit/changelog replace generic workflows."""
        workflows, _ = get_workflows(make_repo(language="python"))
        selected = {item["filename"]: item for item in workflows}

        self.assertIs(artifact_tenant_build, selected[".github/workflows/build.yml"])
        self.assertIs(artifact_tenant_unit, selected[".github/workflows/unit.yml"])
        self.assertIs(
            artifact_tenant_changelog,
            selected[".github/workflows/changelog.yml"],
        )
        self.assertNotIn(".github/workflows/python-pip-options.yml", selected)


class ArtifactTenantBuildTests(unittest.TestCase):
    def test_build_has_four_path_scoped_jobs(self):
        """Scenario: sc2. Relevant input: tenant context. Relevant output: four build jobs, paths, versions, and publish guards. Expected outcome: distributions share typings tags and build in their respective directories."""
        workflow = artifact_tenant_build["function"](make_repo(), {})

        self.assertEqual(
            {"build-ui", "build-etl", "build-typings-pip", "build-typings-nodejs"},
            set(workflow["jobs"]),
        )
        ui = workflow["jobs"]["build-ui"]
        etl = workflow["jobs"]["build-etl"]
        typings = workflow["jobs"]["build-typings-pip"]
        self.assertNotIn("strategy", ui)
        self.assertNotIn("strategy", etl)
        self.assertNotIn("strategy", typings)

        ui_filter = named_step(ui, "Filter Changes")
        self.assertIn("ui/**", ui_filter["with"]["filters"])
        ui_version = named_step(ui, "Get Version")
        self.assertEqual("ui-", ui_version["env"]["PREFIX"])
        self.assertEqual("ui", ui_version["working-directory"])
        self.assertIn("refs/tags/ui-", ui_version["if"])
        ui_artifact = named_step(ui, "Set Docker Artifact")
        self.assertEqual("acme-ui", ui_artifact["env"]["PACKAGE_NAME"])
        ui_docker = named_step(ui, "Build and Push")
        self.assertEqual("ui", ui_docker["with"]["context"])
        self.assertEqual("ui/Dockerfile", ui_docker["with"]["file"])
        self.assertIn("NPMPASS=", ui_docker["with"]["build-args"])

        etl_filter = named_step(etl, "Filter Changes")
        self.assertIn("etl/**", etl_filter["with"]["filters"])
        etl_version = named_step(etl, "Get Version")
        self.assertEqual("etl-", etl_version["env"]["PREFIX"])
        etl_artifact = named_step(etl, "Set Docker Artifact")
        self.assertEqual("acme-etl", etl_artifact["env"]["PACKAGE_NAME"])

        typings_filter = named_step(typings, "Filter Changes")
        self.assertIn("typings/**", typings_filter["with"]["filters"])
        typings_version = named_step(typings, "Set Python Release Version")
        self.assertIn('js/scripts/set_version.py "$REF_LONG"', typings_version["run"])
        self.assertEqual("typings", typings_version["working-directory"])
        self.assertEqual(
            "typings",
            named_step(typings, "Build and Check Python Distribution")["working-directory"],
        )
        typings_publish = named_step(typings, "Publish Python Package")
        self.assertIn("startsWith(github.ref_name, 'typings-')", typings_publish["if"])
        self.assertIn("github.event_name == 'push'", typings_publish["if"])
        self.assertIn("github.event_name == 'workflow_dispatch'", typings_publish["if"])
        nodejs = workflow["jobs"]["build-typings-nodejs"]
        self.assertEqual("typings/js", named_step(nodejs, "Compile All Python Modules to JavaScript and Declarations")["working-directory"])
        self.assertNotIn("strategy", nodejs)

    def test_static_standard_files_are_written_without_dockerfiles(self):
        """Scenario: sc3. Relevant input: empty tenant checkout. Relevant output: generated static files. Expected outcome: pip index files appear without Dockerfile replacement."""
        repo = make_repo()
        with tempfile.TemporaryDirectory() as repo_dir:
            write_workflow_file(repo, artifact_tenant_build, repo_dir)

            self.assertFalse(os.path.exists(os.path.join(repo_dir, "ui/Dockerfile")))
            self.assertTrue(
                os.path.isfile(os.path.join(repo_dir, "etl/pip-options.txt"))
            )
            self.assertTrue(
                os.path.isfile(os.path.join(repo_dir, "typings/pip-options.txt"))
            )


class ArtifactTenantUnitTests(unittest.TestCase):
    def test_unit_jobs_apply_actions_config_only_as_requested(self):
        """Scenario: sc4. Relevant input: custom runtime versions and ETL settings. Relevant output: unit jobs. Expected outcome: configuration stays scoped to its intended component."""
        custom_step = {"name": "Configured Step", "run": "echo configured"}
        workflow = artifact_tenant_unit["function"](
            make_repo(),
            {
                "python_version": "3.12",
                "node_version": "18",
                "runs-on": ["self-hosted", "etl"],
                "ci_steps": [custom_step],
                "workflow_env": {"TENANT_ENV": "etl-only"},
            },
        )

        self.assertEqual({"unit-ui", "unit-etl", "unit-typings"}, set(workflow["jobs"]))
        ui = workflow["jobs"]["unit-ui"]
        etl = workflow["jobs"]["unit-etl"]
        typings = workflow["jobs"]["unit-typings"]

        self.assertEqual(["ubuntu-latest"], ui["runs-on"])
        ui_node = next(
            step
            for step in ui["steps"]
            if step.get("uses", "").startswith("actions/setup-node@")
        )
        self.assertNotEqual("18", ui_node["with"]["node-version"])
        self.assertEqual("ui", named_step(ui, "Run Tests")["working-directory"])
        self.assertNotIn("Configured Step", [step.get("name") for step in ui["steps"]])

        self.assertEqual(["self-hosted", "etl"], etl["runs-on"])
        self.assertEqual({"TENANT_ENV": "etl-only"}, etl["env"])
        self.assertIn("Configured Step", [step.get("name") for step in etl["steps"]])
        self.assertEqual(
            "etl",
            named_step(etl, "Verify Docker Python Version")["working-directory"],
        )

        self.assertEqual(["ubuntu-latest"], typings["runs-on"])
        typings_python = next(
            step
            for step in typings["steps"]
            if step.get("uses", "").startswith("actions/setup-python@")
        )
        self.assertEqual("3.12", typings_python["with"]["python-version"])
        self.assertNotIn(
            "Verify Docker Python Version",
            [step.get("name") for step in typings["steps"]],
        )
        self.assertIn("-m mypy acme ", named_step(typings, "Type Check")["run"])
        self.assertNotIn(
            "Run Tests",
            [step.get("name") for step in typings["steps"]],
        )

        for component, job in [("ui", ui), ("etl", etl), ("typings", typings)]:
            filters = named_step(job, "Filter Changes")["with"]["filters"]
            self.assertIn(f"{component}/**", filters)
            self.assertIn(".github/workflows/unit.yml", filters)

    def test_typings_typecheck_uses_underscored_repo_name(self):
        """Scenario: sc5. Relevant input: tenant-mmm name. Relevant output: mypy target. Expected outcome: Python module name is tenant_mmm."""
        repo = RepoContext(
            source="github",
            repo_full_name="serv-c/tenant-mmm",
            repo_name="tenant-mmm",
            repo_owner="serv-c",
            clone_url="https://example.com/tenant-mmm.git",
            local_folder="",
            artifact="tenant",
        )
        workflow = artifact_tenant_unit["function"](repo, {})
        typings = workflow["jobs"]["unit-typings"]
        self.assertIn("-m mypy tenant_mmm ", named_step(typings, "Type Check")["run"])


class ArtifactTenantChangelogTests(unittest.TestCase):
    def test_changelog_reuses_monorepo_flow_for_three_components(self):
        """Scenario: sc6. Relevant input: UI, ETL, and typings directories. Relevant output: changelog matrix. Expected outcome: each component uses its matching release tag."""
        with tempfile.TemporaryDirectory() as repo_dir:
            for component in ["ui", "etl", "typings", "not-a-component"]:
                os.makedirs(os.path.join(repo_dir, component))
            workflow = artifact_tenant_changelog["function"](make_repo(repo_dir), {})

        job = workflow["jobs"]["changelog"]
        self.assertEqual(["ui", "etl", "typings"], job["strategy"]["matrix"]["package"])
        changelog_step = next(
            step for step in job["steps"] if step.get("id") == "changelog"
        )
        self.assertEqual("${{ matrix.package }}-", changelog_step["with"]["tag-prefix"])
        self.assertEqual("${{ matrix.package }}", changelog_step["with"]["git-path"])
