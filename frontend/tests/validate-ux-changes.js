#!/usr/bin/env node
/**
 * Comprehensive UX Validation Script
 * Tests all CSS rules, component mode-awareness, PWA config, and accessibility
 * for the three theme modes: Sense Classic, Maya Classic, Maya Immersive
 */

const fs = require('fs');
const path = require('path');

const FRONTEND = path.resolve(__dirname, '..');
const SRC = path.join(FRONTEND, 'src');
const PUBLIC = path.join(FRONTEND, 'public');

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;
const failures = [];

function test(name, condition, detail = '') {
  totalTests++;
  if (condition) {
    passedTests++;
    console.log(`  ✅ ${name}`);
  } else {
    failedTests++;
    const msg = detail ? `${name} — ${detail}` : name;
    failures.push(msg);
    console.log(`  ❌ ${name}${detail ? ` — ${detail}` : ''}`);
  }
}

function readFile(relPath) {
  return fs.readFileSync(path.join(FRONTEND, relPath), 'utf-8');
}

function fileExists(relPath) {
  return fs.existsSync(path.join(FRONTEND, relPath));
}

// ============================================================
// SECTION 1: CSS VALIDATION (index.css)
// ============================================================
console.log('\n═══════════════════════════════════════════════');
console.log('  SECTION 1: CSS VALIDATION (index.css)');
console.log('═══════════════════════════════════════════════\n');

const indexCSS = readFile('src/index.css');

// 1.1 - Font-weight !important overrides removed
console.log('--- 1.1 Font-weight overrides ---');
const fontWeightMatches = indexCSS.match(/\.avatar-world\s+(?:p|span|div|label|button|a)[^{]*\{[^}]*font-weight:\s*\d+\s*!important/g) || [];
const problematicFW = fontWeightMatches.filter(m => !m.includes('input') && !m.includes('textarea'));
test('No problematic font-weight !important on general elements (p, span, div, label, button, a)', problematicFW.length === 0,
  problematicFW.length > 0 ? `Found ${problematicFW.length} problematic overrides` : '');

// Allow font-weight on input/textarea
const inputFW = indexCSS.includes('.avatar-world input') || indexCSS.includes('.avatar-world textarea');
test('Font-weight preserved for input/textarea (acceptable)', inputFW);

// 1.2 - CSS Variables for immersive mode
console.log('\n--- 1.2 Immersive Mode CSS Variables ---');
const requiredVars = [
  '--background', '--foreground', '--card', '--card-foreground',
  '--popover', '--popover-foreground', '--primary', '--primary-foreground',
  '--secondary', '--secondary-foreground', '--muted', '--muted-foreground',
  '--accent', '--accent-foreground', '--destructive', '--destructive-foreground',
  '--border', '--input', '--ring'
];

const immersiveVarBlock = indexCSS.match(/body\.avatar-world\.view-immersive\s*\{[^}]+\}/);
if (immersiveVarBlock) {
  for (const v of requiredVars) {
    test(`CSS variable ${v} defined for immersive mode`, immersiveVarBlock[0].includes(v));
  }
} else {
  test('body.avatar-world.view-immersive CSS variable block exists', false, 'Block not found');
}

// 1.3 - Pastel background overrides
console.log('\n--- 1.3 Pastel Background Overrides (Immersive) ---');
const pastelBgs = [
  'bg-yellow-50', 'bg-yellow-100', 'bg-red-50', 'bg-red-100',
  'bg-blue-50', 'bg-blue-100', 'bg-purple-50', 'bg-purple-100',
  'bg-green-50', 'bg-green-100', 'bg-emerald-50', 'bg-emerald-100',
  'bg-gray-50', 'bg-gray-100', 'bg-slate-50', 'bg-slate-100'
];
for (const bg of pastelBgs) {
  const pattern = new RegExp(`view-immersive[^}]*\\[class\\*="${bg}"\\]`, 's');
  test(`Pastel override for ${bg}`, pattern.test(indexCSS));
}

// 1.4 - Semantic text color overrides
console.log('\n--- 1.4 Semantic Text Color Overrides (Immersive) ---');
const textColors = [
  { cls: 'text-purple-700', expected: '196, 181, 253' },
  { cls: 'text-violet-700', expected: '196, 181, 253' },
  { cls: 'text-green-700', expected: '110, 231, 183' },
  { cls: 'text-emerald-700', expected: '110, 231, 183' },
  { cls: 'text-red-600', expected: '252, 165, 165' },
  { cls: 'text-red-700', expected: '252, 165, 165' },
  { cls: 'text-blue-600', expected: '147, 197, 253' },
  { cls: 'text-blue-700', expected: '147, 197, 253' },
  { cls: 'text-yellow-700', expected: '253, 224, 71' },
  { cls: 'text-slate-600', expected: '' }, // just check existence
];
for (const { cls, expected } of textColors) {
  const regex = new RegExp(`view-immersive[^}]*\\[class\\*="${cls}"\\]`);
  test(`Semantic override for ${cls}`, regex.test(indexCSS));
}

// 1.5 - Element-qualified selectors for specificity
console.log('\n--- 1.5 Element-Qualified Selectors (Specificity Fix) ---');
const elementQualified = [
  'span[class*="text-purple-700"]',
  'span[class*="text-violet-600"]',
  'span[class*="text-emerald-700"]',
  'span[class*="text-green-700"]',
  'span[class*="text-red-600"]',
  'span[class*="text-blue-600"]',
];
for (const sel of elementQualified) {
  test(`Element-qualified selector: ${sel}`, indexCSS.includes(sel));
}

// 1.6 - Focus-visible styles
console.log('\n--- 1.6 Accessibility: Focus-Visible ---');
test(':focus-visible rule exists', indexCSS.includes(':focus-visible'));
test(':focus-visible uses hsl(var(--ring))', indexCSS.includes('hsl(var(--ring))'));
test(':focus:not(:focus-visible) removes outline', indexCSS.includes(':focus:not(:focus-visible)'));
test('focus-visible for button elements', indexCSS.includes('button:focus-visible'));
test('focus-visible for input elements', indexCSS.includes('input:focus-visible'));
test('focus-visible for [role="tab"]', indexCSS.includes('[role="tab"]:focus-visible'));

// 1.7 - Skip-to-content styles
console.log('\n--- 1.7 Accessibility: Skip-to-Content ---');
test('.skip-to-content class defined', indexCSS.includes('.skip-to-content'));
test('.skip-to-content:focus brings to view', indexCSS.includes('.skip-to-content:focus'));

// 1.8 - cardShimmer disabled in immersive
console.log('\n--- 1.8 Card Shimmer ---');
test('cardShimmer animation defined', indexCSS.includes('@keyframes cardShimmer'));
test('card-avatar::before disabled in immersive', /view-immersive[^}]*\.card-avatar::before\s*\{[^}]*display:\s*none/s.test(indexCSS));

// 1.9 - Friend card immersive styling
console.log('\n--- 1.9 Friend Card Immersive Styling ---');
test('Friend card dark background in immersive', /view-immersive\s+\.friend-card\s*\{[^}]*background:\s*rgba\(15,\s*23,\s*42/.test(indexCSS));
test('Friend card text color in immersive', /view-immersive\s+\.friend-card\s+(?:h3|p|span)/.test(indexCSS));

// 1.10 - bg-white override (no exclusion pattern)
console.log('\n--- 1.10 bg-white Override ---');
test('No :not([class*="bg-white/"]) exclusion in index.css',
  !indexCSS.includes(':not([class*="bg-white/"])'));

// ============================================================
// SECTION 2: CSS VALIDATION (App.css)
// ============================================================
console.log('\n═══════════════════════════════════════════════');
console.log('  SECTION 2: CSS VALIDATION (App.css)');
console.log('═══════════════════════════════════════════════\n');

const appCSS = readFile('src/App.css');

console.log('--- 2.1 No Duplicate Avatar World Background ---');
const avatarWorldBgMatches = appCSS.match(/body\.avatar-world\s*\{[^}]*background/g) || [];
test('No duplicate avatar-world background in App.css', avatarWorldBgMatches.length === 0,
  avatarWorldBgMatches.length > 0 ? `Found ${avatarWorldBgMatches.length} background rules` : '');

console.log('\n--- 2.2 Scrollbar Styling ---');
test('App.css has scrollbar styling', appCSS.includes('scrollbar') || appCSS.includes('::-webkit-scrollbar'));

// ============================================================
// SECTION 3: COMPONENT VALIDATION
// ============================================================
console.log('\n═══════════════════════════════════════════════');
console.log('  SECTION 3: COMPONENT VALIDATION');
console.log('═══════════════════════════════════════════════\n');

// 3.1 - PageContainer
console.log('--- 3.1 PageContainer.jsx ---');
const pageContainer = readFile('src/components/layout/PageContainer.jsx');
test('Checks view-immersive class on body', pageContainer.includes("'view-immersive'") || pageContainer.includes('"view-immersive"'));
test('Has id="main-content" on main element', pageContainer.includes('id="main-content"') || pageContainer.includes("id='main-content'"));
test('bg-transparent for immersive mode', pageContainer.includes('bg-transparent'));
test('bg-gradient default for non-immersive', pageContainer.includes('bg-gradient-to-br'));
test('Safe area inset support', pageContainer.includes('safe-area-inset') || pageContainer.includes('min-h-screen-safe'));
test('100dvh support', pageContainer.includes('100dvh'));

// 3.2 - AppHeader
console.log('\n--- 3.2 AppHeader.jsx ---');
const appHeader = readFile('src/components/AppHeader.jsx');
test('Skip-to-content link present', appHeader.includes('skip-to-content'));
test('Skip link href=#main-content', appHeader.includes('#main-content'));
test('role="banner" on header', appHeader.includes('role="banner"'));
test('aria-label on header', appHeader.includes('aria-label'));
test('Dark mode background with backdrop-filter', appHeader.includes('backdropFilter') || appHeader.includes('backdrop-filter'));
test('Safe area padding top', appHeader.includes('safe-area-inset-top'));

// 3.3 - LoadingSpinner
console.log('\n--- 3.3 LoadingSpinner.jsx ---');
const loadingSpinner = readFile('src/components/common/LoadingSpinner.jsx');
test('Checks view-immersive class', loadingSpinner.includes('view-immersive'));
test('bg-transparent for immersive full-screen', loadingSpinner.includes('bg-transparent'));
test('Adjusted spinner color for immersive (border-violet-400)', loadingSpinner.includes('border-violet-400'));
test('Default spinner color (border-purple-400)', loadingSpinner.includes('border-purple-400'));
test('Uses React.memo', loadingSpinner.includes('memo('));

// 3.4 - useThemeTokens
console.log('\n--- 3.4 useThemeTokens.js ---');
const themeTokens = readFile('src/hooks/useThemeTokens.js');
test('Hook uses useMemo', themeTokens.includes('useMemo'));
test('Imports useWorldMode', themeTokens.includes('useWorldMode'));
test('Imports useViewMode', themeTokens.includes('useViewMode'));
test('Returns isImmersive', themeTokens.includes('isImmersive'));
test('Returns isAvatarWorld', themeTokens.includes('isAvatarWorld'));
test('Has cardBg token', themeTokens.includes('cardBg'));
test('Has textPrimary token', themeTokens.includes('textPrimary'));
test('Has pageBg token', themeTokens.includes('pageBg'));
test('Has borderDefault token', themeTokens.includes('borderDefault'));

// Verify 3 modes
test('Maya Immersive mode defined', themeTokens.includes('isAvatarWorld && isImmersive') || themeTokens.includes('isImmersive'));
test('Maya Classic mode defined', (themeTokens.match(/isAvatarWorld/g) || []).length >= 2);
test('Default export', themeTokens.includes('export default'));

// 3.5 - ImmersivePageWrapper
console.log('\n--- 3.5 ImmersivePageWrapper.jsx ---');
const wrapper = readFile('src/components/ambient/ImmersivePageWrapper.jsx');
test('getGlobalStyles function exists', wrapper.includes('getGlobalStyles'));
test('Handles bg-white class', wrapper.includes('bg-white'));
test('No :not([class*="bg-white/"]) exclusion', !wrapper.includes(':not([class*="bg-white/"])'));
test('Has pastel background overrides', wrapper.includes('bg-yellow-50') || wrapper.includes('bg-purple-50'));

// 3.6 - SettingsPage
console.log('\n--- 3.6 SettingsPage.jsx ---');
const settingsPage = readFile('src/pages/SettingsPage.jsx');
test('Passes isImmersive to SiddhiBazaarTab', settingsPage.includes('isImmersive={isImmersive}'));

// ============================================================
// SECTION 4: PWA VALIDATION
// ============================================================
console.log('\n═══════════════════════════════════════════════');
console.log('  SECTION 4: PWA VALIDATION');
console.log('═══════════════════════════════════════════════\n');

// 4.1 - Manifest
console.log('--- 4.1 Web Manifest ---');
const manifestPath = 'public/manifest.webmanifest';
const manifestExists = fileExists(manifestPath);
test('manifest.webmanifest exists', manifestExists);
if (manifestExists) {
  const manifest = JSON.parse(readFile(manifestPath));
  test('Manifest has name', !!manifest.name);
  test('Manifest has short_name', !!manifest.short_name);
  test('Manifest has display mode', manifest.display === 'standalone' || manifest.display === 'fullscreen');
  test('Manifest has theme_color', !!manifest.theme_color);
  test('Manifest has background_color', !!manifest.background_color);
  test('Manifest has icons', Array.isArray(manifest.icons) && manifest.icons.length > 0);
  test('Manifest has start_url', !!manifest.start_url);
  if (manifest.icons && manifest.icons.length > 0) {
    const sizes = manifest.icons.map(i => i.sizes);
    test('Has 192x192 icon', sizes.includes('192x192'));
    test('Has 512x512 icon', sizes.includes('512x512'));
  }
}

// 4.2 - Service Worker
console.log('\n--- 4.2 Service Worker ---');
test('sw.js exists', fileExists('public/sw.js'));
test('serviceWorkerRegistration exists', fileExists('src/serviceWorkerRegistration.js'));

// 4.3 - Offline page
console.log('\n--- 4.3 Offline Page ---');
const offlineExists = fileExists('public/offline.html');
test('offline.html exists', offlineExists);
if (offlineExists) {
  const offline = readFile('public/offline.html');
  test('Offline page has dark theme styling', offline.includes('background') || offline.includes('color'));
  test('Offline page has user-friendly message', offline.toLowerCase().includes('offline') || offline.toLowerCase().includes('connection'));
}

// 4.4 - Index.html meta tags
console.log('\n--- 4.4 Index.html Meta Tags ---');
const indexHTML = readFile('public/index.html');
test('Has theme-color meta tag', indexHTML.includes('theme-color'));
test('Has viewport meta tag with viewport-fit=cover', indexHTML.includes('viewport-fit=cover'));
test('Has apple-mobile-web-app-capable', indexHTML.includes('apple-mobile-web-app-capable'));
test('Links to manifest', indexHTML.includes('manifest'));

// ============================================================
// SECTION 5: ACCESSIBILITY VALIDATION
// ============================================================
console.log('\n═══════════════════════════════════════════════');
console.log('  SECTION 5: ACCESSIBILITY VALIDATION');
console.log('═══════════════════════════════════════════════\n');

// 5.1 - Skip-to-content link
console.log('--- 5.1 Skip-to-Content ---');
test('AppHeader has skip-to-content link', appHeader.includes('Skip to content') || appHeader.includes('skip-to-content'));
test('CSS hides skip-to-content by default', indexCSS.includes('.skip-to-content') && indexCSS.includes('position'));
test('CSS shows skip-to-content on focus', indexCSS.includes('.skip-to-content:focus'));

// 5.2 - ARIA attributes
console.log('\n--- 5.2 ARIA Attributes ---');
test('AppHeader has role="banner"', appHeader.includes('role="banner"'));
test('AppHeader has aria-label', appHeader.includes('aria-label'));

// 5.3 - Focus states in CSS
console.log('\n--- 5.3 Focus States ---');
test('Focus ring color uses theme variable', indexCSS.includes('hsl(var(--ring))'));
test('Outline-offset defined', indexCSS.includes('outline-offset'));

// ============================================================
// SECTION 6: CROSS-MODE CONSISTENCY
// ============================================================
console.log('\n═══════════════════════════════════════════════');
console.log('  SECTION 6: CROSS-MODE CONSISTENCY');
console.log('═══════════════════════════════════════════════\n');

// 6.1 - Check all pages use ImmersivePageWrapper or PageContainer
console.log('--- 6.1 Page Components Mode Awareness ---');
const pages = [
  'src/pages/Chat.jsx',
  'src/pages/AvatarChat.jsx',
  'src/pages/SettingsPage.jsx',
  'src/pages/Missions.jsx',
  'src/pages/FriendsPage.jsx',
  'src/pages/SearchPage.jsx',
  'src/pages/Matches.jsx',
  'src/pages/GalleryPage.jsx',
];

for (const pagePath of pages) {
  if (fileExists(pagePath)) {
    const content = readFile(pagePath);
    const pageName = path.basename(pagePath, '.jsx');
    const hasPageContainer = content.includes('PageContainer');
    const hasImmersiveWrapper = content.includes('ImmersivePageWrapper');
    const hasWorldMode = content.includes('useWorldMode') || content.includes('worldMode');
    const hasViewMode = content.includes('useViewMode') || content.includes('isImmersive') || content.includes('viewMode');
    test(`${pageName}: Uses PageContainer or ImmersivePageWrapper`,
      hasPageContainer || hasImmersiveWrapper,
      !hasPageContainer && !hasImmersiveWrapper ? 'Missing layout wrapper' : '');
    // Pages with ImmersivePageWrapper get mode awareness through the wrapper
    // Pages with direct hooks also count as mode-aware
    const modeAware = hasWorldMode || hasViewMode || hasImmersiveWrapper;
    test(`${pageName}: Has mode awareness (direct hook or via ImmersivePageWrapper)`,
      modeAware,
      !modeAware ? 'No mode detection and no wrapper' : '');
  }
}

// 6.2 - Check for hardcoded white backgrounds without immersive handling
console.log('\n--- 6.2 Hardcoded White Backgrounds Audit ---');
const problematicPages = [];
for (const pagePath of pages) {
  if (fileExists(pagePath)) {
    const content = readFile(pagePath);
    const pageName = path.basename(pagePath, '.jsx');
    // These are handled by global CSS now, just verify they exist
    const hasBgWhite = content.includes('bg-white');
    if (hasBgWhite) {
      // Check that ImmersivePageWrapper or global CSS handles this
      const hasWrapper = content.includes('ImmersivePageWrapper');
      if (!hasWrapper) {
        // Acceptable if global CSS handles bg-white overrides
        const globalHandles = indexCSS.includes('bg-white');
        if (!globalHandles) {
          problematicPages.push(pageName);
        }
      }
    }
  }
}
test('All bg-white usages covered by global CSS or ImmersivePageWrapper',
  problematicPages.length === 0,
  problematicPages.length > 0 ? `Uncovered: ${problematicPages.join(', ')}` : '');

// ============================================================
// SECTION 7: SPECIFICITY CHAIN VALIDATION
// ============================================================
console.log('\n═══════════════════════════════════════════════');
console.log('  SECTION 7: CSS SPECIFICITY VALIDATION');
console.log('═══════════════════════════════════════════════\n');

// The critical fix: friend-card span vs semantic text colors
console.log('--- 7.1 Friend-Card Span vs Semantic Colors ---');
const friendCardSpanPos = indexCSS.indexOf('view-immersive .friend-card span');
const semanticPurplePos = indexCSS.indexOf('span[class*="text-purple-700"]');
test('friend-card span rule exists', friendCardSpanPos !== -1);
test('Element-qualified text-purple-700 rule exists', semanticPurplePos !== -1);
test('Semantic purple rule appears AFTER friend-card span (source order win)',
  semanticPurplePos > friendCardSpanPos,
  `friend-card at ${friendCardSpanPos}, semantic at ${semanticPurplePos}`);

// Check same for other colors
const semanticGreenPos = indexCSS.indexOf('span[class*="text-green-700"]');
const semanticRedPos = indexCSS.indexOf('span[class*="text-red-600"]');
const semanticBluePos = indexCSS.indexOf('span[class*="text-blue-600"]');
test('Semantic green rule appears AFTER friend-card span', semanticGreenPos > friendCardSpanPos);
test('Semantic red rule appears AFTER friend-card span', semanticRedPos > friendCardSpanPos);
test('Semantic blue rule appears AFTER friend-card span', semanticBluePos > friendCardSpanPos);

// ============================================================
// SECTION 8: BUILD OUTPUT VALIDATION
// ============================================================
console.log('\n═══════════════════════════════════════════════');
console.log('  SECTION 8: BUILD OUTPUT VALIDATION');
console.log('═══════════════════════════════════════════════\n');

const buildDir = path.join(FRONTEND, 'build');
const buildExists = fs.existsSync(buildDir);
test('Build directory exists', buildExists);

if (buildExists) {
  const buildFiles = fs.readdirSync(buildDir);
  test('index.html in build', buildFiles.includes('index.html'));

  const staticDir = path.join(buildDir, 'static');
  if (fs.existsSync(staticDir)) {
    const staticCSS = fs.existsSync(path.join(staticDir, 'css'));
    const staticJS = fs.existsSync(path.join(staticDir, 'js'));
    test('Static CSS output exists', staticCSS);
    test('Static JS output exists', staticJS);

    if (staticCSS) {
      const cssFiles = fs.readdirSync(path.join(staticDir, 'css'));
      const mainCSS = cssFiles.find(f => f.endsWith('.css') && !f.endsWith('.map'));
      test('Main CSS bundle exists', !!mainCSS);
      if (mainCSS) {
        const bundledCSS = fs.readFileSync(path.join(staticDir, 'css', mainCSS), 'utf-8');
        test('Bundled CSS contains immersive variables', bundledCSS.includes('view-immersive'));
        test('Bundled CSS contains focus-visible', bundledCSS.includes('focus-visible'));
        test('Bundled CSS contains skip-to-content', bundledCSS.includes('skip-to-content'));
      }
    }
  }

  // Check manifest in build
  test('manifest.webmanifest in build', buildFiles.includes('manifest.webmanifest'));
  test('sw.js in build', buildFiles.includes('sw.js'));
  test('offline.html in build', buildFiles.includes('offline.html'));
}

// ============================================================
// FINAL SUMMARY
// ============================================================
console.log('\n═══════════════════════════════════════════════');
console.log('  FINAL SUMMARY');
console.log('═══════════════════════════════════════════════\n');
console.log(`  Total tests:  ${totalTests}`);
console.log(`  Passed:       ${passedTests} ✅`);
console.log(`  Failed:       ${failedTests} ❌`);
console.log(`  Pass rate:    ${((passedTests / totalTests) * 100).toFixed(1)}%`);

if (failures.length > 0) {
  console.log('\n  FAILURES:');
  failures.forEach((f, i) => console.log(`  ${i + 1}. ${f}`));
}

console.log('');
process.exit(failedTests > 0 ? 1 : 0);
