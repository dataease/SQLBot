# syntax=docker/dockerfile:1
ARG SQLBOT_RUNTIME_IMAGE=registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-python-pg:latest
ARG SQLBOT_BUILD_IMAGE=registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-build-base:latest
ARG NODE_IMAGE=node:22-bookworm-slim

FROM ghcr.io/1panel-dev/maxkb-vector-model:v1.0.1 AS vector-model

FROM --platform=$BUILDPLATFORM ${NODE_IMAGE} AS sqlbot-ui-builder
WORKDIR /tmp/frontend
COPY frontend/ ./
RUN npm install && npm run build

FROM ${SQLBOT_RUNTIME_IMAGE} AS runtime-base
# Rebuild Dockerfile-base first, then point this build at the rebuilt image.
RUN if ! node -e 'if (process.versions.node.split(".")[0] !== "22") process.exit(1)' \
        || [ -e /opt/dmdbms/bin/libssl.so ] \
        || ! dpkg --compare-versions "$(dpkg-query -W -f='${Version}' libharfbuzz0b)" ge '6.0.0+dfsg-3+sqlbot1' \
        || dpkg-query -W libtiff6 >/dev/null 2>&1; then \
        echo 'Rebuild Dockerfile-base and set SQLBOT_RUNTIME_IMAGE to the new image.' >&2; \
        exit 1; \
    fi

FROM ${SQLBOT_BUILD_IMAGE} AS build-base

FROM build-base AS sqlbot-builder
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/sqlbot/app \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /opt/sqlbot/app
COPY backend/ ./

# Resolve the security constraints together with the application dependencies.
# Elasticsearch 7.17.13 permits urllib3 2.x on Python 3.11. The source-built
# PostgreSQL and SQL Server drivers use the same patched OS libraries as runtime.
RUN python - <<'PY'
from pathlib import Path

project = Path('pyproject.toml')
contents = project.read_text()
for old, new in (
    ('psycopg[binary]<4.0.0,>=3.1.13', 'psycopg[c]<4.0.0,>=3.1.13'),
    ('psycopg2-binary (>=2.9.12,<3.0.0)', 'psycopg2 (>=2.9.12,<3.0.0)'),
    ('elasticsearch[requests] (>=7.10,<8.0)', 'elasticsearch[requests] (>=7.17.13,<8.0)'),
    ('dmpython==2.5.22', 'dmpython==2.6.1'),
):
    assert contents.count(old) == 1, old
    contents = contents.replace(old, new)
contents = contents.replace(
    '[tool.uv]\n',
    '[tool.uv]\nconstraint-dependencies = ["idna>=3.7", "setuptools>=78.1.1", "urllib3>=2.2.2,<3", "pymssql==2.4.6"]\n',
    1,
)
project.write_text(contents)
PY

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --extra cpu --python /usr/local/bin/python3.11 \
        --default-index https://pypi.org/simple \
        --no-binary-package psycopg2 --no-binary-package pymssql \
    && uv pip check --python .venv/bin/python \
    && .venv/bin/python -c 'import psycopg, psycopg2, pymssql; assert psycopg.pq.__impl__ == "c"'

FROM build-base AS ssr-builder
WORKDIR /app
COPY g2-ssr/app.js g2-ssr/package.json ./
COPY g2-ssr/charts/ ./charts/
# g2-ssr uses canvas. Drop the unused node-canvas fork, which targets old V8.
# Build the Node 22-compatible canvas release against distro libraries.
RUN npm pkg delete dependencies.node-canvas dependencies.nan \
    && npm pkg set 'overrides.canvas=^3.2.3' \
    && npm_config_build_from_source=true npm install --no-fund --no-audit --no-progress

FROM runtime-base
COPY --from=build-base /usr/local/lib/libsybdb.so.5.* /usr/local/lib/
COPY --from=build-base /etc/freetds/ /etc/freetds/
COPY --from=build-base /usr/local/share/doc/freetds/COPYING_LIB.txt /usr/local/share/doc/freetds/COPYING_LIB.txt
RUN ldconfig
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1
ENV SQLBOT_HOME=/opt/sqlbot
ENV PYTHONPATH=${SQLBOT_HOME}/app
ENV PATH="${SQLBOT_HOME}/app/.venv/bin:$PATH"
# The DM SSL symlinks need the wheel's hashed crypto library at load time.
ENV LD_LIBRARY_PATH="${SQLBOT_HOME}/app/.venv/lib/python3.11/site-packages/dmpython.libs:$LD_LIBRARY_PATH"

ENV POSTGRES_DB=sqlbot
ENV POSTGRES_USER=root
ENV POSTGRES_PASSWORD=Password123@pg

# Copy necessary files from builder
COPY start.sh /opt/sqlbot/app/start.sh
COPY g2-ssr/*.ttf /usr/share/fonts/truetype/liberation/
COPY --from=sqlbot-builder /opt/sqlbot/app/ /opt/sqlbot/app/
COPY --from=sqlbot-ui-builder /tmp/frontend/dist/ /opt/sqlbot/frontend/dist/
COPY --from=ssr-builder /app/ /opt/sqlbot/g2-ssr/
COPY g2-ssr/supervisord.conf /etc/supervisor/conf.d/g2-ssr.conf
COPY --from=vector-model /opt/maxkb/app/model /opt/sqlbot/models

WORKDIR ${SQLBOT_HOME}/app

RUN set -eu; \
    mkdir -p /opt/sqlbot/images /opt/sqlbot/g2-ssr/logs; \
    dmssl="$SQLBOT_HOME/app/.venv/lib/python3.11/site-packages/dmssl"; \
    for library in libssl.so libcrypto.so; do \
        test -f "$dmssl/$library"; \
        ln -s "$dmssl/$library" "$DM_HOME/bin/$library"; \
    done; \
    python -c 'import ctypes, os, ssl; import dmPython, psycopg, psycopg2, pymssql; assert psycopg.pq.__impl__ == "c"; ctypes.CDLL(os.environ["DM_HOME"] + "/bin/libssl.so")'; \
    node -e "require('/opt/sqlbot/g2-ssr/node_modules/@antv/g2-ssr')"

EXPOSE 3000 8000 8001 5432

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:8000/{os.environ.get(\"CONTEXT_PATH\", \"\")}', timeout=3)" || exit 1

ENTRYPOINT ["sh", "start.sh"]
