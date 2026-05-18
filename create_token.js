const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // 去 token 页面
  await page.goto('https://github.com/settings/tokens?type=beta');
  
  // 等待用户登录
  console.log('请在浏览器中完成登录，然后告诉我');
  
  // 等待一下看是否需要登录
  await page.waitForTimeout(3000);
  
  // 检查是否已登录
  const url = page.url();
  console.log('当前 URL:', url);
  
  await browser.close();
})();