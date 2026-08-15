const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    await page.goto('http://127.0.0.1:3000/', { waitUntil: 'domcontentloaded' });
    console.log('✓ Homepage loaded');
    
    // Wait a bit for page to fully render
    await page.waitForTimeout(2000);
    
    // Look for the sign-in button
    const signInBtn = page.locator('button').filter({ hasText: 'Sign in' }).first();
    console.log('Sign-in button exists:', await signInBtn.count());
    
    if (await signInBtn.count() > 0) {
      await signInBtn.click();
      console.log('✓ Sign-in button clicked');
      
      await page.waitForTimeout(1500);
      
      // Try to find email input
      const emailInput = page.locator('input[placeholder="Email"]');
      const exists = await emailInput.count();
      console.log('Email input found:', exists);
      
      if (exists > 0) {
        await emailInput.fill('testuser@example.com');
        await page.locator('input[placeholder="Password"]').fill('TestPassword123');
        console.log('✓ Form filled');
        
        const submitBtn = page.locator('button[type="submit"]').filter({ hasText: 'Sign in' });
        await submitBtn.click();
        console.log('✓ Form submitted');
        
        await page.waitForTimeout(3000);
        console.log('PAGE_URL:', page.url());
        
        // Check for profile button
        const profileBtn = page.locator('.profile-button');
        const visible = await profileBtn.isVisible();
        console.log('✓ PROFILE_BUTTON_VISIBLE:', visible);
        
        if (visible) {
          await profileBtn.click();
          await page.waitForTimeout(800);
          const menuVisible = await page.locator('.profile-menu').isVisible();
          console.log('✓ PROFILE_MENU_VISIBLE:', menuVisible);
        }
      } else {
        console.log('ERROR: Modal did not appear');
        console.log('Page HTML snippet:', (await page.content()).substring(0, 500));
      }
    }
    
  } catch (err) {
    console.error('ERROR:', err.message);
  } finally {
    await page.close();
    await browser.close();
  }
})();

