from src.com.actions.step import STEP_GENERATOR

list: STEP_GENERATOR = lambda ctx, m: {
    "id": m.get("id", "list"),
    "run": f"""\
items=$(ls {m.get("ls_dir", "")} | jq -R '.' | jq -cs .)
echo $items
echo items=$items >> $GITHUB_OUTPUT
""",
}

find: STEP_GENERATOR = lambda ctx, m: {
    "id": m.get("id", "find"),
    "run": f"""\
items=$(find {m.get("ls_dir", "")} -name {m.get("ls_pattern", "")} | jq -R '.' | jq -cs .)
echo $items
echo items=$items >> $GITHUB_OUTPUT
""",
}
