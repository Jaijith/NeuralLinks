/**
 * Build Test Script
 * Verifies the app builds successfully
 */

const { execSync } = require('child_process');
const path = require('path');

const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

const log = {
  info: (msg) => console.log(`${colors.blue}ℹ${colors.reset} ${msg}`),
  success: (msg) => console.log(`${colors.green}✅${colors.reset} ${msg}`),
  error: (msg) => console.log(`${colors.red}❌${colors.reset} ${msg}`),
  section: (msg) => console.log(`\n${colors.cyan}━━━ ${msg} ━━━${colors.reset}\n`),
};

log.section('Build Test');

try {
  log.info('Running build...');
  const frontendDir = path.join(__dirname, '..');
  process.chdir(frontendDir);
  
  const output = execSync('npm run build', { 
    encoding: 'utf8',
    stdio: 'pipe',
    timeout: 300000 // 5 minutes
  });
  
  // Check for success indicators
  if (output.includes('Compiled successfully') || output.includes('build/static')) {
    log.success('Build completed successfully!');
    
    // Extract bundle size info if available
    const bundleSizeMatch = output.match(/File sizes after gzip:\s+([\d.]+)\s+kB/);
    if (bundleSizeMatch) {
      log.info(`Main bundle size: ${bundleSizeMatch[1]} kB (gzipped)`);
    }
    
    process.exit(0);
  } else {
    log.error('Build completed but success indicator not found');
    console.log(output);
    process.exit(1);
  }
} catch (error) {
  log.error('Build failed!');
  console.error(error.stdout || error.message);
  process.exit(1);
}

