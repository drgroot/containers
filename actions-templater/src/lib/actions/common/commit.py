from src.com.actions.workflow import WORKFLOW_GENERATOR
from src.lib.actions.steps.actions.common import checkout
from src.lib.actions.steps.actions.setup import nodejs

commtlint: WORKFLOW_GENERATOR = {
    "context_matchers": None,
    "negative_matchers": {
        "commitlint": ["false"],
    },
    "filename": ".github/workflows/commit.yml",
    "static": [],
    "function": lambda ctx, m: {
        "name": "COMMIT LINT",
        "run-name": "COMMIT LINT",
        "on": {"pull_request": {}},
        "jobs": {
            "commitlint": {
                "runs-on": ["ubuntu-latest"],
                "name": "commitlint",
                "steps": [
                    checkout(ctx, {**m, "fetch": True}),
                    nodejs(ctx, m),
                    {
                        "name": "Install commitlint",
                        "run": """\
if [ -f package.json ]; then
    rm package*.json
fi
npm install -g --registry https://npm.yusufali.ca @commitlint/cli @commitlint/config-conventional
if [ ! -f "commitlint.config.js" ]; then
    echo "module.exports = {extends: ['@commitlint/config-conventional']}" > commitlint.config.js
fi
                        """,
                    },
                    {
                        "name": "Lint Commit Message",
                        "if": "github.event_name == 'push'",
                        "run": "commitlint --from=HEAD~1 --verbose",
                    },
                    {
                        "name": "Lint Pull Request",
                        "if": "github.event_name == 'pull_request'",
                        "run": "commitlint --from ${{ github.event.pull_request.base.sha }} --to ${{ github.event.pull_request.head.sha }} --verbose",
                    },
                ],
            }
        },
    },
}
