from src.com.actions.step import STEP_GENERATOR
from src.com.repo import MODIFIERS, RepoContext

install_git: STEP_GENERATOR = lambda ctx, m: {
    "name": "Install Git",
    "run": "sudo apt-get update && sudo apt-get install -y git && git config advice.diverging false",
}


def get_latest_tag(id: str = "previoustag", name="Get Latest Tag") -> STEP_GENERATOR:
    def get_tag(ctx: RepoContext, m: MODIFIERS):
        tag_prefix = m.get("tag_prefix", "")
        list = f'"{tag_prefix}[0-9.-]*"' if tag_prefix else ""
        clean = (
            f"${{last_tag_wprefix#{tag_prefix}}}" if tag_prefix else "$last_tag_wprefix"
        )

        return {
            "id": id,
            "name": name,
            "run": f"""\
git fetch --tags
last_tag_wprefix=$(git tag --list {list} --sort=-v:refname | head -n 1)
last_tag={clean}
echo $last_tag_wprefix
echo $last_tag

echo last_tag=$last_tag >> $GITHUB_ENV
    """,
        }

    return get_tag
