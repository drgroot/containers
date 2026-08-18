import hashlib
import os
import shutil
from io import TextIOWrapper
from string import Template
from typing import Any, Callable, List, Tuple

import yaml

from src.com.actions.dependabot import GENERATE_DEPENDABOT
from src.com.actions.workflow import WORKFLOW_GENERATOR
from src.com.repo import RepoContext

CWD = os.path.dirname(os.path.realpath(__file__))
WRITE_METHOD = Callable[[Any, TextIOWrapper], None]


def repr_str(dumper, data):
    if "\n" in data:
        data = "\n".join([line.rstrip() for line in data.splitlines()])
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, repr_str)


def get_sha(filename: str) -> str:
    if filename.endswith(".tgz"):
        return os.path.basename(filename)

    BUF_SIZE = 8192

    md5 = hashlib.sha256()
    with open(filename, "rb") as f:
        while chunk := f.read(BUF_SIZE):
            md5.update(chunk)
        return str(md5.hexdigest())


YAML_WRITER: WRITE_METHOD = lambda n, f: yaml.dump(
    n, f, default_flow_style=False, width=float("inf")
)


def file_copy(repo: RepoContext, src: Any, dest: TextIOWrapper) -> None:
    if not isinstance(src, str):
        raise Exception("File copy only supports string paths")
    with open(src, "r") as f:
        dest.write(Template(f.read()).safe_substitute(**repo.model_dump()))


def write_yaml(
    newcontent: Any, filename: str, writer: WRITE_METHOD = YAML_WRITER
) -> int:
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    original_sha = ""
    if os.path.exists(filename):
        if not filename.endswith(".tgz"):
            with open(filename, "r") as f:
                content = f.read()
                if "#ignore" in content or "# ignore" in content:
                    print(f"Skipping {filename}")
                    return 0
        original_sha = get_sha(filename)

    if filename.endswith(".tgz"):
        if get_sha(newcontent) != original_sha:
            shutil.copyfile(newcontent, filename)
    else:
        with open(filename, "w+") as f:
            writer(newcontent, f)
    new_sha = get_sha(filename)
    return 1 if original_sha != new_sha else 0


def write_static_files(
    repodir: str, static_path: str | Tuple[str, str], repo: RepoContext
) -> int:
    if isinstance(static_path, str):
        return write_static_files(repodir, (static_path, static_path), repo)
    local_static_ref, target_static_ref = static_path

    static_root = os.path.join(CWD, "static")
    local_path = os.path.join(static_root, local_static_ref)
    if not os.path.exists(local_path):
        raise Exception(f"Static path {local_path} does not exist")
    files: List[str] = [local_path]
    if os.path.isdir(local_path):
        files = [
            os.path.join(dp, f)
            for dp, dn, filenames in os.walk(local_path)
            for f in filenames
            if os.path.isfile(os.path.join(dp, f))
        ]

    count = 0
    for file in files:
        filename = os.path.join(repodir, os.path.relpath(file, static_root)).replace(
            local_static_ref, target_static_ref
        )
        count += write_yaml(file, filename, lambda n, f: file_copy(repo, n, f))

    return count


def write_workflow_file(
    repo: RepoContext, workflow: WORKFLOW_GENERATOR, repo_dir: str
) -> int:
    modifiers = {} if not repo.model_extra else repo.model_extra
    modifiers = {**repo.model_dump(), **modifiers}
    yamlcontent = workflow["function"](repo, modifiers)
    outputfilename = os.path.join(repo_dir, workflow["filename"])

    static_files: int = 0
    for file in workflow["static"]:
        static_files += write_static_files(repo_dir, file, repo)

    if yamlcontent is not None:
        static_files += write_yaml(yamlcontent, outputfilename)

    return static_files


def write_dependabot(
    repo: RepoContext,
    dependabots: List[GENERATE_DEPENDABOT],
    repo_dir: str,
) -> int:
    modifiers = {} if not repo.model_extra else repo.model_extra
    filename = ".github/dependabot.yml"

    update_config = [
        dependabot["function"](repo, modifiers) for dependabot in dependabots
    ]
    yamlcontent = {
        "version": 2,
        "updates": [x for x in update_config if x is not None],
    }

    outputfilename = os.path.join(repo_dir, filename)
    return write_yaml(yamlcontent, outputfilename)
