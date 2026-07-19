const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const https = require('https');
const http = require('http');

const PROJECT_ROOT = path.resolve(__dirname, '..');

function log(msg) { console.log(msg); }
function logError(msg) { console.error(`\x1b[31mERROR:\x1b[0m ${msg}`); }
function logSuccess(msg) { console.log(`\x1b[32mOK:\x1b[0m ${msg}`); }
function logWarn(msg) { console.log(`\x1b[33mWARN:\x1b[0m ${msg}`); }
function logInfo(msg) { console.log(`\x1b[36mINFO:\x1b[0m ${msg}`); }

function getPythonCmd() {
  const cmds = ['python', 'python3', 'py'];
  for (const cmd of cmds) {
    try {
      execSync(`${cmd} --version`, { encoding: 'utf8', stdio: 'pipe' });
      return cmd;
    } catch (e) {}
  }
  return null;
}

function checkPostgres() {
  const platform = os.platform();
  if (platform === 'win32') {
    const paths = [
      "C:/Program Files/PostgreSQL/18/bin/psql.exe",
      "C:/Program Files/PostgreSQL/17/bin/psql.exe",
      "C:/Program Files/PostgreSQL/16/bin/psql.exe",
      "C:/Program Files/PostgreSQL/15/bin/psql.exe",
      "C:/Program Files/PostgreSQL/14/bin/psql.exe",
    ];
    return paths.some(p => fs.existsSync(p));
  }
  try {
    execSync('which psql', { stdio: 'pipe' });
    return true;
  } catch (e) {
    return false;
  }
}

function checkDbConnection() {
  try {
    const python = os.platform() === 'win32'
      ? path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe')
      : path.join(PROJECT_ROOT, '.venv', 'bin', 'python');
    execSync(`"${python}" -c "import models; models.get_db_connection()"`, {
      cwd: PROJECT_ROOT,
      stdio: 'pipe',
      env: { ...process.env }
    });
    return true;
  } catch (e) {
    return false;
  }
}

function checkNode() {
  try {
    const version = execSync('node --version', { encoding: 'utf8', stdio: 'pipe' }).trim();
    return { exists: true, version };
  } catch (e) {
    return { exists: false, version: null };
  }
}

function checkNpm() {
  try {
    const version = execSync('npm --version', { encoding: 'utf8', stdio: 'pipe' }).trim();
    return { exists: true, version };
  } catch (e) {
    return { exists: false, version: null };
  }
}

function checkDocker() {
  try {
    execSync('docker --version', { stdio: 'pipe' });
    execSync('docker compose version', { stdio: 'pipe' });
    return true;
  } catch (e) {
    return false;
  }
}

function main() {
  log('='.repeat(50));
  log(' Doctor - Environment Health Check');
  log('='.repeat(50));
  log('');

  let issues = 0;
  let fixes = 0;

  // Check Node.js
  const node = checkNode();
  if (node.exists) {
    logSuccess(`Node.js: ${node.version}`);
  } else {
    logError('Node.js not found');
    issues++;
  }

  // Check npm
  const npm = checkNpm();
  if (npm.exists) {
    logSuccess(`npm: ${npm.version}`);
  } else {
    logError('npm not found');
    issues++;
  }

  // Check Python
  const python = getPythonCmd();
  if (python) {
    const version = execSync(`${python} --version`, { encoding: 'utf8', stdio: 'pipe' }).trim();
    logSuccess(`Python: ${version}`);
  } else {
    logError('Python 3.8+ not found');
    issues++;
  }

  // Check virtual environment
  const venvDir = path.join(PROJECT_ROOT, '.venv');
  if (fs.existsSync(venvDir)) {
    logSuccess('Virtual environment: exists');
  } else {
    logWarn('Virtual environment: missing');
    logInfo('  Fix: Run "npm run setup"');
    issues++;
  }

  // Check .env
  const envPath = path.join(PROJECT_ROOT, '.env');
  if (fs.existsSync(envPath)) {
    logSuccess('.env file: exists');

    // Validate critical vars
    const envContent = fs.readFileSync(envPath, 'utf8');
    if (envContent.includes('SECRET_KEY=') && !envContent.includes('SECRET_KEY=change-in-production')) {
      logSuccess('SECRET_KEY: configured');
    } else {
      logWarn('SECRET_KEY: using default or placeholder');
    }
  } else {
    logWarn('.env file: missing');
    logInfo('  Fix: Run "npm run setup"');
    issues++;
  }

  // Check PostgreSQL
  if (checkPostgres()) {
    logSuccess('PostgreSQL: installed');
  } else {
    logWarn('PostgreSQL: not detected');
    logInfo('  Alternative: Use Docker (docker compose up)');
  }

  // Check database connectivity
  if (fs.existsSync(venvDir) && fs.existsSync(envPath)) {
    if (checkDbConnection()) {
      logSuccess('Database connection: OK');
    } else {
      logWarn('Database connection: failed');
      logInfo('  Fix: Ensure PostgreSQL is running and DATABASE_URL is correct');
      issues++;
    }
  }

  // Check Docker
  if (checkDocker()) {
    logSuccess('Docker + Compose: available');
  } else {
    logInfo('Docker: not available (optional)');
  }

  // Check uploads folder
  const uploadsDir = path.join(PROJECT_ROOT, 'uploads');
  if (fs.existsSync(uploadsDir)) {
    logSuccess('Uploads folder: exists');
  } else {
    logWarn('Uploads folder: missing');
    logInfo('  Fix: Run "npm run setup"');
  }

  log('');
  log('='.repeat(50));
  if (issues === 0) {
    logSuccess(`All checks passed! ${fixes} issues fixed.`);
    log('');
    log('You can now run:');
    log('  npm run dev');
  } else {
    logWarn(`Found ${issues} issue(s). See suggestions above.`);
    log('');
    log('Quick fixes:');
    log('  npm run setup    - Full project setup');
    log('  npm run reset    - Clean and re-setup');
    log('  docker compose up - Run with Docker');
  }
  log('='.repeat(50));
}

main();
