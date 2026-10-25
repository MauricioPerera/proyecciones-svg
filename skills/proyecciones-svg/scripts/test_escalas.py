"""Scale regressions checked against raw geometry and the emitted SVG labels."""
import argparse
import copy
import json
import math
from pathlib import Path
import unittest

import proyectar as p
import pieza_taladrada as single
import taladro_cilindrico as block
import taladros_cruzados as base
import taladros_desiguales as unequal
import tres_taladros as shared
from cuatro_taladros import FourBores

ASSETS=Path(__file__).resolve().parent.parent/'assets'
SCALES=(1e-8,1e-5,1.0,1e6)


def load(name):
    return json.loads((ASSETS/name).read_text(encoding='utf-8'))


def scaled(data,factor):
    result=copy.deepcopy(data)
    for name in ('size','profile','footprint','vertices'):
        if name in result:
            result[name]=[[x*factor for x in point] for point in result[name]] if name!='size' else [x*factor for x in result[name]]
    for name in ('depth',):
        if name in result:
            result[name]*=factor
    if 'roof' in result:
        result['roof']['offset']*=factor
    for section in result.get('sections', []):
        section['origin']=[x*factor for x in section['origin']]
    for bore in result.get('bores',[result['bore']] if 'bore' in result else []):
        bore['center']=[x*factor for x in bore['center']]
        bore['diameter']*=factor
    return result


def radial_ratio(point,bore):
    # Independent raw-JSON cylinder equation, evaluated at the original scale.
    axis=bore.get('direction',[0,0,1])
    norm=math.hypot(*axis)
    axis=[v/norm for v in axis]
    vector=[point[0]-bore['center'][0],point[1]-bore['center'][1],point[2]]
    along=sum(a*b for a,b in zip(vector,axis))
    return sum((v-along*a)**2 for v,a in zip(vector,axis))/(bore['diameter']/2)**2


def material_oracle(data,point,direction):
    # Split the in-body ray at every quadratic root, then test each open span.
    ax,by=data['roof']['slope_x'],data['roof']['slope_y']
    planes=[((0,0,-1),0),((-ax,-by,1),data['roof']['offset'])]
    footprint=data['footprint']
    for a,b in zip(footprint,footprint[1:]+footprint[:1]):
        n=(b[1]-a[1],a[0]-b[0],0)
        planes.append((n,n[0]*a[0]+n[1]*a[1]))
    lo,hi=1e-7,math.inf
    for normal,constant in planes:
        distance=sum(a*b for a,b in zip(normal,point))-constant
        speed=sum(a*b for a,b in zip(normal,direction))
        if abs(speed)<1e-12:
            if distance>1e-8:
                return False
        elif speed>0:
            hi=min(hi,-distance/speed)
        else:
            lo=max(lo,-distance/speed)
    if hi<=lo:
        return False
    knots=[lo,hi]
    for bore in data['bores']:
        axis=bore['direction'];norm=math.hypot(*axis)
        axis=[x/norm for x in axis]
        v=[point[0]-bore['center'][0],point[1]-bore['center'][1],point[2]]
        vd=sum(x*y for x,y in zip(v,axis))
        dd=sum(x*y for x,y in zip(direction,axis))
        a=sum((x-dd*y)**2 for x,y in zip(direction,axis))
        b=2*sum((x-vd*z)*(y-dd*z) for x,y,z in zip(v,direction,axis))
        c=sum((x-vd*y)**2 for x,y in zip(v,axis))-(bore['diameter']/2)**2
        disc=b*b-4*a*c
        if a>1e-14 and disc>0:
            knots.extend(t for t in ((-b-math.sqrt(disc))/(2*a),(-b+math.sqrt(disc))/(2*a)) if lo<t<hi)
    knots.sort()
    for start,end in zip(knots,knots[1:]):
        if end-start<1e-9:
            continue
        sample=[v+(start+end)/2*d for v,d in zip(point,direction)]
        if all(radial_ratio(sample,b)>1+1e-9 for b in data['bores']):
            return True
    return False


def expected_state(data,curve,point,direction):
    if isinstance(curve,unequal.Seam) and any(radial_ratio(point,data['bores'][i])<1-1e-8 for i in getattr(curve,'others',())):
        return 'omit'
    return 'hidden' if material_oracle(data,point,direction) else 'visible'


class ScaleTests(unittest.TestCase):
    def test_two_bore_visibility_keeps_value_at_all_scales(self):
        for name,constructor in (('taladros-cruzados.json',base.CrossedBores),('taladros-desiguales.json',unequal.UnequalBores)):
            data=load(name)
            for factor in SCALES:
                model=constructor(scaled(data,factor))
                for azimuth,elevation in ((45,50),(210,50),(0,90)):
                    direction=p.camera(azimuth,elevation)[2]
                    if constructor is base.CrossedBores:
                        mapping=p.angle_mapping(model.body)
                        screens=[base.projected(c,model,azimuth,elevation,mapping) for c in model.curves]
                        lines=base.generator_lines(model,direction,azimuth,elevation,mapping)
                    for index,curve in enumerate(model.curves):
                        intervals=(base.visibility_intervals(curve,screens[index],screens,lines,model,direction)
                                   if constructor is base.CrossedBores else unequal.visibility_intervals(curve,model,direction))
                        for i in range(97):
                            theta=math.tau*(i+.381)/97
                            visible=next(value for a,b,value in intervals if a<=theta<=b)
                            point=[x/factor for x in curve.point(theta)]
                            self.assertEqual(visible,not material_oracle(data,point,direction),(name,factor,azimuth,elevation,curve.feature,theta))

    def test_dimension_labels_keep_value_for_every_generator(self):
        cases=[
            ('escalon.json',p.Model,lambda m:p.sheet_svg(m)),
            ('bloque-taladrado.json',block.BoredBlock,lambda m:block.sheet(m,'third','dash')),
            ('taladro-inclinado.json',single.SlopedBore,lambda m:single.sheet(m,'third','dash')),
            ('taladros-cruzados.json',base.CrossedBores,lambda m:base.sheet(m,'third','dash')),
            ('taladros-desiguales.json',unequal.UnequalBores,lambda m:base.sheet(m,'third','dash',unequal.decorate)),
            ('tres-taladros.json',shared.ThreeBores,lambda m:base.sheet(m,'third','dash',shared.decorate)),
            ('cuatro-taladros.json',FourBores,lambda m:base.sheet(m,'third','dash',shared.decorate)),
        ]
        for name,constructor,sheet in cases:
            data=load(name)
            original=constructor(data)
            body=original.box if hasattr(original,'box') else original.body if hasattr(original,'body') else original
            width,depth,height=body.size
            bores=data.get('bores',[data['bore']] if 'bore' in data else [])
            for factor in (1e-8,1,1e8):
                with self.subTest(name=name,factor=factor):
                    root=sheet(constructor(scaled(data,factor)))
                    values=[float(n.text) for n in root if n.tag==f'{{{p.NS}}}text' and n.get('class')=='label']
                    self.assertEqual(len(values),4)
                    for actual,target in zip(values,(width,height,depth,depth)):
                        self.assertTrue(math.isclose(actual,target*factor,rel_tol=5e-12),(actual,target*factor))
                    diameters=[float(n.text.split('Ø ')[1]) for n in root.iter(f'{{{p.NS}}}text') if n.text and 'Ø ' in n.text]
                    self.assertEqual(len(diameters),len(bores))
                    for actual,bore in zip(diameters,bores):
                        self.assertTrue(math.isclose(actual,bore['diameter']*factor,rel_tol=5e-12))

    def test_micro_block_labels_remain_nonzero_in_meters(self):
        data={'type':'block_with_bore','units':'m','size':[8e-6,6e-6,2e-6],
              'bore':{'axis':'z','center':[4e-6,3e-6],'diameter':3e-6,'through':True}}
        root=block.sheet(block.BoredBlock(data),'third','dash')
        dimensions=[float(n.text) for n in root if n.tag==f'{{{p.NS}}}text' and n.get('class')=='label']
        self.assertEqual(dimensions,[8e-6,2e-6,6e-6,6e-6])
        diameter=next(n.text for n in root.iter(f'{{{p.NS}}}text') if n.text and n.text.startswith('Ø '))
        self.assertEqual(float(diameter[2:]),3e-6)

    def test_curve_visibility_and_burial_against_raw_geometry_at_all_scales(self):
        for name,constructor in (('tres-taladros.json',shared.ThreeBores),('cuatro-taladros.json',FourBores)):
            data=load(name)
            for factor in SCALES:
                m=constructor(scaled(data,factor))
                for azimuth,elevation in ((45,50),(210,50),(0,90)):
                    direction=p.camera(azimuth,elevation)[2]
                    mapping=p.angle_mapping(m.body)
                    screens={c.feature:shared.screen_curve(c,m,azimuth,elevation,mapping) for c in m.curves}
                    tops=[screens['top-'+str(i)] for i in range(len(m.bores))]
                    hulls={pair:unequal.overlap_projection_path(value,azimuth,elevation,mapping,True) for pair,value in m.pairs.items()}
                    for curve in m.curves:
                        intervals=shared.curve_intervals(curve,screens[curve.feature],tops,hulls,m,direction)
                        for i in range(97):
                            theta=math.tau*(i+.381)/97
                            actual=next(state for a,b,state in intervals if a<=theta<=b)
                            point=[v/factor for v in curve.point(theta)]
                            expected=expected_state(data,curve,point,direction)
                            self.assertEqual(actual,expected,(name,factor,azimuth,elevation,curve.feature,theta))

    def test_exported_svg_does_not_reintroduce_buried_curves_at_small_scale(self):
        for name,constructor in (('tres-taladros.json',shared.ThreeBores),('cuatro-taladros.json',FourBores)):
            data=load(name)
            for factor in SCALES:
                m=constructor(scaled(data,factor))
                args=argparse.Namespace(azimuth=45,elevation=50,hidden='dash')
                root=base.view(m,args,shared.decorate)
                lookup={c.feature:c for c in m.curves}
                for node in root.iter():
                    feature=node.get('data-curve')
                    if not feature:
                        continue
                    curve=lookup[feature]
                    a,b=float(node.get('data-start')),float(node.get('data-end'))
                    for fraction in (.17,.43,.79):
                        point=[v/factor for v in curve.point(a+(b-a)*fraction)]
                        self.assertNotEqual(expected_state(data,curve,point,p.camera(45,50)[2]),'omit',(name,factor,feature))

    def test_generators_keep_geometry_and_trim_at_all_scales(self):
        for name,constructor in (('tres-taladros.json',shared.ThreeBores),('cuatro-taladros.json',FourBores)):
            data=load(name)
            lengths=[]
            for factor in SCALES:
                model=constructor(scaled(data,factor))
                pieces=shared.generator_pieces(model,p.camera(45,50)[2])
                lengths.append(sum(math.dist(a,b)/factor for a,b in pieces))
                self.assertTrue(pieces)
                for first,last in pieces:
                    for fraction in (.1,.5,.9):
                        point=[(a+(b-a)*fraction)/factor for a,b in zip(first,last)]
                        self.assertTrue(all(radial_ratio(point,b)>1-1e-8 for b in data['bores']),(name,factor,point))
            self.assertTrue(all(math.isclose(value,lengths[0],rel_tol=1e-7) for value in lengths),lengths)


if __name__=='__main__':
    unittest.main()
