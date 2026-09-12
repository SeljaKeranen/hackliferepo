import {launch} from './browser.mjs';
import {mkdirSync,copyFileSync,writeFileSync,readFileSync} from 'node:fs';
const base=process.env.DEMO_URL||'http://localhost:5173';mkdirSync('outputs/recording',{recursive:true});
const browser=await launch();const context=await browser.newContext({viewport:{width:1440,height:900},recordVideo:{dir:'outputs/recording',size:{width:1440,height:900}}});const page=await context.newPage();const video=page.video();const started=Date.now();
const cues=[];
async function caption(text){cues.push({seconds:Math.round((Date.now()-started)/1000),text});await page.evaluate(text=>{let el=document.getElementById('recording-caption');if(!el){el=document.createElement('div');el.id='recording-caption';el.style.cssText='position:fixed;bottom:18px;left:50%;transform:translateX(-50%);z-index:9999;background:#173f34f2;color:#eef2df;border:1px solid #9eb58380;padding:13px 24px;border-radius:8px;font:500 15px Inter,system-ui;box-shadow:0 4px 24px #0002;max-width:90vw;text-align:center;pointer-events:none';document.body.appendChild(el)}el.textContent=text},text)}
const hold=ms=>page.waitForTimeout(ms);
try{
 await page.goto(base,{waitUntil:'networkidle'});await caption('Longview: national policy evidence and population-health scenarios.');await hold(7000);
 await page.getByRole('button',{name:'Explore United States',exact:true}).click();await caption('Compare the same published World Bank indicator across three countries.');await hold(6500);
 await page.getByRole('button',{name:'Explore Singapore',exact:true}).click();await hold(4500);
 await page.getByRole('tab',{name:'Policy evidence'}).click();await page.locator('.workspace-tabs').scrollIntoViewIfNeeded();await caption('Only human-approved claims enter the public release. Pending review is explicit.');await hold(8000);
 await page.getByRole('tab',{name:'Outcomes & scenarios'}).click();await page.locator('.forecast-grid').scrollIntoViewIfNeeded();await caption('The five-year forecast uses numerical indicators, not policy labels.');await hold(7000);
 await page.locator('#pollution').fill('-20');await caption('Assume 20% lower PM2.5. This is a conditional association, not a policy effect.');await hold(8500);
 await page.getByRole('button',{name:'10 years Exploratory'}).click();await caption('Ten years is exploratory: two five-year model steps, with no ten-year validation.');await hold(7000);
 await page.getByRole('button',{name:'Reset ↺'}).click();await hold(2500);
 await page.getByRole('tab',{name:'Data & method'}).click();await page.locator('.methods').scrollIntoViewIfNeeded();await caption('Compare regression with both baselines. Country failures remain visible.');await hold(9500);
 await page.locator('.funding-lens').scrollIntoViewIfNeeded();await caption('New research lens: fundamental ageing funding, with explicit comparability limits.');await hold(7000);
 await page.getByRole('button',{name:'Inspect the 90 percent human verification requirement'}).scrollIntoViewIfNeeded();await caption('The ≥90% gate measures human evidence verification, separately from forecast error.');await hold(8000);
 await page.getByRole('tab',{name:'Outcomes & scenarios'}).click();await page.evaluate(()=>scrollTo({top:0,behavior:'instant'}));await caption('Selja · Max · Jan / Stockholm AI × Longevity Hackathon 2026');
 const remaining=92000-(Date.now()-started);if(remaining>0)await hold(remaining);
}finally{await context.close();await video.saveAs('outputs/longview-demo.webm');await browser.close();writeFileSync('outputs/recording-cues.json',JSON.stringify(cues,null,2));console.log('Recorded outputs/longview-demo.webm, approximately 90 seconds. Captions describe real interactions; no human approvals are simulated.')}
