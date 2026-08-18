from src.com.actions.step import STEP_GENERATOR

pip_install: STEP_GENERATOR = lambda ctx, m: {
    "name": "Install pip dependencies",
    "env": {
        "EXTRA_MODULES": m.get("extra_modules", ""),
    },
    "run": """\
python -m venv .venv

if [ -n "$EXTRA_MODULES" ]; then
    .venv/bin/python -m pip install $EXTRA_MODULES
fi
if [ -f ../pip-options.txt ]; then
    cp ../pip-options.txt .
fi
if [ ! -f pip-options.txt ]; then
    touch pip-options.txt
fi

.venv/bin/python -m pip install -r requirements.txt -r pip-options.txt
.venv/bin/python -m pip install -r requirements-dev.txt -r pip-options.txt
""",
}
