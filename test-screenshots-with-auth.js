/**
 * Screenshot Testing Script with Authentication
 * 
 * This script opens a visible browser, waits for manual login, then captures screenshots.
 * 
 * Prerequisites:
 * npm install -D playwright
 * npx playwright install chromium
 * 
 * Run with: node test-screenshots-with-auth.js
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');
const BASE_URL = 'http://localhost:3000';

// Ensure screenshots directory exists
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function askQuestion(question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer);
    });
  });
}

async function captureScreenshot(page, name, description) {
  const filename = `${name}.png`;
  const filepath = path.join(SCREENSHOTS_DIR, filename);
  
  console.log(`\n📸 Capturing: ${description}`);
  console.log(`   Filename: ${filename}`);
  
  // Wait a bit for animations to settle
  await page.waitForTimeout(1500);
  
  await page.screenshot({ 
    path: filepath, 
    fullPage: true 
  });
  
  console.log(`   ✅ Saved to: ${filepath}`);
}

async function clickToggle(page, toggleText, description) {
  console.log(`\n🔄 ${description}`);
  
  try {
    // Try to find the toggle button with exact text match
    const button = page.locator(`button`).filter({ hasText: toggleText }).first();
    await button.waitFor({ state: 'visible', timeout: 3000 });
    await button.click();
    console.log(`   ✅ Clicked: ${toggleText}`);
    
    // Wait for transition
    await page.waitForTimeout(800);
    return true;
  } catch (error) {
    console.log(`   ⚠️  Toggle "${toggleText}" not found - ${error.message}`);
    return false;
  }
}

async function navigateAndCapture(page, url, name, description) {
  console.log(`\n🔗 Navigating to: ${url}`);
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(1000); // Extra wait for content to load
    await captureScreenshot(page, name, description);
    return true;
  } catch (error) {
    console.error(`   ❌ Error: ${error.message}`);
    return false;
  }
}

async function main() {
  console.log('🚀 Screenshot Capture Test with Authentication');
  console.log(`📁 Screenshots will be saved to: ${SCREENSHOTS_DIR}\n`);
  
  const browser = await chromium.launch({ 
    headless: false,  // VISIBLE browser for login
    slowMo: 50 
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
  });
  
  const page = await context.newPage();
  
  try {
    // Step 1: Navigate to home page and check for authentication
    console.log('\n========================================');
    console.log('STEP 1: Navigate and Check Authentication');
    console.log('========================================');
    
    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    
    // Check if we're on the landing page
    const landingPageHeading = await page.locator('text=Your Memory Lives On').count();
    const hasAppHeader = await page.locator('header').count();
    
    if (landingPageHeading > 0 || hasAppHeader === 0) {
      console.log('\n⚠️  Not logged in. The browser window is now open.');
      console.log('📝 Please log in manually in the browser window.');
      console.log('   1. Click "Get Started For Free" or navigate to the login page');
      console.log('   2. Log in with your credentials');
      console.log('   3. Wait until you see the home feed');
      
      await askQuestion('\nPress ENTER when you are logged in and can see the home feed...');
      
      // Refresh to ensure we're on the right page
      await page.goto(`${BASE_URL}/home`, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
    }
    
    // Verify we have a header now
    const headerCheck = await page.locator('header').count();
    if (headerCheck === 0) {
      console.log('\n❌ Still not seeing the application header. Please ensure you are logged in.');
      await askQuestion('Press ENTER to continue anyway...');
    }
    
    // Step 2: Capture initial state
    console.log('\n========================================');
    console.log('STEP 2: Capture Initial State');
    console.log('========================================');
    await captureScreenshot(page, '01-initial-authenticated', 'Initial Authenticated View');
    
    // Step 3: Determine current world mode
    console.log('\n========================================');
    console.log('STEP 3: Check Current World Mode');
    console.log('========================================');
    
    const hasSenseButton = await page.locator('button:has-text("Sense")').count() > 0;
    const hasMayaButton = await page.locator('button:has-text("Maya")').count() > 0;
    
    let currentWorld = 'unknown';
    if (hasSenseButton) {
      currentWorld = 'sense';
      console.log('   Current world: SENSE');
    } else if (hasMayaButton) {
      currentWorld = 'maya';
      console.log('   Current world: MAYA');
    }
    
    // Step 4: Capture both worlds in Classic mode
    console.log('\n========================================');
    console.log('STEP 4: Capture Both Worlds - Classic Mode');
    console.log('========================================');
    
    if (currentWorld === 'sense') {
      await captureScreenshot(page, '02-sense-classic', 'Sense World - Classic Mode');
      
      // Switch to Maya
      await clickToggle(page, 'Sense', 'Switching to Maya World');
      await captureScreenshot(page, '03-maya-classic', 'Maya World - Classic Mode');
    } else if (currentWorld === 'maya') {
      await captureScreenshot(page, '03-maya-classic', 'Maya World - Classic Mode');
      
      // Switch to Sense
      await clickToggle(page, 'Maya', 'Switching to Sense World');
      await captureScreenshot(page, '02-sense-classic', 'Sense World - Classic Mode');
      
      // Switch back to Maya
      await clickToggle(page, 'Sense', 'Switching back to Maya World');
    }
    
    // Step 5: Switch to Immersive mode (only available in Maya world)
    console.log('\n========================================');
    console.log('STEP 5: Switch to Immersive Mode');
    console.log('========================================');
    
    const hasClassicButton = await page.locator('button:has-text("Classic")').count() > 0;
    const hasImmersiveButton = await page.locator('button:has-text("Immersive")').count() > 0;
    
    if (hasClassicButton) {
      await clickToggle(page, 'Classic', 'Switching to Immersive Mode');
      await captureScreenshot(page, '04-maya-immersive', 'Maya World - Immersive Mode');
    } else if (hasImmersiveButton) {
      console.log('   Already in Immersive mode');
      await captureScreenshot(page, '04-maya-immersive', 'Maya World - Immersive Mode');
    } else {
      console.log('   ⚠️  View mode toggle not found. Are we in Maya world?');
    }
    
    // Step 6: Capture all pages in Immersive mode
    console.log('\n========================================');
    console.log('STEP 6: Capture All Pages (Maya Immersive)');
    console.log('========================================');
    
    const pages = [
      { url: '/home', name: '05-home-immersive', desc: 'Home Page (Immersive)' },
      { url: '/friends', name: '06-friends-immersive', desc: 'Friends Page (Immersive)' },
      { url: '/search', name: '07-search-immersive', desc: 'Search Page (Immersive)' },
      { url: '/settings', name: '08-settings-immersive', desc: 'Settings Page (Immersive)' },
      { url: '/gallery', name: '09-gallery-immersive', desc: 'Gallery Page (Immersive)' },
      { url: '/myprofile', name: '10-myprofile-immersive', desc: 'My Profile (Immersive)' },
      { url: '/missions', name: '11-missions-immersive', desc: 'Missions Page (Immersive)' },
      { url: '/matches', name: '12-matches-immersive', desc: 'Matches Page (Immersive)' },
      { url: '/integrations', name: '13-integrations-immersive', desc: 'Integrations (Immersive)' },
      { url: '/avatar-visualization', name: '14-avatar-viz-immersive', desc: 'Avatar Viz (Immersive)' },
      { url: '/avatar-control', name: '15-avatar-control-immersive', desc: 'Avatar Control (Immersive)' },
    ];
    
    for (const pageInfo of pages) {
      await navigateAndCapture(
        page,
        `${BASE_URL}${pageInfo.url}`,
        pageInfo.name,
        pageInfo.desc
      );
    }
    
    // Step 7: Switch back to Classic mode
    console.log('\n========================================');
    console.log('STEP 7: Switch Back to Classic Mode');
    console.log('========================================');
    
    await page.goto(`${BASE_URL}/home`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    
    const immersiveToggle = await page.locator('button:has-text("Immersive")').count() > 0;
    if (immersiveToggle) {
      await clickToggle(page, 'Immersive', 'Switching back to Classic Mode');
      await captureScreenshot(page, '16-maya-classic-return', 'Back to Maya Classic');
    }
    
    // Step 8: Capture key pages in Classic mode
    console.log('\n========================================');
    console.log('STEP 8: Capture Key Pages (Maya Classic)');
    console.log('========================================');
    
    const classicPages = [
      { url: '/home', name: '17-home-classic', desc: 'Home Page (Classic)' },
      { url: '/friends', name: '18-friends-classic', desc: 'Friends Page (Classic)' },
      { url: '/myprofile', name: '19-myprofile-classic', desc: 'My Profile (Classic)' },
    ];
    
    for (const pageInfo of classicPages) {
      await navigateAndCapture(
        page,
        `${BASE_URL}${pageInfo.url}`,
        pageInfo.name,
        pageInfo.desc
      );
    }
    
    console.log('\n========================================');
    console.log('✅ Screenshot capture complete!');
    console.log(`📁 All screenshots saved to: ${SCREENSHOTS_DIR}`);
    console.log('========================================\n');
    
    // List all captured screenshots
    console.log('📋 Captured screenshots:');
    const files = fs.readdirSync(SCREENSHOTS_DIR).filter(f => f.endsWith('.png')).sort();
    files.forEach(file => {
      const stats = fs.statSync(path.join(SCREENSHOTS_DIR, file));
      const sizeMB = (stats.size / 1024 / 1024).toFixed(2);
      console.log(`   - ${file} (${sizeMB} MB)`);
    });
    
  } catch (error) {
    console.error('\n❌ Error during screenshot capture:', error);
    throw error;
  } finally {
    rl.close();
    await browser.close();
  }
}

// Run the script
main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
