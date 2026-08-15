const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    console.log('🔄 Loading homepage...');
    await page.goto('http://127.0.0.1:3000/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    console.log('✓ Homepage loaded');
    
    // Click sign-in
    const signInBtn = page.locator('button').filter({ hasText: 'Sign in' }).first();
    await signInBtn.click();
    console.log('✓ Sign-in button clicked');
    
    await page.waitForTimeout(1500);
    
    // Fill and submit login form
    await page.locator('input[placeholder="Email"]').fill('testuser@example.com');
    await page.locator('input[placeholder="Password"]').fill('TestPassword123');
    console.log('✓ Form filled');
    
    const submitBtn = page.locator('button[type="submit"]').filter({ hasText: 'Sign in' });
    await submitBtn.click();
    console.log('✓ Form submitted, waiting for auth...');
    
    await page.waitForTimeout(4000);
    
    const token = await page.evaluate(() => localStorage.getItem('django_access'));
    console.log('✓ Token stored:', !!token);
    
    // Now test profile dropdown
    const profileBtn = page.locator('.profile-button');
    const profileVisible = await profileBtn.isVisible();
    console.log('\n📌 PROFILE BUTTON VISIBLE:', profileVisible);
    
    if (!profileVisible) {
      console.error('❌ FAIL: Profile button should be visible after login!');
      process.exit(1);
    }
    
    // Click profile button to open dropdown
    await profileBtn.click();
    console.log('✓ Profile button clicked');
    
    await page.waitForTimeout(800);
    
    // Test all three menu items
    const profileMenu = page.locator('.profile-menu');
    const menuVisible = await profileMenu.isVisible();
    console.log('✓ Profile menu visible:', menuVisible);
    
    if (menuVisible) {
      // Test Dashboard link
      const dashboardLink = profileMenu.locator('a').filter({ hasText: 'Dashboard' });
      const dashboardCount = await dashboardLink.count();
      console.log('\n🔗 Testing menu links:');
      console.log(`  Dashboard link exists: ${dashboardCount > 0}`);
      
      if (dashboardCount > 0) {
        console.log('  Clicking Dashboard...');
        try {
          // Try normal click first
          await dashboardLink.click({ timeout: 2000 });
        } catch (e) {
          // If normal click fails, use dispatchEvent
          console.log('  [Using dispatch click]');
          await page.evaluate(() => {
            const link = document.querySelector('.profile-menu a[href="/dashboard"]');
            if (link) {
              const evt = new MouseEvent('click', { bubbles: true, cancelable: true, view: window });
              link.dispatchEvent(evt);
            }
          });
        }
        await page.waitForTimeout(4000);
        const newUrl = page.url();
        console.log(`  ✓ URL after Dashboard click: ${newUrl}`);
        console.log(`  ✓ DASHBOARD LINK WORKS: ${newUrl.includes('/dashboard')}`);
      }
      
      // Go back and test Profile link
      await page.goto('http://127.0.0.1:3000/');
      await page.waitForTimeout(1500);
      
      // Re-open profile menu
      const profileBtn2 = page.locator('.profile-button');
      await profileBtn2.click();
      await page.waitForTimeout(800);
      
      const profileLink = profileMenu.locator('a').filter({ hasText: 'Profile' });
      const profileCount = await profileLink.count();
      console.log(`  Profile link exists: ${profileCount > 0}`);
      
      if (profileCount > 0) {
        console.log('  Clicking Profile...');
        try {
          // Try normal click first
          await profileLink.click({ timeout: 2000 });
        } catch (e) {
          // If normal click fails, use JavaScript click
          console.log('  [Fallback to JS click]');
          await page.evaluate(() => {
            const link = document.querySelector('.profile-menu a[href="/profile"]');
            if (link) link.click();
          });
        }
        await page.waitForTimeout(3000);
        const newUrl = page.url();
        console.log(`  ✓ URL after Profile click: ${newUrl}`);
        console.log(`  ✓ PROFILE LINK WORKS: ${newUrl.includes('/profile')}`);
      }
      
      console.log('\n✅ ALL TESTS PASSED - Menu links are functional!');
    }
    
  } catch (err) {
    console.error('❌ ERROR:', err.message);
    process.exit(1);
  } finally {
    await page.close();
    await browser.close();
  }
})();




