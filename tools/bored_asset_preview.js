import * as THREE from 'three';
import {GLTFLoader} from './vendor/addons/loaders/GLTFLoader.js';
import {OrbitControls} from './vendor/addons/controls/OrbitControls.js';

function view(host,object,clipped=false){
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.localClippingEnabled=true;
  renderer.domElement.tabIndex=0;renderer.domElement.setAttribute('aria-label',clipped?'Interior del GLB con recorte visual; arrastra para girar':'GLB completo; arrastra para girar');host.append(renderer.domElement);
  const scene=new THREE.Scene();scene.add(object);
  const plane=new THREE.Plane(new THREE.Vector3(0,-1,0),.015);
  object.traverse(node=>{if(node.isMesh){node.material=node.material.clone();if(clipped){node.material.clippingPlanes=[plane];node.material.side=THREE.DoubleSide;}}});
  const box=new THREE.Box3().setFromObject(object),size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3());
  const extent=Math.max(...size.toArray());
  const camera=new THREE.PerspectiveCamera(36,1,extent/1000,extent*100);
  camera.position.copy(center).add(new THREE.Vector3(.8,1.1,1.4).multiplyScalar(extent*1.4));
  scene.add(new THREE.HemisphereLight(0xffffff,0x647b90,2.5));
  const sun=new THREE.DirectionalLight(0xffffff,3.2);sun.position.copy(center).add(new THREE.Vector3(-1,2,1).multiplyScalar(extent));scene.add(sun);
  const grid=new THREE.GridHelper(.16,16,0xaec7d0,0xd8e4e9);grid.position.set(center.x,-.0002,center.z);scene.add(grid);
  const controls=new OrbitControls(camera,renderer.domElement);controls.target.copy(center);controls.enablePan=false;controls.minDistance=extent*.7;controls.maxDistance=extent*6;controls.update();
  const render=()=>renderer.render(scene,camera);controls.addEventListener('change',render);
  const resize=new ResizeObserver(()=>{const {width,height}=host.getBoundingClientRect();if(width&&height){renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();render();}});resize.observe(host);render();
  host.dataset.loaded='true';host.querySelector('.status').textContent=clipped?'Recorte visual · sin tapa añadida':'GLB cargado · sólido completo';
  return {size:size.toArray(),setHeight(mm){plane.constant=mm/1000;host.dataset.cutHeightMm=String(mm);render();}};
}
try{
  const [item]=await fetch('./catalog.json').then(r=>r.json());
  const gltf=await new GLTFLoader().loadAsync('./cuatro-taladros/modelo.glb');
  const whole=view(document.getElementById('whole'),gltf.scene.clone(true));
  const inside=view(document.getElementById('inside'),gltf.scene.clone(true),true);
  if(whole.size.some((v,i)=>Math.abs(v-item.dimensionsMm[[0,2,1][i]]/1000)>1e-7))throw new Error('Dimensiones del GLB distintas al catálogo');
  document.getElementById('metrics').textContent=`${item.dimensionsMm.map(v=>Number(v.toFixed(3))).join(' × ')} mm · ${item.triangles.toLocaleString('es')} triángulos · ${(item.volumeMm3/1000).toLocaleString('es',{maximumFractionDigits:3})} cm³ · ocho bocas y cuatro conductos comunicados.`;
  document.getElementById('metrics').dataset.valid='true';inside.setHeight(15);
  document.getElementById('height').addEventListener('input',event=>{const mm=Number(event.target.value);inside.setHeight(mm);document.getElementById('heightValue').textContent=`${mm.toLocaleString('es')} mm`;});
}catch(error){document.getElementById('metrics').textContent='No se pudo cargar o validar el GLB.';document.getElementById('metrics').classList.add('error');console.error(error);}
