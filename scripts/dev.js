const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const PROJECT_ROOT = path.resolve(__dirname, '..');

function log(msg) { console.log(msg); }
function logError(msg) { console.error(`\x1b[31mERROR:\x1b[0m ${msg}`); }
function logSuccess(msg) { console.log(`\x1b[32mOK:\x1b[0m ${msg}`); }

function getPythonExe() {
  if (os.platform() === 'win32') {
    return path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe');
  }
  return path.join(PROJECT_ROOT, '.venv', 'bin', 'python');
}

function main() {
  const venvDir = path.join(PROJECT_ROOT, '.venv');
  const envPath = path.join(PROJECT_ROOT, '.env');

  if (!fs.existsSync(venvDir)) {
    logError('Virtual environment not found. Run "npm run setup" first.');
    process.exit(1);
  }
  if (!fs.existsSync(envPath)) {
    logError('.env file not found. Run "npm run setup" first.');
    process.exit(1);
  }

  log('Starting development server...');
  log('Open http://localhost:5000');
  log('Press Ctrl+C to stop');
  log('');

  const python = getPythonExe();
  const child = spawn(python, ['start.py'], {
    cwd: PROJECT_ROOT,
    stdio: 'inherit',
    shell: os.platform() === 'win32'
  });

  child.on('error', (err) => {
    logError(`Failed to start server: ${err.message}`);
    process.exit(1);
  });

  child.on('exit', (code) => {
    if (code !== 0 && code !== null) {
      logError(`Server exited with code ${code}`);
    }
  });
}

main();
