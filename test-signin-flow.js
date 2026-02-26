/**
 * Sign-In Flow Testing Script
 * 
 * This script navigates to the app and attempts to click through the sign-in flow
 * to see what authentication method is used.
 * 
 * Run with: node test-signin-flow.js
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
  
  console.log(`\n📸 ${description}`);
  console.log(`   Saved: ${filename}`);
  
  await page.waitForTimeout(1000);
  await page.screenshot({ 
    path: filepath, 
    fullPage: true 
  });
  
  return filepath;
}

async function main() {
  console.log('🔐 Testing Sign-In Flow');
  console.log(`📁 Screenshots: ${SCREENSHOTS_DIR}\n`);
  
  const browser = await chromium.launch({ 
    headless: false,  // Visible browser
    slowMo: 100 
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
  });
  
  const page = await context.newPage();
  
  try {
    // Step 1: Navigate to home
    console.log('\n========================================');
    console.log('STEP 1: Load Landing Page');
    console.log('========================================');
    
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 15000 });
    await captureScreenshot(page, 'signin-01-landing', 'Landing page loaded');
    
    console.log('✅ Page URL:', page.url());
    console.log('✅ Page title:', await page.title());
    
    // Step 2: Look for Sign In button
    console.log('\n========================================');
    console.log('STEP 2: Look for Sign-In Button');
    console.log('========================================');
    
    // Try multiple selectors for sign-in button
    const signInSelectors = [
      'button:has-text("Sign In")',
      'a:has-text("Sign In")',
      'button:has-text("Get Started")',
      'a:has-text("Get Started")',
      'button:has-text("Login")',
      '[data-testid="sign-in"]',
      '.sign-in-button',
      '#sign-in'
    ];
    
    let signInButton = null;
    let usedSelector = null;
    
    for (const selector of signInSelectors) {
      try {
        const button = page.locator(selector).first();
        const count = await button.count();
        if (count > 0) {
          signInButton = button;
          usedSelector = selector;
          console.log(`✅ Found button with selector: ${selector}`);
          break;
        }
      } catch (e) {
        // Continue to next selector
      }
    }
    
    if (!signInButton) {
      console.log('❌ No sign-in button found with known selectors');
      console.log('📸 Capturing current page for manual inspection');
      await captureScreenshot(page, 'signin-02-no-button-found', 'No sign-in button found');
      
      // Try to find all buttons on the page
      const allButtons = await page.locator('button, a[href*="login"], a[href*="signin"]').all();
      console.log(`\nFound ${allButtons.length} clickable elements on page`);
      
      for (let i = 0; i < Math.min(allButtons.length, 10); i++) {
        const text = await allButtons[i].textContent();
        const tag = await allButtons[i].evaluate(el => el.tagName);
        console.log(`  ${i + 1}. <${tag}>: "${text?.trim()}"`);
      }
      
      return;
    }
    
    // Step 3: Click the sign-in button
    console.log('\n========================================');
    console.log('STEP 3: Click Sign-In Button');
    console.log('========================================');
    
    console.log(`🖱️  Clicking: ${usedSelector}`);
    
    // Listen for popup windows (Google OAuth often opens popup)
    const popupPromise = context.waitForEvent('page', { timeout: 5000 }).catch(() => null);
    
    await signInButton.click();
    await page.waitForTimeout(2000);
    
    // Check for popup
    const popup = await popupPromise;
    
    if (popup) {
      console.log('\n🪟 Popup window detected!');
      console.log('   Popup URL:', popup.url());
      await captureScreenshot(popup, 'signin-03-popup-oauth', 'OAuth popup window');
      
      // Check if it's Google OAuth
      if (popup.url().includes('accounts.google.com')) {
        console.log('✅ Google OAuth detected');
        console.log('   This is the Google sign-in page');
        
        // Try to find what's on the Google page
        await popup.waitForTimeout(1000);
        const googleTitle = await popup.title();
        console.log('   Google page title:', googleTitle);
        
        // Look for email input
        const emailInput = await popup.locator('input[type="email"]').count();
        if (emailInput > 0) {
          console.log('   ✅ Email input field found');
          console.log('   📝 Google wants email address for authentication');
        }
      } else {
        console.log('⚠️  Non-Google popup detected');
        console.log('   Popup title:', await popup.title());
      }
      
      await popup.close();
    } else {
      console.log('\n📄 No popup - checking main page');
      
      // Wait for navigation or content change
      await page.waitForTimeout(2000);
      
      const newUrl = page.url();
      console.log('   Current URL:', newUrl);
      
      await captureScreenshot(page, 'signin-03-after-click', 'After clicking sign-in');
      
      // Check what we see now
      if (newUrl.includes('google.com')) {
        console.log('✅ Redirected to Google OAuth');
        console.log('   Page title:', await page.title());
        
        const emailInput = await page.locator('input[type="email"]').count();
        if (emailInput > 0) {
          console.log('   ✅ Email input field found');
          console.log('   📝 Google wants email address');
        }
      } else if (newUrl !== BASE_URL) {
        console.log('⚠️  Navigated to different page:', newUrl);
        console.log('   Page title:', await page.title());
      } else {
        console.log('⚠️  Still on same page');
        
        // Check for modal or dialog
        const dialog = await page.locator('[role="dialog"], .modal, [data-radix-dialog-content]').count();
        if (dialog > 0) {
          console.log('   ✅ Modal/dialog appeared on page');
          await captureScreenshot(page, 'signin-04-modal', 'Modal dialog appeared');
        }
      }
    }
    
    // Step 4: Summary
    console.log('\n========================================');
    console.log('SUMMARY');
    console.log('========================================');
    console.log('Final URL:', page.url());
    console.log('Authentication Method:', popup ? 'Popup-based OAuth' : 'Redirect-based or Modal');
    
    if (page.url().includes('google.com') || (popup && popup.url().includes('google.com'))) {
      console.log('\n✅ Google OAuth Authentication Confirmed');
      console.log('   - Users must sign in with Google account');
      console.log('   - No way to bypass without valid Google credentials');
      console.log('   - For testing, need a valid Google account login');
    }
    
    console.log('\n💡 Recommendation:');
    console.log('   1. Use a test Google account to log in');
    console.log('   2. Complete OAuth flow manually in the browser');
    console.log('   3. Then run test-screenshots-with-auth.js');
    console.log('   4. Or set up test credentials in backend');
    
  } catch (error) {
    console.error('\n❌ Error during sign-in flow test:', error.message);
    await captureScreenshot(page, 'signin-error', 'Error state');
  } finally {
    console.log('\n✅ Test complete. Browser will close in 5 seconds...');
    await page.waitForTimeout(5000);
    await browser.close();
  }
}

// Run the script
main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
