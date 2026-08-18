# ignore

FROM python:3.13-slim AS builder-image
ARG DEBIAN_FRONTEND=noninteractive
ARG WORKDIR=/usr/src/

RUN python -m venv ${WORKDIR}/venv
ENV PATH="${WORKDIR}/venv/bin:$PATH"

COPY requirements.txt .
COPY pip-options.txt .
RUN pip install --no-cache-dir -r requirements.txt -r pip-options.txt

FROM python:3.13-slim AS app
ARG DEBIAN_FRONTEND=noninteractive
ARG WORKDIR=/usr/src/

COPY --from=builder-image ${WORKDIR}/venv ${WORKDIR}/venv
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# copy source code
RUN mkdir ${WORKDIR}/app
RUN adduser python
COPY src ${WORKDIR}/app/src
COPY main.py ${WORKDIR}/app/main.py
COPY trigger.py ${WORKDIR}/app/trigger.py

# activate nonroot user
USER python
WORKDIR ${WORKDIR}/app
RUN git config --global user.email "devopsbot@yusuf.email"
RUN git config --global user.name "DevOps Bot"

# activate virtualenv
ENV VIRTUAL_ENV=${WORKDIR}/venv
ENV PATH="${WORKDIR}/venv/bin:$PATH"
ENV GIT_PATH=/usr/bin/git
ENV PYTHON_VERSION=

CMD ["python", "trigger.py"]
