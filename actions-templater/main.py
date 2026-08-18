#!/usr/bin/env python

from servc.server import start_server

from src.config import QUEUE_NAME
from src.domains.template import template_github_actions


def main():
    return start_server(
        resolver={
            "rollout": template_github_actions,
        },
        route=QUEUE_NAME,
    )


if __name__ == "__main__":
    main()
