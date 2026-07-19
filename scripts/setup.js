const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const os = require('os');
const crypto = require('crypto');

const PROJECT_ROOT = path.resolve(__dirname, '..');

function log(msg) { console.log(msg); }
function logError(msg) { console.error(`\x1b[31mERROR:\x1b[0m ${msg}`); }
function logSuccess(msg) { console.log(`\x1b[32mOK:\x1b[0m ${msg}`); }
function logInfo(msg) { console.log(`\x1b[36mINFO:\x1b[0m ${msg}`); }

function runCommand(cmd, options = {}) {
  try {
    const result = execSync(cmd, {
      encoding: 'utf8',
      cwd: PROJECT_ROOT,
      stdio: options.silent ? 'pipe' : 'inherit',
      ...options
    });
    return { success: true, output: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function getPythonCmd() {
  const cmds = ['python', 'python3', 'py'];
  for (const cmd of cmds) {
    try {
      const result = execSync(`${cmd} --version`, { encoding: 'utf8', stdio: 'pipe' });
      if (result.includes('Python')) return cmd;
    } catch (e) {}
  }
  return 'python';
}

function getPipCmd(python) {
  const platform = os.platform();
  if (platform === 'win32') {
    return path.join('.venv', 'Scripts', 'pip.exe');
  }
  return path.join('.venv', 'bin', 'pip');
}

function getPythonExe(python) {
  const platform = os.platform();
  if (platform === 'win32') {
    return path.join('.venv', 'Scripts', 'python.exe');
  }
  return path.join('.venv', 'bin', 'python');
}

function checkPython() {
  const python = getPythonCmd();
  const result = runCommand(`${python} --version`, { silent: true });
  if (!result.success) {
    logError('Python 3.8+ is required but not found.');
    log('  Download from: https://www.python.org/downloads/');
    process.exit(1);
  }
  logSuccess(`Python found: ${python} (${result.output.trim()})`);
  return python;
}

function checkPostgres() {
  const platform = os.platform();
  let found = false;

  if (platform === 'win32') {
    const paths = [
      "C:/Program Files/PostgreSQL/18/bin/psql.exe",
      "C:/Program Files/PostgreSQL/17/bin/psql.exe",
      "C:/Program Files/PostgreSQL/16/bin/psql.exe",
      "C:/Program Files/PostgreSQL/15/bin/psql.exe",
      "C:/Program Files/PostgreSQL/14/bin/psql.exe",
    ];
    found = paths.some(p => fs.existsSync(p));
  } else {
    const result = runCommand('which psql', { silent: true });
    found = result.success;
  }

  if (!found) {
    logWarn('PostgreSQL not detected on this machine.');
    log('  Install PostgreSQL: https://www.postgresql.org/download/');
    log('  Or use Docker: docker compose up');
    return false;
  }
  logSuccess('PostgreSQL found');
  return true;
}

function ensureEnv() {
  const envPath = path.join(PROJECT_ROOT, '.env');
  const examplePath = path.join(PROJECT_ROOT, '.env.example');

  if (fs.existsSync(envPath)) {
    logInfo('.env already exists');
    return true;
  }

  if (!fs.existsSync(examplePath)) {
    logError('.env.example not found!');
    return false;
  }

  let envContent = fs.readFileSync(examplePath, 'utf8');
  const secretKey = crypto.randomBytes(32).toString('hex');
  envContent = envContent.replace(/SECRET_KEY=.*/, `SECRET_KEY=${secretKey}`);

  fs.writeFileSync(envPath, envContent);
  logSuccess('Created .env from .env.example with random SECRET_KEY');
  return true;
}

function createVenV(python) {
  const venvDir = path.join(PROJECT_ROOT, '.venv');
  if (fs.existsSync(venvDir)) {
    logInfo('Virtual environment already exists');
    return true;
  }

  log('Creating virtual environment...');
  const result = runCommand(`${python} -m venv .venv`);
  if (result.success) {
    logSuccess('Virtual environment created');
    return true;
  }
  logError('Failed to create virtual environment');
  return false;
}

function installDependencies(python) {
  log('Installing Python dependencies...');
  const pip = getPipCmd(python);
  const result = runCommand(`"${pip}" install -r requirements.txt`);
  if (result.success) {
    logSuccess('Dependencies installed');
    return true;
  }
  logError('Failed to install dependencies');
  return false;
}

function createFolders() {
  const folders = ['uploads', 'logs'];
  for (const folder of folders) {
    const dir = path.join(PROJECT_ROOT, folder);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
      logSuccess(`Created folder: ${folder}/`);
    }
  }
  return true;
}

function initDatabase(python) {
  log('Initializing database...');
  const py = getPythonExe(python);

  // Run cross-platform DB setup
  const setupResult = runCommand(`"${py}" scripts/setup_db.py`);
  if (!setupResult.success) {
    logWarn('Database setup encountered issues, trying to continue...');
  } else {
    logSuccess('Database user/database ensured');
  }

  // Run app-level init (creates tables and seeds data)
  const initResult = runCommand(`"${py}" -c "import models; models.initialize_database()"`);
  if (initResult.success) {
    logSuccess('Database tables created and seeded');
    return true;
  }
  logError('Failed to initialize database tables');
  return false;
}

function main() {
  log('='.repeat(60));
  log(' Multi-Plant DMS - Zero Setup');
  log('='.repeat(60));

  const python = checkPython();

  const hasPostgres = checkPostgres();
  if (!hasPostgres) {
    log('');
    log('TIP: Run with Docker instead:');
    log('  docker compose up');
    process.exit(1);
  }

  if (!createVenV(python)) process.exit(1);
  if (!installDependencies(python)) process.exit(1);
  if (!ensureEnv()) process.exit(1);
  createFolders();

  const dbReady = initDatabase(python);
  if (!dbReady) {
    logWarn('Database initialization had issues. Check your PostgreSQL connection.');
  }

  log('');
  log('='.repeat(60));
  logSuccess('Setup complete!');
  log('');
  log('Next steps:');
  log('  npm run dev      - Start development server');
  log('  npm run doctor   - Check environment health');
  log('  npm run start    - Start production server');
  log('='.repeat(60));
}

main();
