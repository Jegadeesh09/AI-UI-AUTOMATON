const { test, expect } = require('@playwright/test');

test('Verify Dashboard and Delete Modal', async ({ page }) => {
  await page.goto('http://localhost:5175/');

  // 1. Dashboard Tab
  console.log('Switching to Dashboard Tab');
  await page.click('text=Dashboard');
  await page.waitForTimeout(2000); // Wait for charts to animate
  await page.screenshot({ path: 'dashboard_new.png', fullPage: true });

  // 2. Technical View (Drill down)
  console.log('Switching to Technical View');
  await page.click('text=Technical View');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: 'dashboard_technical.png', fullPage: true });

  // 3. AI Intelligence View
  console.log('Switching to AI Intelligence');
  await page.click('text=AI Intelligence');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: 'dashboard_ai.png', fullPage: true });

  // 4. Delete Modal
  console.log('Checking Delete Modal');
  await page.click('text=Scripts & Execution');
  // Find a delete button (Trash2 icon usually translates to a button)
  // Let's look for the title="Delete Script" button
  const deleteBtn = page.locator('button[title="Delete Script"]').first();
  if (await deleteBtn.isVisible()) {
      await deleteBtn.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: 'delete_modal.png' });
  } else {
      console.log('No delete button found on Scripts tab');
  }
});
