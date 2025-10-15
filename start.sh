SSR_PATH=/opt/sqlbot/g2-ssr
APP_PATH=/opt/sqlbot/app
PM2_CMD_PATH=$SSR_PATH/node_modules/pm2/bin/pm2

/usr/local/bin/docker-entrypoint.sh postgres &
sleep 5
wait-for-it 127.0.0.1:5432 --timeout=120 --strict -- echo -e "\033[1;32mPostgreSQL started.\033[0m"

nohup $PM2_CMD_PATH start $SSR_PATH/app.js &

nohup uvicorn main:mcp_app --host 0.0.0.0 --port 8001 &

cd $APP_PATH
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers
