module.exports = {
  apps: [{
    name: 'claimgpt',
    script: 'python3',
    args: '-m uvicorn app.server:app --host 0.0.0.0 --port 3000',
    cwd: '/home/user/claimgpt',
    interpreter: 'none',
    watch: false,
    instances: 1,
    exec_mode: 'fork',
    env: { PYTHONUNBUFFERED: '1' }
  }]
}
