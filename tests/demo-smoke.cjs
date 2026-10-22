const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage({viewport:{width:1400,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  try{
    await page.goto('http://127.0.0.1:8765/docs/');
    await page.locator('[data-view="nuevo"]').click();
    await page.locator('#evaluate').click();
    assert.match(await page.locator('#decision').innerText(),/DOCUMENTOS PENDIENTES/);
    await page.locator('#fill').click();
    await page.locator('#evaluate').click();
    assert.match(await page.locator('#decision').innerText(),/PREAPROBADA/);
    await page.locator('[data-view="solicitudes"]').click();
    assert.equal(await page.locator('#cases tr').count(),2);
    await fs.promises.mkdir('test-results',{recursive:true});
    await page.screenshot({path:'test-results/cirugia-agil.png',fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('Cirugía Ágil: demo interactiva OK');
  } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
