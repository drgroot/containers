from src.com.actions.step import STEP_GENERATOR
from src.lib import (
    HELM_VERSION,
    JAVA_DISTRUBUTION,
    JAVA_VERSION,
    JFROG_VERSION,
    JQ_VERSION,
    KUBECTL_VERSION,
    KUBELOGIN_VERSION,
    MAVEN_VERSION,
    NODEJS_VERSION,
    PYTHON_VERSION,
    TERRAFORM_VERSION,
    YQ_VERSION,
)
from src.lib.actions.steps.actions import (
    SETUP_HELM_VERSION,
    SETUP_JFROG_VERSION,
    SETUP_JQ_VERSION,
    SETUP_KUBECTL_VERSION,
    SETUP_KUBELOGIN_VERSION,
    SETUP_MAVEN_VERSION,
    SETUP_NODE_VERSION,
    SETUP_PYTHON_VERSION,
    SETUP_TERRAFORM_VERSION,
    SETUP_YQ_VERSION,
)

nodejs: STEP_GENERATOR = lambda ctx, m: {
    "uses": f"actions/setup-node@{m.get('setup_node_version', SETUP_NODE_VERSION)}",
    "with": {
        "node-version": m.get("node_version", NODEJS_VERSION),
    },
}

python: STEP_GENERATOR = lambda ctx, m: {
    "uses": f"actions/setup-python@{m.get('setup_python_version', SETUP_PYTHON_VERSION)}",
    "with": {
        "python-version": m.get("python_version", PYTHON_VERSION),
    },
}

jq: STEP_GENERATOR = lambda ctx, m: {
    "uses": f"dcarbone/install-jq-action@{m.get('setup_jq_version', SETUP_JQ_VERSION)}",
    "with": {
        "version": m.get("jq_version", JQ_VERSION),
    },
}

yq: STEP_GENERATOR = lambda ctx, m: {
    "uses": f"chrisdickinson/setup-yq@{m.get('setup_yq_version', SETUP_YQ_VERSION)}",
    "with": {
        "yq-version": m.get("yq_version", YQ_VERSION),
    },
}

maven: STEP_GENERATOR = lambda ctx, m: {
    "uses": f"s4u/setup-maven-action@{m.get('setup_maven_version', SETUP_MAVEN_VERSION)}",
    "with": {
        "java-version": m.get("java_version", JAVA_VERSION),
        "java-distribution": m.get("java_distribution", JAVA_DISTRUBUTION),
        "maven-version": m.get("maven_version", MAVEN_VERSION),
        "cache-enabled": False,
    },
}

jfrog: STEP_GENERATOR = lambda ctx, m: {
    "uses": f"jfrog/setup-jfrog-cli@{m.get('setup_jfrog_version', SETUP_JFROG_VERSION)}",
    "with": {
        "jfrog-cli-version": m.get("jfrog_version", JFROG_VERSION),
    },
}

kubectl: STEP_GENERATOR = lambda ctx, m: {
    "uses": f"azure/setup-kubectl@{m.get('setup_kubectl_version', SETUP_KUBECTL_VERSION)}",
    "with": {
        "version": m.get("kubectl_version", KUBECTL_VERSION),
    },
}

helm: STEP_GENERATOR = lambda ctx, m: {
    "uses": f"azure/setup-helm@{m.get('setup_helm_version', SETUP_HELM_VERSION)}",
    "with": {
        "version": m.get("version", HELM_VERSION),
    },
}

kubelogin: STEP_GENERATOR = lambda ctx, m: {
    "uses": f"azure/use-kubelogin@{m.get('setup_kubelogin_version', SETUP_KUBELOGIN_VERSION)}",
    "env": {
        "GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
    },
    "with": {
        "kubelogin-version": m.get("kubelogin-version", KUBELOGIN_VERSION),
        "skip-cache": True,
    },
}

terraform: STEP_GENERATOR = lambda ctx, m: {
    "uses": f"hashicorp/setup-terraform@{m.get('setup_terraform_version', SETUP_TERRAFORM_VERSION)}",
    "with": {
        "terraform_version": m.get("terraform_version", TERRAFORM_VERSION),
    },
}
