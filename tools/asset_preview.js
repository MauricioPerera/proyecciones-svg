import * as THREE from 'three';
import { GLTFLoader } from './vendor/addons/loaders/GLTFLoader.js';
import { OrbitControls } from './vendor/addons/controls/OrbitControls.js';

const catalog=await fetch('./catalog.json').then(r=>{if(!r.ok)throw new Error('No se pudo leer el catálogo');return r.json()});
const loader=new GLTFLoader();
const roots=new Map();
function makeView(host,object,course=false){
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.domElement.tabIndex=0;renderer.domElement.setAttribute('aria-label',course?'Escena modular 3D; arrastra para girar':'Modelo GLB 3D; arrastra para girar');
  host.append(renderer.domElement);
  const scene=new THREE.Scene();scene.add(object);
  object.traverse(n=>{if(n.isMesh){n.castShadow=true;n.receiveShadow=true}});
  const box=new THREE.Box3().setFromObject(object),size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3());
  const extent=Math.max(size.x,size.y,size.z);
  const camera=new THREE.PerspectiveCamera(36,1,extent/1000,extent*100);
  camera.position.copy(center).add(new THREE.Vector3(1.15,.95,1.4).multiplyScalar(extent*(course ? .8 : 1.5)));
  scene.add(new THREE.HemisphereLight(0xffffff,0x7a8d99,2.7));
  const sun=new THREE.DirectionalLight(0xffffff,3);sun.position.copy(center).add(new THREE.Vector3(-1,2,1).multiplyScalar(extent*2));sun.castShadow=true;
  sun.shadow.camera.left=sun.shadow.camera.bottom=-extent*2;sun.shadow.camera.right=sun.shadow.camera.top=extent*2;sun.shadow.camera.near=extent/10;sun.shadow.camera.far=extent*10;sun.shadow.mapSize.set(1024,1024);sun.shadow.bias=-.00002;scene.add(sun);scene.add(sun.target);sun.target.position.copy(center);
  const ground=new THREE.Mesh(new THREE.PlaneGeometry(extent*10,extent*10),new THREE.ShadowMaterial({opacity:.12}));ground.rotation.x=-Math.PI/2;ground.position.set(center.x,box.min.y-.0001,center.z);ground.receiveShadow=true;scene.add(ground);
  const grid=new THREE.GridHelper(course ? .24 : .10,course ? 24 : 10,0xb9cbd4,0xd4e0e5);grid.position.set(center.x,box.min.y-.00012,center.z);scene.add(grid);
  const controls=new OrbitControls(camera,renderer.domElement);controls.target.copy(center);controls.enablePan=false;controls.minDistance=extent*.7;controls.maxDistance=extent*6;controls.update();
  const render=()=>renderer.render(scene,camera);controls.addEventListener('change',render);
  const resize=new ResizeObserver(()=>{const {width,height}=host.getBoundingClientRect();if(width&&height){renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();render()}});resize.observe(host);render();
  host.dataset.loaded='true';
  return {size:size.toArray(),box:[box.min.toArray(),box.max.toArray()]};
}
for(const item of catalog){
  const card=document.createElement('article');card.className='card';card.dataset.asset=item.id;
  const host=document.createElement('div');host.className='stage';
  const status=document.createElement('span');status.className='loaded';status.textContent='Cargando modelo…';host.append(status);
  const content=document.createElement('div');content.className='content';
  const title=document.createElement('h2');title.textContent=item.name;
  const details=document.createElement('div');details.className='details';details.textContent=`40 × 40 × 20 mm · ${(item.volumeMm3/1000).toLocaleString('es')} cm³`;
  const downloads=document.createElement('div');downloads.className='downloads';
  for(const [format,label] of [['glb','Juego · GLB'],['3mf','Impresión · 3MF'],['stl','STL']]){const link=document.createElement('a');link.href=`./${item.id}/modelo.${format}`;link.download=`${item.id}.${format}`;link.textContent=label;downloads.append(link)}
  const links=document.createElement('div');links.className='secondary';
  for(const [file,label] of [['visor.html','Vistas y giro SVG'],['modelo.json','Fuente JSON']]){const a=document.createElement('a');a.href=`./${item.id}/${file}`;a.textContent=label;a.target='_blank';a.rel='noopener';links.append(a)}
  content.append(title,details,downloads,links);card.append(host,content);document.getElementById('cards').append(card);
  try{const gltf=await loader.loadAsync(`./${item.id}/modelo.glb`);roots.set(item.id,gltf.scene);const metrics=makeView(host,gltf.scene.clone(true));
    if(metrics.size.some((v,i)=>Math.abs(v-item.dimensionsMm[[0,2,1][i]]/1000)>1e-7))throw new Error('Las dimensiones cargadas no coinciden con el catálogo');
    status.textContent=`Malla cargada · ${item.triangles} triángulos`;card.dataset.valid='true';
  }catch(error){status.classList.add('error');status.textContent='No se pudo cargar el GLB';card.dataset.error=String(error);console.error(error)}
}
try{if(roots.size!==3)throw new Error('Faltan módulos');const course=new THREE.Group();
  const stairs=roots.get('escalera').clone(true);course.add(stairs);
  const block=roots.get('bloque').clone(true);block.position.x=.04;course.add(block);
  const ramp=roots.get('rampa').clone(true);ramp.rotation.y=Math.PI;ramp.position.set(.12,0,-.04);course.add(ramp);
  const host=document.getElementById('scene');const metrics=makeView(host,course,true);host.dataset.widthMeters=String(metrics.size[0]);host.querySelector('.loaded').textContent='3 módulos · arrastra para explorar';
}catch(error){document.querySelector('#scene .loaded').textContent='No se pudo construir la escena';console.error(error)}
