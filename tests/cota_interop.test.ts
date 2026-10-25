import { it,expect } from 'vitest'
import { readFileSync,writeFileSync } from 'node:fs'
import * as THREE from 'three'
import { DocumentModel } from '../core/document/DocumentModel'
import { solidGeometry,solidMesh } from '../render/csg'
import type { SolidProps } from '../core/document/types'
import { orthoProject,segmentsBounds } from '../core/projection/orthographic'

const root=process.env.PROYECCIONES_SVG_COTA_OUTPUT!
if(!root)throw Error('Run with tools/check_cota_interop.py')
const details:any[]=[]
const load=(name:string)=>{
  const data=JSON.parse(readFileSync(`${root}/${name}/modelo.cota`,'utf8'))
  const doc=DocumentModel.fromJSON(data)
  expect(doc.units).toBe('mm')
  expect(doc.modelEntities).toHaveLength(1)
  expect(doc.modelEntities[0].props).toEqual(data.entities[0].props)
  return data.entities[0].props as SolidProps
}
const volume=(p:SolidProps)=>{
  const {vertices:v,faces:f}=solidMesh(p)
  return f.reduce((total,[a,b,c])=>{
    const [x,y,z]=v[a], [u,w,t]=v[b], [j,k,l]=v[c]
    return total+(x*(w*l-t*k)+y*(t*j-u*l)+z*(u*k-w*j))/6
  },0)
}
const materialTester=(props:SolidProps)=>{
  const m=new THREE.Mesh(solidGeometry(props),new THREE.MeshBasicMaterial({side:THREE.DoubleSide}))
  m.updateMatrixWorld(true)
  return (p:number[])=>{
    const ray=new THREE.Raycaster(new THREE.Vector3(p[0],p[1],p[2]),new THREE.Vector3(.879,.412,.24).normalize())
    const hits=ray.intersectObject(m).map(h=>h.distance)
    const unique=hits.filter((h,i)=>i===0||Math.abs(h-hits[i-1])>1e-5)
    return unique.length%2===1
  }
}

it('opens the generated wedge, preserving all three views and volume',()=>{
  const props=load('cuna')
  const mesh=solidMesh(props)
  const views=['front','top','right'].map((v:any)=>{
    const b=segmentsBounds(orthoProject([mesh],v))
    return [b.maxU-b.minU,b.maxV-b.minV]
  })
  expect(views).toEqual([[60,30],[60,40],[40,30]])
  expect(volume(props)).toBeCloseTo(36000,2)
  const material=materialTester(props)
  expect(material([45,20,5])).toBe(true)
  expect(material([10,20,25])).toBe(false)
  expect(material([70,20,5])).toBe(false)
  details.push({model:'cuna',views_mm:views,volume_mm3:volume(props),material_checks:3})
})

it('opens the four bores and verifies material, cavities and the sloped roof volume',()=>{
  const props=load('cuatro-taladros')
  if(props.op!=='SUBTRACT')throw Error('Expected a cut solid')
  const original=JSON.parse(readFileSync(`${root}/cuatro-taladros/modelo.json`,'utf8'))
  const f=original.footprint
  let area2=0,mx6=0,my6=0
  f.forEach(([x,y]:number[],i:number)=>{
    const [u,v]=f[(i+1)%f.length],c=x*v-u*y
    area2+=c;mx6+=(x+u)*c;my6+=(y+v)*c
  })
  const expected=1000*(original.roof.offset*area2/2+original.roof.slope_x*mx6/6+original.roof.slope_y*my6/6)
  const actual=volume(props.operands[0])
  expect(actual).toBeCloseTo(expected,1)
  const material=materialTester(props)
  const checks:any[]=[]
  for(const bore of original.bores)for(const z of [5,15,20]){
    const p=[bore.center[0]*10+z*bore.direction[0]/bore.direction[2],bore.center[1]*10+z*bore.direction[1]/bore.direction[2],z]
    expect(material(p),`Hole axis at ${p}`).toBe(false)
    checks.push({point:p,material:false})
  }
  for(const p of [[5,5,5],[70,15,10],[10,50,10]]){
    expect(material(p),`Material at ${p}`).toBe(true)
    checks.push({point:p,material:true})
  }
  const mesh=solidMesh(props)
  details.push({model:'cuatro-taladros',body_volume_expected_mm3:expected,body_volume_actual_mm3:actual,faces:mesh.faces.length,material_checks:checks})
  writeFileSync(`${root}/cota-interop.json`,JSON.stringify({cota_commit:'e43e37de4017e6b87f72180b0f4e6162943f4880',cases:details},null,2))
},60000)
