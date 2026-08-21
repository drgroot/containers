from typing import List

from src.com.actions.workflow import WORKFLOW_GENERATOR
from src.lib.actions.build.docker import docker, node_docker, python_docker
from src.lib.actions.build.npm import npm_build
from src.lib.actions.build.pip import pip_build
from src.lib.actions.common.agent import (
    agent_embed_issue,
    agent_embed_issue_servc,
    agent_embed_markdown,
    agent_embed_markdown_servc,
    issue_agent,
    issue_agent_servc,
)
from src.lib.actions.common.commit import commtlint
from src.lib.actions.common.semver import changelog
from src.lib.actions.python_static import python_pip_options_static
from src.lib.actions.test.npm import npm_test
from src.lib.actions.test.python import python_test

GITHUB_ACTIONS_INVENTORY: List[WORKFLOW_GENERATOR] = [
    commtlint,
    issue_agent,
    issue_agent_servc,
    python_docker,
    pip_build,
    npm_build,
    python_pip_options_static,
    docker,
    node_docker,
    npm_test,
    python_test,
    changelog,
    agent_embed_issue,
    agent_embed_issue_servc,
    agent_embed_markdown,
    agent_embed_markdown_servc,
]
