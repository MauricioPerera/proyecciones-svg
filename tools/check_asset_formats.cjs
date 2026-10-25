'use strict';
const fs=require('node:fs');
const path=require('node:path');
const validator=require('gltf-validator');
const root=path.resolve(process.argv[2]||path.join(__dirname,'..','build','prototipo-assets'));
(async()=>{
  const reports=[];
  const catalog=JSON.parse(fs.readFileSync(path.join(root,'catalog.json'),'utf8'));
  for(const {id:name} of catalog){
    const file=path.join(root,name,'modelo.glb');
    const report=await validator.validateBytes(new Uint8Array(fs.readFileSync(file)),{uri:name+'.glb',writeTimestamp:false,maxIssues:0});
    reports.push({model:name,validator:validator.version(),report});
    if(report.issues.numErrors||report.issues.numWarnings)throw new Error(name+': '+JSON.stringify(report.issues));
  }
  fs.writeFileSync(path.join(root,'gltf-validation.json'),JSON.stringify({status:'success',reports},null,2)+'\n');
  console.log(JSON.stringify(reports.map(r=>({model:r.model,validator:r.validator,errors:r.report.issues.numErrors,warnings:r.report.issues.numWarnings}))));
})().catch(e=>{console.error(e);process.exitCode=1});
