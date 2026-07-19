const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const PROJECT_ROOT = path.resolve(__dirname, '..');

function log(msg) { console.log(msg); }
function logError(msg) { console.error(`\x1b[31mERROR:\x1b[0m ${msg}`); }
function logSuccess(msg) { console.log(`\x1b[32mOK:\x1b[0m ${msg}`); }
function logInfo(msg) { console.log(`\x1b[36mINFO:\x1b[0m ${msg}`); }

function getPythonExe() {
  if (os.platform() === 'win32') {
    return path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe');
  }
  return path.join(PROJECT_ROOT, '.venv', 'bin', 'python');
}

function checkPythonSyntax(file) {
  const python = getPythonExe();
  try {
    execSync(`"${python}" -m py_compile "${file}"`, { cwd: PROJECT_ROOT, stdio: 'pipe' });
    return true;
  } catch (e) {
    return false;
  }
}

function main() {
  log('='.repeat(50));
  log(' Building / Validating Project');
  log('='.repeat(50));

  const python = getPythonExe();
  const venvDir = path.join(PROJECT_ROOT, '.venv');

  // 1. Ensure venv exists
  if (!fs.existsSync(venvDir)) {
    logError('Virtual environment not found. Run "npm run setup" first.');
    process.exit(1);
  }
  logSuccess('Virtual environment exists');

  // 2. Install production dependencies
  log('Installing production dependencies...');
  const pip = os.platform() === 'win32'
    ? path.join('.venv', 'Scripts', 'pip.exe')
    : path.join('.venv', 'bin', 'pip');

  try {
    execSync(`"${pip}" install -r requirements.txt`, { cwd: PROJECT_ROOT, stdio: 'inherit' });
    logSuccess('Production dependencies installed');
  } catch (e) {
    logError('Failed to install dependencies');
    process.exit(1);
  }

  // 3. Syntax check Python files
  log('Checking Python syntax...');
  const pyFiles = fs.readdirSync(PROJECT_ROOT).filter(f => f.endsWith('.py'));
  let syntaxOk = true;
  for (const file of pyFiles) {
    if (!checkPythonSyntax(file)) {
      logError(`Syntax error in ${file}`);
      syntaxOk = false;
    }
  }
  if (syntaxOk) {
    logSuccess('All Python files pass syntax check');
  } else {
    process.exit(1);
  }

  // 4. Validate templates exist
  log('Checking templates...');
  const templateDir = path.join(PROJECT_ROOT, 'templates');
  if (fs.existsSync(templateDir)) {
    const templates = fs.readdirSync(templateDir);
    logSuccess(`Found ${templates.length} templates`);
  } else {
    logError('templates/ directory missing');
    process.exit(1);
  }

  // 5. Validate .env
  const envPath = path.join(PROJECT_ROOT, '.env');
  if (!fs.existsSync(envPath)) {
    logWarn('.env not found. Run "npm run setup" to create it.');
  } else {
    logSuccess('.env exists');
  }

  // 6. Validate static assets
  const staticDir = path.join(PROJECT_ROOT, 'static');
  if (fs.existsSync(staticDir)) {
    logSuccess('Static assets present');
  }

  log('');
  logSuccess('Build validation passed!');
}

main();
