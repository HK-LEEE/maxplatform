module.exports = {
  apps: [
    {
      name: 'maxplatform-backend-8000',
      script: '/home/app-user/maxproject/maxplatform/backend/.venv/bin/python',
      args: '-m uvicorn app.main:app --host 127.0.0.1 --port 8000',
      cwd: '/home/app-user/maxproject/maxplatform/backend',
      instances: 1,
      exec_mode: 'fork',
      interpreter: 'none',
      env: {
        PORT: '8000',  // 중요: 각 인스턴스마다 다른 포트 지정
        HOST: '127.0.0.1',
        DEBUG: 'False',
        NODE_ENV: 'production',
        PYTHONPATH: '/home/app-user/maxproject/maxplatform/backend'
      },
      watch: false,
      max_memory_restart: '1G',
      error_file: '/home/app-user/maxproject/maxplatform/backend/logs/pm2-error-8000.log',
      out_file: '/home/app-user/maxproject/maxplatform/backend/logs/pm2-out-8000.log',
      log_file: '/home/app-user/maxproject/maxplatform/backend/logs/pm2-combined-8000.log',
      time: true
    },
    {
      name: 'maxplatform-backend-8001',
      script: '/home/app-user/maxproject/maxplatform/backend/.venv/bin/python',
      args: '-m uvicorn app.main:app --host 127.0.0.1 --port 8001',
      cwd: '/home/app-user/maxproject/maxplatform/backend',
      instances: 1,
      exec_mode: 'fork',
      interpreter: 'none',
      env: {
        PORT: '8001',  // 중요: 각 인스턴스마다 다른 포트 지정
        HOST: '127.0.0.1',
        DEBUG: 'False',
        NODE_ENV: 'production',
        PYTHONPATH: '/home/app-user/maxproject/maxplatform/backend'
      },
      watch: false,
      max_memory_restart: '1G',
      error_file: '/home/app-user/maxproject/maxplatform/backend/logs/pm2-error-8001.log',
      out_file: '/home/app-user/maxproject/maxplatform/backend/logs/pm2-out-8001.log',
      log_file: '/home/app-user/maxproject/maxplatform/backend/logs/pm2-combined-8001.log',
      time: true
    },
    {
      name: 'maxplatform-backend-8002',
      script: '/home/app-user/maxproject/maxplatform/backend/.venv/bin/python',
      args: '-m uvicorn app.main:app --host 127.0.0.1 --port 8002',
      cwd: '/home/app-user/maxproject/maxplatform/backend',
      instances: 1,
      exec_mode: 'fork',
      interpreter: 'none',
      env: {
        PORT: '8002',  // 중요: 각 인스턴스마다 다른 포트 지정
        HOST: '127.0.0.1',
        DEBUG: 'False',
        NODE_ENV: 'production',
        PYTHONPATH: '/home/app-user/maxproject/maxplatform/backend'
      },
      watch: false,
      max_memory_restart: '1G',
      error_file: '/home/app-user/maxproject/maxplatform/backend/logs/pm2-error-8002.log',
      out_file: '/home/app-user/maxproject/maxplatform/backend/logs/pm2-out-8002.log',
      log_file: '/home/app-user/maxproject/maxplatform/backend/logs/pm2-combined-8002.log',
      time: true
    }
  ]
}
