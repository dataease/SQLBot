#!/bin/bash

INSTALL_TYPE='install'
title_count=1

CURRENT_DIR=$(
    cd "$(dirname "$0")"
    pwd
)

function log() {
    echo -e "${1}" 2>&1 | tee -a ${CURRENT_DIR}/install.log
}

function log_title () {
    log "${title_count}. ${1}"
    let title_count++
}

function log_content () {
    log "\t${1}"
}

COMPROMISED_SECRET_KEY_SHA256='78682d15dcf21e49b462da00b3ab33355c095450e02e2b37ed601e08e1b799c5'

function secret_key_fingerprint() {
    printf '%s' "$1" | sha256sum | awk '{print $1}'
}

function prepare_secret_key() {
    local current_fingerprint=''
    local secret_action='generated'

    if [[ -n "${SQLBOT_SECRET_KEY:-}" ]]; then
        current_fingerprint=$(secret_key_fingerprint "${SQLBOT_SECRET_KEY}")
    fi

    if [[ "${current_fingerprint}" == "${COMPROMISED_SECRET_KEY_SHA256}" ]]; then
        secret_action='rotated'
        SQLBOT_SECRET_KEY=''
    fi

    if [[ -z "${SQLBOT_SECRET_KEY:-}" ]]; then
        SQLBOT_SECRET_KEY=$(
            LC_ALL=C tr -dc 'A-Za-z0-9_-' </dev/urandom | head -c 64
        )
        export SQLBOT_SECRET_KEY

        if [[ "${#SQLBOT_SECRET_KEY}" -ne 64 ]]; then
            log_content "生成 SQLBot Secret Key 失败"
            exit 1
        fi

        if [[ "${secret_action}" == 'rotated' ]]; then
            log_content "检测到已公开的 SQLBot Secret Key，已自动轮换，现有登录会话将失效"
        else
            log_content "已生成新的 SQLBot Secret Key"
        fi
    elif [[ "${#SQLBOT_SECRET_KEY}" -lt 32 ]]; then
        log_content "SQLBOT_SECRET_KEY 长度不能少于 32 个字符"
        exit 1
    fi
}

function check_and_prepare_env_params() {
    log "当前时间 : $(date)"
    log_title "检查安装环境并初始化环境变量"

    cd ${CURRENT_DIR}
    if [ -f /usr/bin/sctl ]; then
        echo "当前版本： $(sctl version | head -n 1)"

        # 获取已安装的 SQLBOT 的运行目录
        SQLBOT_BASE=$(grep "^SQLBOT_BASE=" /usr/bin/sctl | cut -d'=' -f2)
        SQLBOT_BASE_OLD=${SQLBOT_BASE}
        sed -i -e "s#SQLBOT_BASE=.*#SQLBOT_BASE=${SQLBOT_BASE}#g" sctl
        \cp sctl /usr/local/bin && chmod +x /usr/local/bin/sctl

        log_content "停止 SQLBot 服务"
        sctl stop

        INSTALL_TYPE='upgrade'
    fi

    set -a
    source ${CURRENT_DIR}/install.conf
    if [[ ${SQLBOT_BASE_OLD} ]];then
        SQLBOT_BASE=${SQLBOT_BASE_OLD}
        export SQLBOT_BASE=${SQLBOT_BASE_OLD}
    fi
    if [[ -d ${SQLBOT_BASE} ]] && [[ -f ${SQLBOT_BASE}/sqlbot/.env ]]; then
        source $SQLBOT_BASE/sqlbot/.env
        INSTALL_TYPE='upgrade'
        log_content "升级安装"
    else
        INSTALL_TYPE='install'
        mkdir -p ${SQLBOT_BASE}
        log_content "全新安装"
    fi
    prepare_secret_key
    set +a
}

function set_run_base_path() {
    log_title "设置运行目录"
    SQLBOT_RUN_BASE=$SQLBOT_BASE/sqlbot
    CONF_FOLDER=${SQLBOT_RUN_BASE}/conf
    TEMPLATES_FOLDER=${SQLBOT_RUN_BASE}/templates
    log_content "运行目录 $SQLBOT_RUN_BASE"
    log_content "配置文件目录 $CONF_FOLDER"
}

function prepare_sqlbot_run_base() {
    log_title "初始化运行目录"
    cd ${CURRENT_DIR}
    mkdir -p ${SQLBOT_RUN_BASE}
    log_content "复制安装文件到运行目录"
    cp -r ./sqlbot/* ${SQLBOT_RUN_BASE}/

    cd ${SQLBOT_RUN_BASE}
    env | grep SQLBOT_ >.env

    mkdir -p ${SQLBOT_RUN_BASE}/conf
    mkdir -p ${SQLBOT_RUN_BASE}/data/sqlbot/{excel,images,logs}

    if [ "${SQLBOT_EXTERNAL_DB}" = "false" ]; then
        mkdir -p ${SQLBOT_RUN_BASE}/data/postgresql
        export SQLBOT_DB_PORT=5432
    else
        sed -i -e "/^    depends_on/,+2d" docker-compose.yml
    fi

    log_content "调整配置文件参数"
    cd ${SQLBOT_RUN_BASE}
    cp -r ${TEMPLATES_FOLDER}/* ${CONF_FOLDER}

    cd ${TEMPLATES_FOLDER}
    templates_files=( sqlbot.conf )
    for i in ${templates_files[@]}; do
       if [ -f $i ]; then
           envsubst < $i > ${CONF_FOLDER}/$i
       fi
    done
}

function update_sctl() {
    log_title "安装 sctl 命令行工具"
    log_content "安装至 /usr/local/bin/sctl & /usr/bin/sctl"
    cd ${CURRENT_DIR}
    sed -i -e "s#SQLBOT_BASE=.*#SQLBOT_BASE=${SQLBOT_BASE}#g" sctl
    \cp sctl /usr/local/bin && chmod +x /usr/local/bin/sctl
    if [ ! -f /usr/bin/sctl ]; then
        ln -s /usr/local/bin/sctl /usr/bin/sctl 2>/dev/null
    fi
}

function prepare_system_settings() {
    log_title "修改操作系统相关设置"
    if which getenforce >/dev/null 2>&1 && [ $(getenforce) == "Enforcing" ];then
        log_content  "关闭 SELINUX"
        setenforce 0
        sed -i "s/SELINUX=enforcing/SELINUX=disabled/g" /etc/selinux/config
    fi

    if which firewall-cmd >/dev/null 2>&1; then
        if systemctl is-active firewalld &>/dev/null ;then
            log_content "开启防火墙端口 ${SQLBOT_WEB_PORT}"
            firewall-cmd --zone=public --add-port=${SQLBOT_WEB_PORT}/tcp --permanent
            log_content "开启防火墙端口 ${SQLBOT_MCP_PORT}"
            firewall-cmd --zone=public --add-port=${SQLBOT_MCP_PORT}/tcp --permanent
            firewall-cmd --reload
        else
            log_content "防火墙未开启，忽略端口开放"
        fi
    fi
}

function install_docker() {
    log_title "安装 docker"
    #Install docker
    ##Install Latest Stable Docker Release
    cd ${CURRENT_DIR}

    if which docker >/dev/null 2>&1; then
        log_content "检测到 Docker 已安装，跳过安装步骤"
        log_content "启动 Docker "
        service docker start >/dev/null 2>&1 | tee -a ${CURRENT_DIR}/install.log
    else
       if [[ -d docker ]]; then
           log_content "离线安装 docker"
           cp docker/bin/* /usr/bin/
           cp docker/service/docker.service /etc/systemd/system/
           chmod +x /usr/bin/docker*
           chmod 644 /etc/systemd/system/docker.service
       else
           log_content "在线安装 docker"
           curl -fsSL https://resource.fit2cloud.com/get-docker-linux.sh -o get-docker.sh 2>&1 | tee -a ${CURRENT_DIR}/install.log
           if [[ ! -f get-docker.sh ]];then
              log_content "docker 在线安装脚本下载失败，请稍候重试"
              exit 1
           fi
           sudo sh get-docker.sh 2>&1 | tee -a ${CURRENT_DIR}/install.log
       fi

       docker_config_folder="/etc/docker"
       if [ ! -d "$docker_config_folder" ];then
           mkdir -p "$docker_config_folder"
           cat <<EOF> $docker_config_folder/daemon.json
           {
              "log-driver": "json-file",
              "log-opts": {
                  "max-file": "3",
                  "max-size": "10m"
              }
           }
EOF
       fi

       log_content "启动 docker"
       systemctl enable docker >/dev/null 2>&1; systemctl daemon-reload; systemctl start docker 2>&1 | tee -a ${CURRENT_DIR}/install.log

       docker version >/dev/null 2>&1
       if [ $? -ne 0 ]; then
           log_content "docker 安装失败"
           exit 1
       else
           log_content "docker 安装成功"

       fi
    fi
}

function install_docker_compose() {
    log_title "安装 docker-compose"
    #Install docker-compose
    cd ${CURRENT_DIR}
    ##Install Latest Stable Docker Compose Release
    docker-compose version >/dev/null 2>&1
    if [ $? -ne 0 ]; then
       docker compose version >/dev/null 2>&1
       if [ $? -eq 0 ]; then
           echo 'docker compose "$@"' > /usr/bin/docker-compose
           chmod +x /usr/bin/docker-compose
       else
           if [[ -d docker ]]; then
              log_content "离线安装 docker-compose"
              cp docker/bin/docker-compose /usr/bin/
              chmod +x /usr/bin/docker-compose
           else
              log_content "在线安装 docker-compose"
              curl -L https://resource.fit2cloud.com/docker/compose/releases/download/v2.16.0/docker-compose-$(uname -s | tr A-Z a-z)-$(uname -m) -o /usr/local/bin/docker-compose 2>&1 | tee -a ${CURRENT_DIR}/install.log
              if [[ ! -f /usr/local/bin/docker-compose ]];then
                  log_content "docker-compose 下载失败，请稍候重试"
                  exit 1
              fi
              chmod +x /usr/local/bin/docker-compose
              ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
           fi
       fi

       docker-compose version >/dev/null
       if [ $? -ne 0 ]; then
           log_content "docker-compose 安装失败"
           exit 1
       else
           log_content "docker-compose 安装成功"
       fi
    else
       log_content "检测到 Docker Compose 已安装，跳过安装步骤"
    fi
    export COMPOSE_HTTP_TIMEOUT=180
}

function load_images() {
    log_title "加载 SQLBOT 镜像"
    cd ${CURRENT_DIR}

    for i in $(docker images --format '{{.Repository}}:{{.Tag}}' | grep dataease); do
       current_images[${#current_images[@]}]=${i##*/}
    done

    # 加载镜像
    if [[ -d images ]]; then
       for i in $(ls images); do
           if [[ "${current_images[@]}"  =~ "${i%.tar.gz}" ]]; then
              log_content "已存在镜像 ${i%.tar.gz}"
           else
              log_content "加载镜像 ${i%.tar.gz}"
              docker load -i images/$i >/dev/null 2>&1 | tee -a ${CURRENT_DIR}/install.log
           fi
       done
    else
       SQLBOTVERSION=$(cat ${CURRENT_DIR}/sqlbot/templates/version)
       curl -sfL https://resource.fit2cloud.com/installation-log.sh | sh -s sqlbot ${INSTALL_TYPE} ${SQLBOTVERSION}
    fi
}

function start_sqlbot() {
    log_title "启动 SQLBOT 服务"
    sctl reload 2>&1 | tee -a ${CURRENT_DIR}/install.log
    if [[ $? -ne 0 ]]; then
        log_content "SQLBOT 服务启动失败，请检查日志"
        exit 1
    fi
    echo
    if [[ $INSTALL_TYPE != "upgrade" ]];then
       echo -e "======================= 安装完成 =======================\n" 2>&1 | tee -a ${CURRENT_DIR}/install.log
       echo -e "系统登录信息如下:\n\t访问地址: http://服务器IP:$SQLBOT_WEB_PORT\n\t用户名: admin\n\t初始密码: SQLBot@123456" 2>&1 | tee -a ${CURRENT_DIR}/install.log
    else
       echo -e "======================= 升级完成 =======================\n" 2>&1 | tee -a ${CURRENT_DIR}/install.log
    fi
}

function main() {
    check_and_prepare_env_params
    set_run_base_path
    prepare_sqlbot_run_base
    update_sctl
    prepare_system_settings
    install_docker
    install_docker_compose
    load_images
    start_sqlbot
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main
fi
