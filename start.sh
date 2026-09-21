SSR_PATH=/opt/sqlbot/g2-ssr
APP_PATH=/opt/sqlbot/app

/usr/local/bin/docker-entrypoint.sh postgres &
MAX_WAIT=120  
WAIT_COUNT=0  
echo "Waiting for PostgreSQL to complete crash recovery and accept connections (max ${MAX_WAIT}s)..."  
until pg_isready -h 127.0.0.1 -p 5432 -U postgres -q; do  
    if [ $WAIT_COUNT -ge $MAX_WAIT ]; then  
        echo -e "\033[1;31mError: PostgreSQL failed to become ready within ${MAX_WAIT} seconds. Exiting to avoid hanging.\033[0m"  
        exit 1  
    fi  
    sleep 2  
    WAIT_COUNT=$((WAIT_COUNT + 2))  
done  
echo -e "\033[1;32mPostgreSQL is fully ready and accepting connections (took ${WAIT_COUNT}s).\033[0m"

nohup /usr/bin/supervisord -c /etc/supervisor/supervisord.conf &

nohup uvicorn main:mcp_app --host 0.0.0.0 --port 8001 --proxy-headers --forwarded-allow-ips='*' &

cd $APP_PATH
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips='*'
