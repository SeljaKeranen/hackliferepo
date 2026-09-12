import {launch} from './browser.mjs';
import assert from 'node:assert/strict';
import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
const base=process.env.DEMO_URL||'http://localhost:5173';
const browser=await launch();const errors=[];mkdirSync('outputs',{recursive:true});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1100}});page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base,{waitUntil:'networkidle'});await page.getByRole('heading',{name:'Take the long view.'}).waitFor();
 assert.ok(await page.getByRole('button',{name:'Inspect the 90 percent human verification requirement'}).isVisible());
 await page.screenshot({path:'outputs/demo-desktop.png',fullPage:true});
 const before=await page.locator('.forecast-summary strong').first().innerText();
 await page.locator('#health').fill('1');const after=await page.locator('.forecast-summary strong').first().innerText();assert.notEqual(before,after);
 await page.getByRole('button',{name:'10 years Exploratory'}).click();await page.getByText('This ten-year value applies').waitFor();
 await page.getByRole('button',{name:'Reset ↺'}).click();assert.equal(await page.locator('#health').inputValue(),'0');
 await page.getByRole('button',{name:'Explore United States',exact:true}).press('Enter');await page.getByText('US forecast reliability is limited.').waitFor();
 await page.getByRole('tab',{name:'Policy evidence'}).click();await page.getByText('No human-approved findings in this release yet.').waitFor();
 await page.getByRole('button',{name:'funding',exact:true}).click();assert.ok((await page.url()).includes('country=US'));
 await page.getByRole('tab',{name:'Data & method'}).click();await page.getByRole('heading',{name:'What the model earned. Where it failed.'}).waitFor();
 await page.screenshot({path:'outputs/demo-methods.png',fullPage:true});
 await page.goto(base+'/explore?country=SG&horizon=10&health=1',{waitUntil:'networkidle'});assert.equal(await page.locator('#health').inputValue(),'1');assert.ok(await page.getByText('This ten-year value applies').isVisible());
 await page.pdf({path:'outputs/analyst-brief.pdf',format:'A4',printBackground:true});
 const mobile=await browser.newPage({viewport:{width:390,height:844},isMobile:true,deviceScaleFactor:1});await mobile.goto(base,{waitUntil:'networkidle'});assert.equal(await mobile.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await mobile.screenshot({path:'outputs/demo-mobile.png',fullPage:true});
 const review=await browser.newPage();const key=readFileSync('outputs/reviewer.key','utf8').trim();await review.goto(base+'/review/index.html#'+key,{waitUntil:'networkidle'});await review.locator('#workspace').waitFor({state:'visible'});assert.equal(await review.locator('.card').count(),12);
 // Exercise form persistence and export in an isolated browser. This synthetic export
 // stays in ignored outputs/ and is NEVER imported as a human verdict.
 await review.locator('#reviewer').fill('TEST FIXTURE — NOT HUMAN REVIEW');await review.locator('.card').first().locator('button.pass').first().click();
 assert.ok(await review.locator('#download-status').innerText());
 await review.reload({waitUntil:'networkidle'});await review.locator('#key').fill(key);await review.locator('#open').click();await review.locator('#workspace').waitFor({state:'visible'});assert.equal(await review.locator('.card').first().locator('button.pass.active').count(),1);
 await review.locator('#country').selectOption('united-states');assert.equal(await review.locator('.card').count(),11);
 await review.locator('#country').selectOption('singapore');assert.equal(await review.locator('.card').count(),13);
 await review.locator('#country').selectOption('sweden');
 const dl=review.waitForEvent('download');await review.locator('#download').click();const download=await dl;await download.saveAs('outputs/test-fixture-review-do-not-import.json');
 const exported=JSON.parse(readFileSync('outputs/test-fixture-review-do-not-import.json'));assert.equal(exported.verdicts['se-101'].checks.source_resolves,true);assert.equal(exported.verdicts['se-101'].reviewed,false);assert.equal(exported.history.length,0);assert.equal(exported.verdicts['se-101'].reviewer,'TEST FIXTURE — NOT HUMAN REVIEW');
 assert.equal(errors.length,0,errors.join('\n'));
 const result={base,passed:['desktop rendering','90% verification indicator','scenario update and reset','10-year label','keyboard country selection','US failure warning','policy filters and pending state','method tables','deep links','print brief','mobile overflow','encrypted reviewer unlock','isolated synthetic form export and persistence'],page_errors:errors};writeFileSync('outputs/browser-checks.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
}finally{await browser.close()}
