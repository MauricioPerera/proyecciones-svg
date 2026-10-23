'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const playwright=require('playwright');
const root=path.resolve(__dirname,'..');
const browsers=(process.env.TEST_BROWSERS||'chromium,firefox').split(',');

(async()=>{
  const evidence=[];
  fs.mkdirSync(path.join(root,'build','browser-evidence'),{recursive:true});
  for(const name of browsers){
    const options={headless:true};
    if(name==='chromium'&&process.env.CHROMIUM_EXECUTABLE)options.executablePath=process.env.CHROMIUM_EXECUTABLE;
    const browser=await playwright[name].launch(options);
    try{
      for(const model of ['cuna','bloque-taladrado','cuatro-taladros']){
        const page=await browser.newPage({viewport:{width:1280,height:900}});
        const errors=[];
        page.on('pageerror',error=>errors.push(error.message));
        const base=path.join(root,'build','browser',model);
        const opened=[];
        page.on('request',request=>opened.push(request.url()));
        await page.goto(pathToFileURL(path.join(base,'visor.html')).href);
        const frames=page.locator('#rotation [data-frame]');
        assert.equal(await frames.count(),24);
        for(let index=0;index<24;index++){
          await page.locator('#frame').evaluate((node,value)=>{node.value=String(value);node.dispatchEvent(new Event('input',{bubbles:true}))},index);
          const shown=page.locator('#rotation [data-frame][visibility=visible]');
          assert.equal(await shown.count(),1);
          assert.equal(await shown.getAttribute('data-frame'),String(index));
          const expected=await shown.getAttribute('data-azimuth');
          assert.ok((await page.locator('#angle').textContent()).includes(expected+'°'));
          assert.ok(await shown.evaluate(node=>node.getBBox().width>0));
        }
        const ids=await page.locator('[id]').evaluateAll(nodes=>nodes.map(n=>n.id));
        assert.equal(ids.length,new Set(ids).size,'IDs must be unique across embedded SVGs');
        await page.locator('#hidden').uncheck();
        assert.ok(await page.locator('body').evaluate(node=>node.classList.contains('omit')));
        assert.ok(await page.locator('.hidden-edge').first().evaluate(node=>getComputedStyle(node).display==='none'));
        await page.locator('#hidden').check();
        await page.emulateMedia({reducedMotion:'reduce'});
        assert.equal(await page.locator('#play').getAttribute('aria-pressed'),'false');
        assert.notEqual(await page.locator('#rotation .viewer-frames').evaluate(n=>getComputedStyle(n).display),'none');
        await page.locator('#play').click();
        await page.waitForFunction(()=>document.getElementById('play').getAttribute('aria-pressed')==='false');
        assert.equal(await page.locator('#frame').inputValue(),'23');
        await page.setViewportSize({width:320,height:720});
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'No page overflow at 320px');
        await page.screenshot({path:path.join(root,'build','browser-evidence',name+'-'+model+'.png'),fullPage:true});
        assert.ok(opened.every(url=>url.startsWith('file:')),'Standalone viewer must make no network requests');
        assert.deepEqual(errors,[]);
        // Autonomous SVG retains its independent animation and reduced-motion fallback.
        await page.goto(pathToFileURL(path.join(base,'giro.svg')).href);
        assert.equal(await page.locator('[data-frame]').count(),24);
        assert.notEqual(await page.locator('.still-frame').evaluate(n=>getComputedStyle(n).display),'none');
        await page.emulateMedia({reducedMotion:'no-preference'});
        await page.evaluate(()=>{const svg=document.documentElement;svg.pauseAnimations();svg.setCurrentTime(.6)});
        const active=await page.locator('[data-frame]').evaluateAll(nodes=>nodes.filter(n=>getComputedStyle(n).visibility==='visible').map(n=>n.dataset.frame));
        assert.equal(active.length,1);
        assert.ok(Number(active[0])>=13&&Number(active[0])<=15);
        evidence.push({browser:name,version:browser.version(),model,angles:24,portable:true,reducedMotion:true,width320:true});
        await page.close();
      }
    }finally{await browser.close()}
  }
  fs.writeFileSync(path.join(root,'build','browser-evidence','report.json'),JSON.stringify(evidence,null,2)+'\n');
  console.log(JSON.stringify(evidence));
})().catch(error=>{console.error(error);process.exitCode=1});
