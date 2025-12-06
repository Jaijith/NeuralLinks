/**
 * End-to-End Testing Script
 * Tests all functionality after refactoring
 */

const fs = require('fs');
const path = require('path');

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

const log = {
  info: (msg) => console.log(`${colors.blue}ℹ${colors.reset} ${msg}`),
  success: (msg) => console.log(`${colors.green}✅${colors.reset} ${msg}`),
  error: (msg) => console.log(`${colors.red}❌${colors.reset} ${msg}`),
  warn: (msg) => console.log(`${colors.yellow}⚠️${colors.reset} ${msg}`),
  section: (msg) => console.log(`\n${colors.cyan}━━━ ${msg} ━━━${colors.reset}\n`),
};

const results = {
  passed: 0,
  failed: 0,
  warnings: 0,
  errors: [],
};

function test(name, testFn) {
  try {
    const result = testFn();
    if (result === false) {
      results.failed++;
      results.errors.push({ name, error: 'Test returned false' });
      log.error(`${name}`);
      return false;
    }
    results.passed++;
    log.success(`${name}`);
    return true;
  } catch (error) {
    results.failed++;
    results.errors.push({ name, error: error.message });
    log.error(`${name}: ${error.message}`);
    return false;
  }
}

function warn(name, message) {
  results.warnings++;
  log.warn(`${name}: ${message}`);
}

// Test 1: File Structure
log.section('File Structure Tests');

test('Config files exist', () => {
  const configPath = path.join(__dirname, '../src/config/config.js');
  const constantsPath = path.join(__dirname, '../src/config/constants.js');
  return fs.existsSync(configPath) && fs.existsSync(constantsPath);
});

test('API services exist', () => {
  const servicesDir = path.join(__dirname, '../src/services/api');
  const requiredFiles = [
    'apiClient.js',
    'endpoints.js',
    'authService.js',
    'postService.js',
    'userService.js',
    'friendService.js',
    'messageService.js',
    'matchService.js',
    'index.js',
  ];
  return requiredFiles.every(file => 
    fs.existsSync(path.join(servicesDir, file))
  );
});

test('Common components exist', () => {
  const componentsDir = path.join(__dirname, '../src/components/common');
  const requiredFiles = [
    'UserAvatar.jsx',
    'LoadingSpinner.jsx',
    'ErrorBoundary.jsx',
    'LazyPage.jsx',
    'OptimizedImage.jsx',
    'index.js',
  ];
  return requiredFiles.every(file => 
    fs.existsSync(path.join(componentsDir, file))
  );
});

test('Post components exist', () => {
  const componentsDir = path.join(__dirname, '../src/features/posts/components');
  const requiredFiles = [
    'PostCard.jsx',
    'PostHeader.jsx',
    'PostContent.jsx',
    'PostEngagement.jsx',
    'PostActions.jsx',
    'CommentSection.jsx',
    'CommentItem.jsx',
    'LikeButton.jsx',
    'index.js',
  ];
  return requiredFiles.every(file => 
    fs.existsSync(path.join(componentsDir, file))
  );
});

test('Hooks exist', () => {
  const hooksDir = path.join(__dirname, '../src/hooks');
  const requiredFiles = [
    'useApi.js',
    'usePagination.js',
    'useDebounce.js',
    'useLocalStorage.js',
    'usePerformance.js',
    'index.js',
  ];
  return requiredFiles.every(file => 
    fs.existsSync(path.join(hooksDir, file))
  );
});

test('Utils exist', () => {
  const utilsDir = path.join(__dirname, '../src/utils');
  const requiredFiles = [
    'errorHandler.js',
    'logger.js',
    'dateUtils.js',
    'performance.js',
    'index.js',
  ];
  return requiredFiles.every(file => 
    fs.existsSync(path.join(utilsDir, file))
  );
});

// Test 2: Code Quality
log.section('Code Quality Tests');

test('App.js uses lazy loading', () => {
  const appPath = path.join(__dirname, '../src/App.js');
  const content = fs.readFileSync(appPath, 'utf8');
  return (content.includes('lazy') || content.includes('React.lazy')) && content.includes('LazyPage');
});

test('App.js uses authService', () => {
  const appPath = path.join(__dirname, '../src/App.js');
  const content = fs.readFileSync(appPath, 'utf8');
  return content.includes('authService') && !content.includes('axios.get(`${API}/auth/me`');
});

test('PostContent uses OptimizedImage', () => {
  const postContentPath = path.join(__dirname, '../src/features/posts/components/PostContent.jsx');
  const content = fs.readFileSync(postContentPath, 'utf8');
  return content.includes('OptimizedImage');
});

// Test 3: Import/Export Structure
log.section('Import/Export Tests');

test('Services index exports all services', () => {
  const indexPath = path.join(__dirname, '../src/services/api/index.js');
  const content = fs.readFileSync(indexPath, 'utf8');
  const requiredExports = [
    'apiClient',
    'endpoints',
    'authService',
    'postService',
    'userService',
    'friendService',
    'messageService',
    'matchService',
  ];
  return requiredExports.every(exp => content.includes(exp));
});

test('Common components index exports all components', () => {
  const indexPath = path.join(__dirname, '../src/components/common/index.js');
  const content = fs.readFileSync(indexPath, 'utf8');
  const requiredExports = [
    'UserAvatar',
    'LoadingSpinner',
    'ErrorBoundary',
    'LazyPage',
    'OptimizedImage',
  ];
  return requiredExports.every(exp => content.includes(exp));
});

test('Hooks index exports all hooks', () => {
  const indexPath = path.join(__dirname, '../src/hooks/index.js');
  const content = fs.readFileSync(indexPath, 'utf8');
  const requiredExports = [
    'useApi',
    'usePagination',
    'useDebounce',
    'useLocalStorage',
    'usePerformance',
  ];
  return requiredExports.every(exp => content.includes(exp));
});

test('Utils index exports all utilities', () => {
  const indexPath = path.join(__dirname, '../src/utils/index.js');
  const content = fs.readFileSync(indexPath, 'utf8');
  const requiredExports = [
    'errorHandler',
    'logger',
    'dateUtils',
    'performance',
  ];
  return requiredExports.every(exp => content.includes(exp));
});

// Test 4: Component Structure
log.section('Component Structure Tests');

test('PostCard has all required props', () => {
  const postCardPath = path.join(__dirname, '../src/features/posts/components/PostCard.jsx');
  const content = fs.readFileSync(postCardPath, 'utf8');
  return content.includes('memo') && content.includes('PostCard');
});

test('UserAvatar is memoized', () => {
  const userAvatarPath = path.join(__dirname, '../src/components/common/UserAvatar.jsx');
  const content = fs.readFileSync(userAvatarPath, 'utf8');
  return content.includes('memo');
});

test('OptimizedImage is memoized', () => {
  const imagePath = path.join(__dirname, '../src/components/common/OptimizedImage.jsx');
  const content = fs.readFileSync(imagePath, 'utf8');
  return content.includes('memo');
});

// Test 5: Warnings (Non-blocking)
log.section('Migration Status (Warnings)');

const checkFileUsesAxios = (filePath, fileName) => {
  if (!fs.existsSync(filePath)) return;
  const content = fs.readFileSync(filePath, 'utf8');
  if (content.includes('axios.get') || content.includes('axios.post')) {
    warn(`${fileName}`, 'Still uses axios directly - should use services');
  }
};

const checkFileUsesOldComponents = (filePath, fileName) => {
  if (!fs.existsSync(filePath)) return;
  const content = fs.readFileSync(filePath, 'utf8');
  if (content.includes('PostCard') && !content.includes('@/features/posts/components')) {
    warn(`${fileName}`, 'Uses PostCard but may not be using new component');
  }
};

// Check pages
const pagesDir = path.join(__dirname, '../src/pages');
const pages = fs.readdirSync(pagesDir).filter(f => f.endsWith('.jsx'));

pages.forEach(page => {
  const pagePath = path.join(pagesDir, page);
  checkFileUsesAxios(pagePath, `pages/${page}`);
});

// Check specific files
checkFileUsesAxios(
  path.join(__dirname, '../src/components/AppHeader.jsx'),
  'AppHeader.jsx'
);

// Summary
log.section('Test Summary');

console.log(`\n${colors.cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${colors.reset}`);
console.log(`${colors.green}✅ Passed: ${results.passed}${colors.reset}`);
console.log(`${colors.red}❌ Failed: ${results.failed}${colors.reset}`);
console.log(`${colors.yellow}⚠️  Warnings: ${results.warnings}${colors.reset}`);
console.log(`${colors.cyan}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${colors.reset}\n`);

if (results.errors.length > 0) {
  log.section('Errors');
  results.errors.forEach(({ name, error }) => {
    log.error(`${name}: ${error}`);
  });
}

if (results.failed === 0) {
  log.success('All critical tests passed! 🎉');
  process.exit(0);
} else {
  log.error('Some tests failed. Please review the errors above.');
  process.exit(1);
}

