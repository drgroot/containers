FROM python:3.13-slim AS builder-image
ARG DEBIAN_FRONTEND=noninteractive
ARG WORKDIR=/usr/src/

RUN python -m venv ${WORKDIR}/venv
ENV PATH="${WORKDIR}/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim AS app
ARG DEBIAN_FRONTEND=noninteractive
ARG WORKDIR=/usr/src/

COPY --from=builder-image ${WORKDIR}/venv ${WORKDIR}/venv


# copy source code
RUN mkdir ${WORKDIR}/app
RUN adduser --system --no-create-home python
COPY src ${WORKDIR}/app/src
COPY *.py ${WORKDIR}/app/

# activate nonroot user
USER python
WORKDIR ${WORKDIR}/app

# activate virtualenv
ENV VIRTUAL_ENV=${WORKDIR}/venv
ENV PATH="${WORKDIR}/venv/bin:$PATH"
ENV CONF__LAKE__CATALOG_NAME=default
ENV CONF__LAKE__CATALOG_PROPERTIES__TYPE=sql
ENV CONF__LAKE__CATALOG_PROPERTIES__INIT_CATALOG_TABLES=true

CMD ["python", "main.py"]
