from src.com.actions.step import STEP_GENERATOR

npm_login: STEP_GENERATOR = lambda ctx, m: {
    "name": "Login to NPM",
    "env": {
        "NPMPASS": m.get("npm_pass", "${{ secrets.NPMPASS }}"),
        "NPMUSER": m.get("npm_user", "${{ secrets.NPMUSER }}"),
    },
    "run": """\
touch ~/.npmrc
npm config set userconfig ~/.npmrc

encoded_pw=$(printf '%s' "${NPMPASS}" | base64 | tr -d '\n')
encoded_auth=$(printf '%s' "${NPMUSER}:${NPMPASS}" | base64 | tr -d '\n')

npm set registry https://npm.yusufali.ca
npm set @servc:registry https://npm.yusufali.ca
npm set "//npm.yusufali.ca/:username" "${NPMUSER}"
npm set "//npm.yusufali.ca/:_password" "${encoded_pw}"
npm set "//npm.yusufali.ca/:_auth" "${encoded_auth}"
""",
}

npm_install: STEP_GENERATOR = lambda ctx, m: {
    "name": "Install dependencies",
    "run": "npm install",
    "working-directory": "",
}
