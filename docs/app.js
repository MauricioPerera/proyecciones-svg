'use strict';
(() => {
  const models={
    cuna:{name:'La cuña',detail:'Una rampa sencilla: 6 × 4 × 3 cm.',dimensions:'6 × 4 × 3 cm',alt:'una cuña'},
    escalon:{name:'El escalón',detail:'Un rebaje que atraviesa toda la profundidad.',dimensions:'6 × 4 × 4 cm',alt:'una pieza escalonada'},
    taladro:{name:'Un taladro',detail:'Un bloque con un agujero cilíndrico vertical y pasante.',dimensions:'8 × 6 × 2 cm · Ø 3 cm',alt:'un bloque con taladro'},
    irregular:{name:'Cuatro conductos',detail:'Una cubierta inclinada y cuatro taladros que se cruzan dentro.',dimensions:'85 × 64 × 36,52 mm · Ø 12 / 9 / 6 / 4 mm',alt:'una pieza irregular con cuatro conductos'}
  };
  const prompts={
    simple:'Usa $proyecciones-svg para dibujar una cuña de 6 cm de ancho, 4 cm de profundidad y 3 cm de alto. Muéstrame el alzado, la planta, el perfil derecho y un giro SVG.',
    sketch:'Usa $proyecciones-svg con el croquis que adjunto. Identifica las medidas dadas y pregúntame por los datos que cambien la forma. Genera las tres vistas y un giro SVG, dejando claros los supuestos.',
    bores:'Usa $proyecciones-svg para proponer una pieza irregular con cubierta inclinada y cuatro taladros pasantes de diámetros distintos, con sus ejes concurrentes. Indica las medidas supuestas y muéstrame las tres vistas y el giro SVG.'
  };
  const stage=document.getElementById('rotation-stage');
  const slider=document.getElementById('angle');
  const angleValue=document.getElementById('angle-value');
  const play=document.getElementById('play');
  const status=document.getElementById('demo-status');
  const hidden=document.getElementById('hidden-lines');
  const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
  const cache=new Map();
  let current='cuna',frames=[],playing=false,timer=0,loading=0,mode='volume';
  function press(group,chosen){document.querySelectorAll(group).forEach(button=>button.setAttribute('aria-pressed',String(button===chosen)));}
  function stop(){playing=false;cancelAnimationFrame(timer);play.setAttribute('aria-pressed','false');play.innerHTML='Girar la pieza <span aria-hidden="true">↻</span>';}
  function show(index){
    if(!frames.length)return;
    index=Math.max(0,Math.min(frames.length-1,Math.round(Number(index)||0)));
    slider.value=String(index);
    frames.forEach((frame,i)=>frame.setAttribute('visibility',i===index?'visible':'hidden'));
    angleValue.textContent=(Number(frames[index].dataset.azimuth)%360).toLocaleString('es',{maximumFractionDigits:1})+'°';
  }
  async function loadRotation(key){
    if(!cache.has(key))cache.set(key,fetch('assets/models/'+key+'/rotation.svg').then(response=>{
      if(!response.ok)throw new Error('No se pudo cargar el giro.');return response.text();
    }).catch(error=>{cache.delete(key);throw error;}));
    return cache.get(key);
  }
  async function selectModel(key){
    stop();current=key;const token=++loading;const info=models[key];
    document.getElementById('model-title').textContent=info.name;
    document.getElementById('model-detail').textContent=info.detail;
    document.getElementById('model-dimensions').textContent=info.dimensions+' · MEDIDAS DE EJEMPLO';
    for(const [id,file] of [['sheet-download','vistas.svg'],['rotation-download','giro.svg'],['model-download','modelo.json'],['cota-download','modelo.cota']])document.getElementById(id).href='assets/models/'+key+'/'+file;
    for(const [id,file,label] of [['plant-image','planta.svg','Planta de '],['front-image','alzado.svg','Alzado de '],['side-image','perfil.svg','Perfil derecho de ']]){
      const image=document.getElementById(id);image.src='assets/models/'+key+'/'+file;image.alt=label+info.alt+'.';
    }
    frames=[];slider.value='0';slider.disabled=true;play.disabled=true;angleValue.textContent='45°';
    const fallback=document.createElement('img');fallback.src='assets/models/'+key+'/angulo.svg';fallback.alt='Vista oblicua de '+info.alt+'.';fallback.width=640;fallback.height=460;stage.replaceChildren(fallback);stage.setAttribute('aria-busy','true');
    status.textContent='Cargando '+info.name.toLowerCase()+'.';
    try{
      const source=await loadRotation(key);if(token!==loading)return;
      const svg=new DOMParser().parseFromString(source,'image/svg+xml').documentElement;
      if(svg.localName!=='svg')throw new Error('Archivo de giro inválido.');
      stage.replaceChildren(document.importNode(svg,true));
      frames=[...stage.querySelectorAll('[data-frame]')];
      if(!frames.length)throw new Error('El giro no contiene ángulos.');
      slider.max=String(frames.length-1);slider.disabled=false;play.disabled=false;show(0);
      status.textContent=info.name+'. Giro y tres vistas disponibles.';
    }catch(error){if(token===loading)status.textContent='El giro no pudo cargarse. Puedes abrir el archivo Giro SVG o consultar las tres vistas.';}
    finally{if(token===loading)stage.removeAttribute('aria-busy');}
  }
  document.querySelectorAll('[data-model]').forEach(button=>button.addEventListener('click',()=>{press('[data-model]',button);selectModel(button.dataset.model);}));
  document.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>{
    stop();mode=button.dataset.mode;press('[data-mode]',button);
    document.getElementById('volume-panel').hidden=mode!=='volume';document.getElementById('views-panel').hidden=mode!=='views';
  }));
  slider.addEventListener('input',()=>{stop();show(slider.value);});
  hidden.addEventListener('change',()=>stage.classList.toggle('show-hidden',hidden.checked));
  play.addEventListener('click',()=>{
    if(playing){stop();return;}if(!frames.length)return;
    let initial=Number(slider.value);if(initial===frames.length-1)initial=0;
    if(motion.matches){show((initial+1)%frames.length);return;}
    playing=true;play.setAttribute('aria-pressed','true');play.innerHTML='Pausar <span aria-hidden="true">Ⅱ</span>';
    const start=performance.now();
    function tick(now){if(!playing)return;const next=initial+Math.floor((now-start)/8000*(frames.length-1));show(next);if(next>=frames.length-1){stop();return;}timer=requestAnimationFrame(tick);}
    show(initial);timer=requestAnimationFrame(tick);
  });
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
  motion.addEventListener('change',()=>{stop();play.setAttribute('aria-label',motion.matches?'Avanzar un ángulo':'Girar la pieza');});
  document.querySelectorAll('[data-prompt]').forEach(button=>button.addEventListener('click',()=>{press('[data-prompt]',button);document.getElementById('prompt-text').textContent=prompts[button.dataset.prompt];}));
  document.querySelectorAll('[data-guide]').forEach(button=>button.addEventListener('click',()=>{press('[data-guide]',button);document.getElementById('guide-assisted').hidden=button.dataset.guide!=='assisted';document.getElementById('guide-terminal').hidden=button.dataset.guide!=='terminal';}));
  document.querySelectorAll('[data-os]').forEach(button=>button.addEventListener('click',()=>{
    press('[data-os]',button);const shell=button.dataset.os!=='windows';
    document.getElementById('command-label').textContent=shell?'INSTALAR / SHELL':'INSTALAR / POWERSHELL';
    document.getElementById('install-command').textContent=shell?'python3 install_skill.py proyecciones-svg-1.1.0.zip --skills-dir "$HOME/.codex/skills"':'python install_skill.py proyecciones-svg-1.1.0.zip --skills-dir "$env:USERPROFILE\\.codex\\skills"';
    const checksum=button.dataset.os==='macos'?'shasum -a 256':'sha256sum';
    document.getElementById('checksum-command').textContent=shell?checksum+' proyecciones-svg-1.1.0.zip install_skill.py':'Get-FileHash proyecciones-svg-1.1.0.zip, install_skill.py -Algorithm SHA256';
  }));
  let copyTimer=0;
  document.querySelectorAll('[data-copy-target]').forEach(button=>button.addEventListener('click',async()=>{
    const target=document.getElementById(button.dataset.copyTarget);let text='Copiado. Ya puedes pegarlo en Codex o en tu terminal.';
    try{await navigator.clipboard.writeText(target.textContent.trim());}catch(error){text='Selecciona el texto y cópialo con Ctrl+C o ⌘C.';const selection=window.getSelection();const range=document.createRange();range.selectNodeContents(target);selection.removeAllRanges();selection.addRange(range);}
    const notice=document.getElementById('copy-status');notice.textContent=text;notice.classList.add('visible');clearTimeout(copyTimer);copyTimer=setTimeout(()=>notice.classList.remove('visible'),3500);
  }));
  const menu=document.querySelector('.menu-toggle'),navigation=document.getElementById('navigation');
  menu.addEventListener('click',()=>{const opened=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(opened));navigation.classList.toggle('open',opened);});
  navigation.querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>{menu.setAttribute('aria-expanded','false');navigation.classList.remove('open');}));
  if('IntersectionObserver' in window){const observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){selectModel(current);observer.disconnect();}},{rootMargin:'250px'});observer.observe(document.getElementById('ejemplos'));}else selectModel(current);
})();
