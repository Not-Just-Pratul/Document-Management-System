const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const os = require('os');

const PROJECT_ROOT = path.resolve(__dirname, '..');

function log(msg) { console.log(msg); }
function logError(msg) { console.error(`\x1b[31mERROR:\x1b[0m ${msg}`); }
function logSuccess(msg) { console.log(`\x1b[32mOK:\x1b[0m ${msg}`); }
function logWarn(msg) { console.log(`\x1b[33mWARN:\x1b[0m ${msg}`); }
function logInfo(msg) { console.log(`\x1b[36mINFO:\x1b[0m ${msg}`); }

function removePath(p) {
  if (fs.existsSync(p)) {
    try {
      if (fs.lstatSync(p).isDirectory()) {
        fs.rmSync(p, { recursive: true, force: true });
      } else {
        fs.unlinkSync(p);
      }
      logSuccess(`Removed: ${p}`);
    } catch (e) {
      if (e.code === 'EBUSY' || e.code === 'EPERM') {
        logWarn(`Could not remove ${p} (file is locked). Close any running processes and try again.`);
      } else {
        logError(`Failed to remove ${p}: ${e.message}`);
      }
    }
  }
}

function main() {
  log('='.repeat(50));
  log(' Cleaning Project Artifacts');
  log('='.repeat(50));

  const itemsToClean = [
    '.venv',
    '__pycache__',
    '.env',
    'app.log',
    'dist',
    'build',
    'node_modules'
  ];

  let cleaned = 0;
  for (const item of itemsToClean) {
    const fullPath = path.join(PROJECT_ROOT, item);
    if (fs.existsSync(fullPath)) {
      removePath(fullPath);
      cleaned++;
    }
  }

  // Clean uploads
  const uploadsDir = path.join(PROJECT_ROOT, 'uploads');
  if (fs.existsSync(uploadsDir)) {
    const files = fs.readdirSync(uploadsDir);
    for (const file of files) {
      removePath(path.join(uploadsDir, file));
    }
    // Remove empty year folders
    const years = fs.readdirSync(uploadsDir);
    for (const year of years) {
      const yearPath = path.join(uploadsDir, year);
      if (fs.lstatSync(yearPath).isDirectory()) {
        const months = fs.readdirSync(yearPath);
        for (const month of months) {
          removePath(path.join(yearPath, month));
        }
        if (fs.readdirSync(yearPath).length === 0) {
          fs.rmdirSync(yearPath);
        }
      }
    }
    logSuccess('Cleaned uploads folder');
    cleaned++;
  }

  log('');
  logSuccess(`Cleaned ${cleaned} items.`);
  log('');
  logInfo('.env.example and source code preserved.');
  log('Run "npm run setup" to reinitialize.');
}

main();
