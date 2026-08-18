from src.com.actions.step import STEP
from src.com.actions.workflow import WORKFLOW_GENERATOR
from src.config import PR_TITLE
from src.lib.actions.steps.actions.common import checkout

setup_gh: STEP = {
    "name": "Setup GitHub CLI",
    "uses": "ksivamuthu/actions-setup-gh-cli@v3",
}

dependabot_auto_merge: WORKFLOW_GENERATOR = {
    "context_matchers": None,
    "negative_matchers": None,
    "static": [],
    "filename": ".github/workflows/dependabot-auto-merge.yml",
    "function": lambda ctx, m: {
        "name": "Dependabot Auto-Merge",
        "run-name": "Dependabot Auto-Merge",
        "on": {
            "pull_request": {},
        },
        "permissions": {
            "pull-requests": "write",
            "contents": "write",
        },
        "jobs": {
            "rennovatebot": {
                "runs-on": ["ubuntu-latest"],
                "name": "rennovatebot",
                "if": "github.event.pull_request.user.login == 'renovate_bot'",
                "steps": [
                    checkout(ctx, m),
                    setup_gh,
                    {
                        "name": "Enable auto-merge for Dependabot",
                        "run": 'gh pr merge --auto --merge "$PR_URL"',
                        "env": {
                            "PR_URL": "${{github.event.pull_request.html_url}}",
                            "GH_TOKEN": "${{secrets.GITHUB_TOKEN}}",
                        },
                    },
                ],
            },
            "dependabot": {
                "name": "dependabot",
                "runs-on": ["ubuntu-latest"],
                "if": "github.event.pull_request.user.login == 'dependabot[bot]'",
                "steps": [
                    {
                        "name": "Enable auto-merge for Dependabot",
                        "run": 'gh pr merge --auto --merge "$PR_URL"',
                        "env": {
                            "PR_URL": "${{github.event.pull_request.html_url}}",
                            "GH_TOKEN": "${{secrets.GITHUB_TOKEN}}",
                        },
                    },
                ],
            },
            "devopsbot": {
                "name": "devopsbot",
                "runs-on": ["ubuntu-latest"],
                "if": f"github.event.pull_request.title == '{PR_TITLE}'",
                "steps": [
                    checkout(ctx, m),
                    setup_gh,
                    {
                        "name": "Enable auto-merge for Dependabot",
                        "run": 'gh pr merge --auto --merge "$PR_URL"',
                        "env": {
                            "PR_URL": "${{github.event.pull_request.html_url}}",
                            "GH_TOKEN": "${{secrets.GITHUB_TOKEN}}",
                        },
                    },
                ],
            },
        },
    },
}
