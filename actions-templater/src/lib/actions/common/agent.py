from typing import List, Tuple

from src.com.actions.step import STEP
from src.com.actions.workflow import WORKFLOW_GENERATOR, Workflow
from src.com.repo import MODIFIERS, RepoContext
from src.com.repo.common import is_servc
from src.lib.actions.steps.actions.common import checkout
from src.lib.actions.steps.actions.vault import (
    get_git_token_steps,
    process_vault_secrets,
)

AGENT_VAULT_STEP_ID = "agent_secrets"
AGENT_VAULT_PATH = "servc/data/iac/servc"
AGENT_TOKEN_OUTPUT = "AGENT_TOKEN"


def get_agent_token_steps(ctx: RepoContext, m: MODIFIERS) -> Tuple[str, List[STEP]]:
    if not is_servc(ctx, m):
        return "${{ secrets.AGENT_TOKEN }}", []

    agent_secrets, agent_vault = process_vault_secrets(
        AGENT_VAULT_STEP_ID,
        [
            {
                "path": AGENT_VAULT_PATH,
                "key": "agent-auth-token",
                "value": AGENT_TOKEN_OUTPUT,
            },
        ],
    )

    return agent_secrets[AGENT_TOKEN_OUTPUT], [agent_vault(ctx, m)]


def issue_agent_workflow(ctx: RepoContext, m: MODIFIERS) -> Workflow:
    agent_token, agent_token_steps = get_agent_token_steps(ctx, m)
    github_token, github_token_steps = get_git_token_steps(
        ctx, m, "${{ secrets.GITHUB_TOKEN }}"
    )

    return {
        "name": "Send Tasks to Agent",
        "on": {
            "issue_comment": {
                "types": [
                    "created",
                    "edited",
                ],
            },
        },
        "jobs": {
            "dispatch": {
                "if": "contains(github.event.comment.body, '@bot')",
                "runs-on": ["ubuntu-latest"],
                "permissions": {
                    "issues": "read",
                    "contents": "read",
                },
                "steps": [
                    *agent_token_steps,
                    *github_token_steps,
                    {
                        "name": "Send task to coding agent",
                        "uses": "https://git.yusufali.ca/actions/issue-codebot@main",
                        "with": {
                            "api_url": "${{ secrets.AGENT_API_URL }}",
                            "api_token": agent_token,
                            "bot_route": "agent-bot",
                            "debug": False,
                        },
                        "env": {
                            "GITHUB_TOKEN": github_token,
                        },
                    },
                ],
            }
        },
    }


def embed_markdown(ctx: RepoContext, m: MODIFIERS) -> Workflow:
    agent_token, agent_token_steps = get_agent_token_steps(ctx, m)

    return {
        "name": "Send Markdown to VectorDB",
        "on": {
            "workflow_dispatch": {},
            "push": {"branches": ["main"], "paths": ["**.md"]},
        },
        "jobs": {
            "agent-embed-markdown": {
                "runs-on": ["ubuntu-latest"],
                "steps": [
                    *agent_token_steps,
                    checkout(ctx, m),
                    {
                        "name": "Send to embeddings",
                        "uses": "https://git.yusufali.ca/actions/embed-markdown@main",
                        "with": {
                            "api_url": "${{ secrets.AGENT_API_URL }}",
                            "api_token": agent_token,
                        },
                    },
                ],
            }
        },
    }


def embed_issues(ctx: RepoContext, m: MODIFIERS) -> Workflow:
    agent_token, agent_token_steps = get_agent_token_steps(ctx, m)

    return {
        "name": "Send Issues to VectorDB",
        "on": {
            "issue_comment": {
                "types": [
                    "created",
                    "edited",
                ],
            },
        },
        "jobs": {
            "agent-embed-issue": {
                "if": "contains(github.event.comment.body, 'solution:')",
                "runs-on": ["ubuntu-latest"],
                "permissions": {
                    "issues": "read",
                    "contents": "read",
                },
                "steps": [
                    *agent_token_steps,
                    {
                        "name": "Send to embeddings",
                        "uses": "https://git.yusufali.ca/actions/embed-issues@main",
                        "with": {
                            "api_url": "${{ secrets.AGENT_API_URL }}",
                            "api_token": agent_token,
                        },
                        "env": {
                            "GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
                        },
                    },
                ],
            }
        },
    }


issue_agent: WORKFLOW_GENERATOR = {
    "context_matchers": {
        "agent": ["enabled"],
    },
    "negative_matchers": None,
    "filename": ".github/workflows/issue-agent.yml",
    "static": [],
    "function": issue_agent_workflow,
}


issue_agent_servc: WORKFLOW_GENERATOR = {
    "context_matchers": None,
    "context_checkers": [is_servc],
    "negative_matchers": None,
    "filename": ".github/workflows/issue-agent.yml",
    "static": [],
    "function": issue_agent_workflow,
}


agent_embed_issue: WORKFLOW_GENERATOR = {
    "context_matchers": {
        "agent": ["enabled"],
    },
    "negative_matchers": None,
    "filename": ".github/workflows/agent-issue.yml",
    "static": [],
    "function": embed_issues,
}


agent_embed_issue_servc: WORKFLOW_GENERATOR = {
    "context_matchers": None,
    "context_checkers": [is_servc],
    "negative_matchers": None,
    "filename": ".github/workflows/agent-issue.yml",
    "static": [],
    "function": embed_issues,
}


agent_embed_markdown: WORKFLOW_GENERATOR = {
    "context_matchers": {
        "agent": ["enabled"],
    },
    "negative_matchers": None,
    "filename": ".github/workflows/agent-markdown.yml",
    "static": [],
    "function": embed_markdown,
}


agent_embed_markdown_servc: WORKFLOW_GENERATOR = {
    "context_matchers": None,
    "context_checkers": [is_servc],
    "negative_matchers": None,
    "filename": ".github/workflows/agent-markdown.yml",
    "static": [],
    "function": embed_markdown,
}
