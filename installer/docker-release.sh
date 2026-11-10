#!/bin/bash

SQLBOT_DOCKER_ENGINE_VERSION=29.9.3
SQLBOT_DOCKER_COMPOSE_VERSION=5.7.0

sqlbot_docker_arch() {
    case "$(uname -m)" in
        x86_64|amd64) echo x86_64 ;;
        aarch64|arm64) echo aarch64 ;;
        *) echo "Unsupported Docker architecture: $(uname -m)" >&2; return 1 ;;
    esac
}

sqlbot_fetch_verified() {
    local url="$1" destination="$2" checksum="$3"
    curl -fsSL --retry 3 --connect-timeout 15 -o "$destination" "$url" &&
        printf '%s  %s\n' "$checksum" "$destination" | sha256sum -c -
}

sqlbot_download_docker_engine() {
    local arch="$1" destination="$2" checksum
    case "$arch" in
        x86_64) checksum=3fb5d1f13014c18cc54945bc177c58a9056a482dada031e17d12cf2e6922c973 ;;
        aarch64) checksum=1b27fd739378ef938401e81ce5afb73b7ad7432d4f598814a9ff5f826bb464d2 ;;
        *) return 1 ;;
    esac
    sqlbot_fetch_verified "https://download.docker.com/linux/static/stable/$arch/docker-$SQLBOT_DOCKER_ENGINE_VERSION.tgz" \
        "$destination" "$checksum"
}

sqlbot_download_docker_compose() {
    local arch="$1" destination="$2" checksum
    case "$arch" in
        x86_64) checksum=7758048ad38e580f22559603312874fec8bb638d021a9e64182385fc17cc12a2 ;;
        aarch64) checksum=15861535d14e26555736b49376c95e14bfd94285366c8446bfac7156a972e76f ;;
        *) return 1 ;;
    esac
    sqlbot_fetch_verified "https://github.com/docker/compose/releases/download/v$SQLBOT_DOCKER_COMPOSE_VERSION/docker-compose-linux-$arch" \
        "$destination" "$checksum"
}

sqlbot_prepare_docker_bundle() (
    set -e
    local arch="$1" staging
    staging="$(mktemp -d)"
    trap 'rm -rf -- "$staging"' EXIT

    sqlbot_download_docker_engine "$arch" "$staging/docker.tgz"
    sqlbot_download_docker_compose "$arch" "$staging/docker-compose"
    curl -fsSL --retry 3 --connect-timeout 15 -o "$staging/docker.service" \
        https://resource-fit2cloud-com.oss-cn-hangzhou.aliyuncs.com/docker/docker.service

    mkdir -p docker/bin docker/service
    tar -xzf "$staging/docker.tgz" --strip-components=1 -C docker/bin
    install -m 0755 "$staging/docker-compose" docker/bin/docker-compose
    install -m 0644 "$staging/docker.service" docker/service/docker.service
)
