const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const PROJECT_ROOT = path.resolve(__dirname, '..');

function log(msg) { console.log(msg); }
function logError(msg) { console.error(`\x1b[31mERROR:\x1b[0m ${msg}`); }
function logSuccess(msg) { console.log(`\x1b[32mOK:\x1b[0m ${msg}`); }

function runScript(scriptName) {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(__dirname, `${scriptName}.js`);
    const child = spawn('node', [scriptPath], {
      cwd: PROJECT_ROOT,
      stdio: 'inherit',
      shell: os.platform() === 'win32'
    });

    child.on('error', (err) => reject(err));
    child.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`Script ${scriptName} exited with code ${code}`));
    });
  });
}

async function main() {
  log('='.repeat(50));
  log(' Resetting Project (Clean + Setup)');
  log('='.repeat(50));
  log('');

  try {
    log('Step 1: Cleaning...');
    await runScript('clean');
    log('');

    log('Step 2: Setting up...');
    await runScript('setup');
    log('');

    log('='.repeat(50));
    logSuccess('Reset complete!');
    log('Run "npm run dev" to start the application.');
    log('='.repeat(50));
  } catch (err) {
    logError(`Reset failed: ${err.message}`);
    process.exit(1);
  }
}

main();
