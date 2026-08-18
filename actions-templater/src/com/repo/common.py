# here is a list of common context checkers
from src.com.repo import MODIFIERS, RepoContext


def is_monorepo(ctx: RepoContext, m: MODIFIERS) -> bool:
    return m.get("mono", False)


def is_docker(ctx: RepoContext, m: MODIFIERS) -> bool:
    return m.get("artifact", "") == "docker"


def is_python(ctx: RepoContext, m: MODIFIERS) -> bool:
    return m.get("language", "") == "python"


def is_spark(ctx: RepoContext, m: MODIFIERS) -> bool:
    return m.get("compute", "") == "spark"


def is_servc(ctx: RepoContext, m: MODIFIERS) -> bool:
    return ctx.repo_owner.lower() == "serv-c"
