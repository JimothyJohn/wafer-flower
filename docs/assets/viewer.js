// Wafer Halo — real-STL viewer widget (mine-architecture scene,
// 2026-08-15). Used by viewer.html. Expects canvas#viz, #status,
// #presets, and the control ids referenced below. Loads
// models/manifest.json + STLs exported by `scripts/mine_stl.py --viewer`:
// Nick's CANONICAL OnShape segment, a generated wafer, the placed 12T
// pinion, and the parametric-RE segment as a comparison overlay.
'use strict';
(function(){
const canvas=document.getElementById('viz');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true});
renderer.localClippingEnabled=true;
const scene=new THREE.Scene(); scene.background=new THREE.Color(0xEEF1F4);
const camera=new THREE.PerspectiveCamera(40,2,1,8000);
scene.add(new THREE.AmbientLight(0xffffff,0.55));
const key=new THREE.DirectionalLight(0xffffff,0.7); key.position.set(400,600,800); scene.add(key);
const fill=new THREE.DirectionalLight(0xffffff,0.3); fill.position.set(-500,-200,400); scene.add(fill);

// binary STL -> non-indexed BufferGeometry (flat normals: it's CAD)
function parseSTL(buf){
  const dv=new DataView(buf), n=dv.getUint32(80,true);
  const pos=new Float32Array(n*9);
  for(let i=0;i<n;i++){
    const o=84+i*50;
    for(let v=0;v<3;v++)for(let c=0;c<3;c++)
      pos[i*9+v*3+c]=dv.getFloat32(o+12+v*12+c*4,true);
  }
  const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.BufferAttribute(pos,3));
  g.computeVertexNormals();
  return g;
}

const clipPlane=new THREE.Plane(new THREE.Vector3(0,-1,0),1e6);
function mat(hex,extra){
  return new THREE.MeshPhongMaterial(Object.assign({color:hex,shininess:18,
    side:THREE.DoubleSide,clippingPlanes:[clipPlane]},extra||{}));
}

let M=null;                       // manifest
const groups={};                  // one THREE.Group per part group
const stations=[];                // clones for stations 1..8
const geo={};
const SEC=()=>M?M.sector_deg*Math.PI/180:0;

async function load(){
  try{
    let bufs;
    try{
      M=await (await fetch('models/manifest.json')).json();
      bufs=await Promise.all(M.parts.map(p=>
        fetch('models/'+p.file).then(r=>{
          if(!r.ok)throw new Error(p.file);return r.arrayBuffer();})));
    }catch(e){
      // fetch() is blocked under file:// — fall back to the base64 bundle
      await new Promise((res,rej)=>{
        const s=document.createElement('script');
        s.src='models/models_data.js'; s.onload=res; s.onerror=rej;
        document.head.appendChild(s);
      });
      const D=window.HALO_MODELS;
      M=D.manifest;
      bufs=M.parts.map(p=>{
        const bin=atob(D.files[p.file]), u=new Uint8Array(bin.length);
        for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
        return u.buffer;
      });
    }
    M.parts.forEach((p,i)=>{geo[p.name]=parseSTL(bufs[i]);});
  }catch(e){
    document.getElementById('status').textContent=
      'failed to load models/ — neither fetch nor the models_data.js bundle '+
      'worked. Regenerate with scripts/mine_stl.py --viewer.';
    throw e;
  }
  for(const p of M.parts){
    if(!groups[p.group]){groups[p.group]=new THREE.Group();scene.add(groups[p.group]);}
    const m=new THREE.Mesh(geo[p.name],
      mat(parseInt(p.color.slice(1),16),
          p.name==='wafer'?{shininess:95,specular:0x8899AA}:
          p.group==='param'?{transparent:true,opacity:0.6}:{}));
    groups[p.group].add(m);
  }
  if(groups.param) groups.param.visible=false;
  // stations 1..8: segment + wafer clones, rotated into place
  for(let k=1;k<9;k++){
    const g=new THREE.Group(); g.rotation.z=k*SEC(); g.visible=false;
    g.add(new THREE.Mesh(geo.segment,groups.segment.children[0].material));
    g.add(new THREE.Mesh(geo.wafer,groups.wafer.children[0].material));
    scene.add(g); stations.push(g);
  }
  renderChecks();
  document.getElementById('status').textContent=
    M.parts.map(p=>p.file).join(' · ')+'  ·  θ='+M.params.theta+'° N='+M.params.N+
    '  ·  canonical: stl/mine (OnShape) + parametric RE overlay';
}

function renderChecks(){
  const el=document.getElementById('checks');
  let pass=0;
  el.innerHTML=M.checks.map(c=>{
    if(c.pass)pass++;
    return '<div><span class="chip '+(c.pass?'ok':'bad')+'">'+(c.pass?'PASS':'FAIL')+
      '</span><span class="nm">['+c.group+'] '+c.name+'</span>'+
      '<span class="mono">'+c.value_mm3.toFixed(2)+'</span></div>';
  }).join('');
  document.getElementById('checksum').innerHTML=
    ' <span class="chip '+(pass===M.checks.length?'ok':'bad')+'">'+
    pass+'/'+M.checks.length+'</span>';
}

// ---- state + animation --------------------------------------------------
const S={lift:0,stations:1,section:1,waf:1,drv:0,dist:800};
const T=Object.assign({},S);                            // targets (lerped)
const ui={lift:document.getElementById('lift'),
  stations:document.getElementById('stations'),
  section:document.getElementById('section'),
  waf:document.getElementById('waf'),
  drv:document.getElementById('drv')};
ui.waf.onchange=()=>{T.waf=ui.waf.checked?1:0;};
ui.drv.onchange=()=>{T.drv=ui.drv.checked?1:0;};
document.getElementById('param').onchange=e=>{
  if(groups.param)groups.param.visible=e.target.checked;
  document.getElementById('paramv').textContent=e.target.checked?'on':'off';
};
ui.lift.oninput=()=>{T.lift=parseFloat(ui.lift.value);};
ui.stations.oninput=()=>{T.stations=parseInt(ui.stations.value);};
ui.section.oninput=()=>{T.section=parseFloat(ui.section.value);};

const PRESETS={
  bare:  {lift:1,stations:1,waf:0,drv:0,dist:600},
  drop:  {lift:1,stations:1,waf:1,drv:0,dist:650},
  bonded:{lift:0,stations:1,waf:1,drv:0,dist:650},
  pair:  {lift:0,stations:2,waf:1,drv:0,dist:1250},
  halo:  {lift:0,stations:9,waf:1,drv:1,dist:2100},
  drive: {lift:0,stations:9,waf:0,drv:1,dist:520},
};
document.getElementById('presets').onclick=e=>{
  const p=PRESETS[e.target.dataset.p]; if(!p)return;
  Object.assign(T,p);
  ui.waf.checked=!!p.waf; ui.drv.checked=!!p.drv;
  ui.lift.value=p.lift; ui.stations.value=p.stations;
  document.querySelectorAll('#presets .pz').forEach(b=>
    b.classList.toggle('act',b===e.target));
};

function apply(){
  if(!M||!groups.wafer)return;   // manifest lands before the meshes do
  const w=M.motion.wafer.vector;
  groups.wafer.position.set(w[0]*S.lift,w[1]*S.lift,w[2]*S.lift);
  groups.wafer.visible=S.waf>0.03;
  const wm=groups.wafer.children[0].material;
  wm.transparent=S.waf<0.98; wm.opacity=Math.max(S.waf,0.05);
  if(groups.drive){
    groups.drive.visible=S.drv>0.03;
    const dm=groups.drive.children[0].material;
    dm.transparent=S.drv<0.98; dm.opacity=Math.max(S.drv,0.05);
  }
  stations.forEach((g,i)=>{g.visible=(i+2)<=Math.round(S.stations);
    g.children[1].visible=S.waf>0.03;});
  clipPlane.constant=S.section>=0.995?1e6:-160+S.section*320;
  // readouts
  document.getElementById('wafv').textContent=S.waf>0.5?'on':'off';
  document.getElementById('drvv').textContent=S.drv>0.5?'on':'off';
  document.getElementById('liftv').textContent=
    S.lift<0.02?'bonded':(S.lift>0.98?'above the land':(S.lift*100).toFixed(0)+'%');
  document.getElementById('stationsv').textContent=Math.round(S.stations);
  document.getElementById('sectionv').textContent=
    S.section>=0.995?'off':('y<'+(-160+S.section*320).toFixed(0));
}

// ---- orbit --------------------------------------------------------------
let az=0.7,pol=1.22;
const target=new THREE.Vector3(335,0,20), tgt=new THREE.Vector3(335,0,20);
let drag=null;
canvas.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);});
canvas.addEventListener('pointermove',e=>{if(!drag)return;
  az-=(e.clientX-drag[0])*0.006; pol=Math.min(2.9,Math.max(0.15,pol-(e.clientY-drag[1])*0.006));
  drag=[e.clientX,e.clientY];});
canvas.addEventListener('pointerup',()=>{drag=null;});
canvas.addEventListener('wheel',e=>{e.preventDefault();
  T.dist=S.dist=Math.min(4000,Math.max(250,S.dist*(1+e.deltaY*0.001)));},{passive:false});

function tick(){
  requestAnimationFrame(tick);
  for(const k of ['lift','stations','section','waf','drv','dist'])
    S[k]+=(T[k]-S[k])*0.14;
  const dist=S.dist;
  apply();
  // camera: station focus vs ring focus (the drive preset zooms the
  // 12 o'clock mesh — station focus point sits on the pinion)
  const ring=Math.min(1,(S.stations-1)/2);
  tgt.set(335*(1-ring),0,20*(1-ring));
  if(S.drv>0.5&&S.dist<700) tgt.set(335,0,12);
  target.lerp(tgt,0.08);
  const w=canvas.clientWidth,h=canvas.clientHeight;
  if(canvas.width!==w*devicePixelRatio||canvas.height!==h*devicePixelRatio){
    renderer.setSize(w,h,false);renderer.setPixelRatio(devicePixelRatio);}
  camera.aspect=w/h;camera.updateProjectionMatrix();
  camera.position.set(target.x+dist*Math.sin(pol)*Math.cos(az),
                      target.y+dist*Math.sin(pol)*Math.sin(az),
                      target.z+dist*Math.cos(pol));
  camera.up.set(0,0,1);
  camera.lookAt(target);
  renderer.render(scene,camera);
}
load(); tick();
})();
