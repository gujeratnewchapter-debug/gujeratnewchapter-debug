# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: tests\auth.spec.ts >> signup and login flow (scaffold)
- Location: tests\auth.spec.ts:3:5

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:3001/
Call log:
  - navigating to "http://localhost:3001/", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test('signup and login flow (scaffold)', async ({ page }) => {
> 4  |   await page.goto('http://localhost:3001');
     |              ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:3001/
  5  |   // TODO: Add selectors and flow based on your app's auth UI
  6  |   // Example (update selectors to match your frontend):
  7  |   // await page.click('text=Sign up');
  8  |   // await page.fill('input[name="email"]', process.env.TEST_EMAIL || 'test@example.com');
  9  |   // await page.fill('input[name="password"]', process.env.TEST_PASSWORD || 'Passw0rd!');
  10 |   // await page.click('button[type=submit]');
  11 |   // await expect(page).toHaveURL(/dashboard/);
  12 | });
  13 | 
```