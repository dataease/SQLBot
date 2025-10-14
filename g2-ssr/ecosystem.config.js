module.exports = {
    apps: [
      {
        name: "app",
        script: "./app.js",
        // 自动重启选项
        autorestart: true, // 启用自动重启
        restart_delay: 5000, // 重启延迟（毫秒）
      },
    ],
  };
  
  