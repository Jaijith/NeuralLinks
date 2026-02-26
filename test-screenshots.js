/**
 * Screenshot Testing Script
 * 
 * This script navigates through the NeuralLinks app and captures screenshots
 * of different pages and view modes.
 * 
 * Prerequisites:
 * npm install -D playwright
 * npx playwright install chromium
 * 
 * Run with: node test-screenshots.js
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');
const BASE_URL = 'http://localhost:3000';

// Ensure screenshots directory exists
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

async function captureScreenshot(page, name, description) {
  const filename = `${name}.png`;
  const filepath = path.join(SCREENSHOTS_DIR, filename);
  
  console.log(`\n📸 Capturing: ${description}`);
  console.log(`   Filename: ${filename}`);
  
  // Wait a bit for animations to settle
  await page.waitForTimeout(1000);
  
  await page.screenshot({ 
    path: filepath, 
    fullPage: true 
  });
  
  console.log(`   ✅ Saved to: ${filepath}`);
}

async function clickToggle(page, toggleText) {
  console.log(`\n🔄 Clicking toggle: ${toggleText}`);
  
  // Find and click the toggle button
  const button = page.locator(`button:has-text("${toggleText}")`).first();
  await button.waitFor({ state: 'visible', timeout: 5000 });
  await button.click();
  
  // Wait for transition
  await page.waitForTimeout(500);
}

async function navigateAndCapture(page, url, name, description) {
  console.log(`\n🔗 Navigating to: ${url}`);
  await page.goto(url, { waitUntil: 'networkidle', timeout: 10000 });
  await captureScreenshot(page, name, description);
}

async function main() {
  console.log('🚀 Starting Screenshot Capture Test');
  console.log(`📁 Screenshots will be saved to: ${SCREENSHOTS_DIR}\n`);
  
  const browser = await chromium.launch({ 
    headless: false,  // Set to true for headless mode
    slowMo: 100 
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
  });
  
  const page = await context.newPage();
  
  try {
    // Step 1: Navigate to home page
    console.log('\n========================================');
    console.log('STEP 1: Initial Load');
    console.log('========================================');
    await navigateAndCapture(
      page, 
      BASE_URL, 
      '01-initial-load', 
      'Initial page load'
    );
    
    // Check if we're logged in by looking for header elements
    const hasHeader = await page.locator('header').count() > 0;
    
    if (!hasHeader) {
      console.log('\n⚠️  Not logged in. Please log in manually and run the script again.');
      await page.pause(); // Allows manual intervention
    }
    
    // Step 2: Capture default state (likely Sense + Classic)
    console.log('\n========================================');
    console.log('STEP 2: Default State (Sense World)');
    console.log('========================================');
    await captureScreenshot(page, '02-sense-classic', 'Sense World - Classic Mode');
    
    // Step 3: Switch to Maya world
    console.log('\n========================================');
    console.log('STEP 3: Switch to Maya World');
    console.log('========================================');
    
    // Check if we're in Sense mode, then click to switch to Maya
    const senseButton = page.locator('button:has-text("Sense")').first();
    const mayaButton = page.locator('button:has-text("Maya")').first();
    
    if (await senseButton.count() > 0) {
      await clickToggle(page, 'Sense');
      await captureScreenshot(page, '03-maya-classic', 'Maya World - Classic Mode');
    } else if (await mayaButton.count() > 0) {
      console.log('   Already in Maya world');
      await captureScreenshot(page, '03-maya-classic', 'Maya World - Classic Mode');
    }
    
    // Step 4: Switch to Immersive mode (only available in Maya world)
    console.log('\n========================================');
    console.log('STEP 4: Switch to Immersive Mode');
    console.log('========================================');
    
    const classicButton = page.locator('button:has-text("Classic")').first();
    const immersiveButton = page.locator('button:has-text("Immersive")').first();
    
    if (await classicButton.count() > 0) {
      await clickToggle(page, 'Classic');
      await captureScreenshot(page, '04-maya-immersive', 'Maya World - Immersive Mode');
    } else if (await immersiveButton.count() > 0) {
      console.log('   Already in Immersive mode');
      await captureScreenshot(page, '04-maya-immersive', 'Maya World - Immersive Mode');
    }
    
    // Step 5: Navigate through all pages (stay in Maya Immersive)
    console.log('\n========================================');
    console.log('STEP 5: Capturing All Pages');
    console.log('========================================');
    
    const pages = [
      { url: '/home', name: '05-home', desc: 'Home Page' },
      { url: '/friends', name: '06-friends', desc: 'Friends Page' },
      { url: '/search', name: '07-search', desc: 'Search Page' },
      { url: '/settings', name: '08-settings', desc: 'Settings Page' },
      { url: '/gallery', name: '09-gallery', desc: 'Gallery Page' },
      { url: '/myprofile', name: '10-myprofile', desc: 'My Profile Page' },
      { url: '/missions', name: '11-missions', desc: 'Missions Page' },
      { url: '/matches', name: '12-matches', desc: 'Matches Page' },
      { url: '/integrations', name: '13-integrations', desc: 'Integrations Page' },
      { url: '/avatar-visualization', name: '14-avatar-viz', desc: 'Avatar Visualization Page' },
      { url: '/avatar-control', name: '15-avatar-control', desc: 'Avatar Control Page' },
    ];
    
    for (const pageInfo of pages) {
      try {
        await navigateAndCapture(
          page,
          `${BASE_URL}${pageInfo.url}`,
          pageInfo.name,
          pageInfo.desc
        );
      } catch (error) {
        console.error(`   ❌ Error capturing ${pageInfo.name}:`, error.message);
      }
    }
    
    // Step 6: Switch back to Classic mode for comparison
    console.log('\n========================================');
    console.log('STEP 6: Back to Classic Mode');
    console.log('========================================');
    
    await page.goto(`${BASE_URL}/home`, { waitUntil: 'networkidle' });
    
    const immersiveToggle = page.locator('button:has-text("Immersive")').first();
    if (await immersiveToggle.count() > 0) {
      await clickToggle(page, 'Immersive');
      await captureScreenshot(page, '16-back-to-classic', 'Back to Classic Mode');
    }
    
    // Step 7: Switch to Sense world
    console.log('\n========================================');
    console.log('STEP 7: Back to Sense World');
    console.log('========================================');
    
    const mayaToggle = page.locator('button:has-text("Maya")').first();
    if (await mayaToggle.count() > 0) {
      await clickToggle(page, 'Maya');
      await captureScreenshot(page, '17-back-to-sense', 'Back to Sense World');
    }
    
    console.log('\n========================================');
    console.log('✅ Screenshot capture complete!');
    console.log(`📁 All screenshots saved to: ${SCREENSHOTS_DIR}`);
    console.log('========================================\n');
    
  } catch (error) {
    console.error('\n❌ Error during screenshot capture:', error);
    throw error;
  } finally {
    await browser.close();
  }
}

// Run the script
main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
