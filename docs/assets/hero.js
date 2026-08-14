// Wafer Halo — the showreel engine. One fixed full-viewport canvas renders
// NICK'S CANONICAL MODELS (docs/models: his OnShape segment + the checked
// pinion) with mirror-cylinder wafers — the real thing, not a parametric
// stand-in (Nick 2026-08-16: "use mine for the main page; the bland ones
// for the parametric visualization"). Meshes stream in async (fetch, with
// the models_data.js base64 bundle as the file:// fallback); the wafers
// paint first so the reel opens instantly. Scroll scrubs a keyframed
// camera through five cinematic shots; pinion speed is the master clock
// and the ring follows at the true ratio.
'use strict';
(function(){
const canvas=document.getElementById('reel');
if(!canvas) return;
let renderer;
try{ renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true}); }
catch(e){ document.body.classList.add('nogl'); return; }
renderer.setClearColor(0x000000,0);

// ---- canonical architecture parameters (stl/mine measured) ----
const P={D:300,wt:0.775,N:9,tilt:3,R:350,bond:1.1};
const LAND_C=38.8;                          // land height over the wall face
const WR=P.D/2, SEG=2*Math.PI/P.N;
const TH=P.tilt*Math.PI/180;
// world frame: wafer mid-plane ~z=0 — the wall face sits at zW
const zW=-(LAND_C+P.bond+P.wt/2);

// ---- scene ----
const scene=new THREE.Scene();
scene.fog=new THREE.Fog(0x08090b,1500,3400);
const camera=new THREE.PerspectiveCamera(38,2,1,7000);
camera.up.set(0,1,0);
scene.add(new THREE.AmbientLight(0x24262a,0.5));
const key=new THREE.DirectionalLight(0xfff2e2,0.95); key.position.set(280,700,520); scene.add(key);
const rim=new THREE.DirectionalLight(0xb9c2cc,0.55); rim.position.set(-900,-250,350); scene.add(rim);
const fill2=new THREE.DirectionalLight(0x8e959d,0.3); fill2.position.set(800,-550,240); scene.add(fill2);
const top2=new THREE.DirectionalLight(0xd8dade,0.3); top2.position.set(-250,800,160); scene.add(top2);
const under=new THREE.DirectionalLight(0x555b63,0.3); under.position.set(0,-900,500); scene.add(under);

const ring=new THREE.Group(); scene.add(ring);
const stations=[];   // {grp, wp} — grp spreads radially, wp lifts the wafer

// binary STL -> BufferGeometry (flat-shaded CAD)
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

// stations first: the mirror wafers paint immediately, the canonical
// segment meshes drop in as soon as they arrive
const TINT=[0x0b0b0c,0x0d0d0e,0x0a0a0b,0x0c0c0d];
(function(){
  const wg=new THREE.CylinderGeometry(WR,WR,P.wt,110);
  for(let k=0;k<P.N;k++){
    const grp=new THREE.Group(); grp.rotation.z=k*SEG;
    const wm=new THREE.MeshPhongMaterial({color:0x767e88,shininess:95,
      specular:0xdde6f0,emissive:TINT[k%4],transparent:true});
    const w=new THREE.Mesh(wg,wm); w.rotation.x=Math.PI/2;
    const p=new THREE.Group(); p.add(w); p.position.set(P.R,0,0); p.rotation.x=TH;
    const wp=new THREE.Group(); wp.add(p); grp.add(wp);
    ring.add(grp);
    stations.push({grp,wp,wm,ca:Math.cos(k*SEG),sa:Math.sin(k*SEG)});
  }
})();

// pinion pivot at 12 o'clock (axis RADIAL = +y through the pivot)
const pinion=new THREE.Group();
pinion.position.set(0,345,zW+10.79);
scene.add(pinion);
const shaft=new THREE.Mesh(new THREE.CylinderGeometry(1.5,1.5,60,20),
  new THREE.MeshPhongMaterial({color:0x232830,shininess:70}));
shaft.position.y=33; pinion.add(shaft);
let pinSpin=null;                       // the spinning mesh, once loaded

(async function loadModels(){
  async function grab(file){
    try{
      const r=await fetch('models/'+file);
      if(!r.ok)throw 0;
      return await r.arrayBuffer();
    }catch(e){
      // file:// — pull the base64 bundle through a <script> tag
      if(!window.HALO_MODELS)
        await new Promise((res,rej)=>{const s=document.createElement('script');
          s.src='models/models_data.js';s.onload=res;s.onerror=rej;
          document.head.appendChild(s);});
      const bin=atob(window.HALO_MODELS.files[file]),u=new Uint8Array(bin.length);
      for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
      return u.buffer;
    }
  }
  try{
    const [segB,pinB]=await Promise.all([grab('segment.stl'),grab('pinion.stl')]);
    const segG=parseSTL(segB);
    const segM=new THREE.MeshPhongMaterial({color:0x3a4049,shininess:30,side:THREE.DoubleSide});
    for(const s of stations){
      const m=new THREE.Mesh(segG,segM);
      m.position.z=zW;                  // his frame: wall face z=0
      s.grp.add(m);
    }
    // his pinion export sits placed at a=0 (+x, axis x through z=10.79);
    // swing it to 12 o'clock and re-express about the pivot origin so it
    // spins about its own (radial, +y) axis
    const pg=parseSTL(pinB);
    pg.rotateZ(Math.PI/2);              // a=0 -> 12 o'clock (axis now +y)
    pg.translate(0,-345,-10.79);        // axis through the pivot origin
    const pm=new THREE.Mesh(pg,new THREE.MeshPhongMaterial({color:0x8b8f98,shininess:55,side:THREE.DoubleSide}));
    const wrap=new THREE.Group();
    wrap.add(pm); pinion.add(wrap);
    pinSpin=wrap;
  }catch(e){/* models missing: the wafers still carry the reel */}
})();

// ---- shots: camera orbits the LOOK point; scroll scrubs between keys ----
// {az,pol,dist,look,ex} — ex is the explode factor for THE BUILD
const KEYS=[
  {az:-1.12,pol:0.30,dist:1900,look:[0,-80,0],  ex:0},   // 0 TITLE
  {az:-0.58,pol:0.66,dist:1150,look:[0,40,0],   ex:0},   // 1 THE SWIRL
  {az:0.38,pol:1.24,dist:170, look:[0,338,zW+8],ex:0},   // 2 THE DRIVE (macro, grazing)
  {az:-1.57,pol:1.42,dist:1450,look:[0,0,10],   ex:0},   // 3 THE EDGE
  {az:-0.85,pol:0.72,dist:2300,look:[0,0,60],   ex:1},   // 4 THE BUILD
  {az:-1.12,pol:0.28,dist:2600,look:[0,-40,0],  ex:0},   // 5 CREDITS
];
const secs=Array.prototype.slice.call(document.querySelectorAll('[data-shot]'));
let anchors=[];
function measure(){
  anchors=secs.map(function(el){ return el.offsetTop; });
}
function ss(f){ return f*f*f*(f*(f*6-15)+10); }
function lerp(a,b,f){ return a+(b-a)*f; }
function camState(y){
  let i=0;
  while(i<anchors.length-1 && y>=anchors[i+1]) i++;
  const a0=anchors[i], a1=(i<anchors.length-1)?anchors[i+1]:a0+1;
  let f=(y-a0)/Math.max(1,a1-a0);
  f=ss(Math.min(1,Math.max(0,(f-0.35)/0.6)));   // hold each shot, then move
  const A=KEYS[Math.min(i,KEYS.length-1)], B=KEYS[Math.min(i+1,KEYS.length-1)];
  return {
    az:lerp(A.az,B.az,f), pol:lerp(A.pol,B.pol,f), dist:lerp(A.dist,B.dist,f),
    look:[lerp(A.look[0],B.look[0],f),lerp(A.look[1],B.look[1],f),lerp(A.look[2],B.look[2],f)],
    ex:lerp(A.ex,B.ex,f), shot:i, s:i+f
  };
}

// pointer parallax (whisper-level)
let pAz=0,pPol=0;
addEventListener('pointermove',function(e){
  pAz=(e.clientX/innerWidth*2-1)*0.06;
  pPol=(e.clientY/innerHeight*2-1)*0.03;
});

function resize(){
  const w=innerWidth,h=innerHeight;
  const dpr=Math.min(devicePixelRatio||1,1.75);
  renderer.setSize(Math.round(w*dpr),Math.round(h*dpr),false);
  camera.aspect=w/h; camera.updateProjectionMatrix();
  measure();
}
addEventListener('resize',resize);
resize();

// ---- HUD hooks (index.html owns the DOM) ----
const slate=document.getElementById('slateShot');
const angleEl=document.getElementById('slateAngle');
const ticks=Array.prototype.slice.call(document.querySelectorAll('.rail i'));
const NAMES=['TITLE','THE SWIRL','THE DRIVE','THE EDGE','THE BUILD','CREDITS'];
let lastShot=-1;

const still=matchMedia('(prefers-reduced-motion: reduce)').matches;
const PIN_W=0.75;  // pinion rad/s on screen — the MASTER (Nick's pick);
const RATIO=60;    // ring follows via the true 60:1, surface speeds match
let tPrev=0;
(function loop(t){
  requestAnimationFrame(loop);
  const dt=Math.min(t-tPrev,100)/1000; tPrev=t;
  if(!still){
    ring.rotation.z+=dt*PIN_W/RATIO;
    if(pinSpin)pinSpin.rotation.y+=dt*PIN_W;
    const a=t*0.00012;
    rim.position.set(-900*Math.cos(a),-250-300*Math.sin(a),350);
  }
  const st=camState(scrollY||window.pageYOffset||0);
  // explode: segments spread radially, wafers lift off their tape;
  // x-ray: wafers ghost fully on the drive mesh, half during the build
  const e=st.ex;
  const ghost=Math.max(Math.max(0,1-Math.abs(st.s-2))*0.92,
                       Math.max(0,1-Math.abs(st.s-4))*0.5);
  for(let k=0;k<stations.length;k++){
    const s=stations[k];
    s.grp.position.set(s.ca*e*150,s.sa*e*150,0);
    s.wp.position.z=e*150;
    s.wm.opacity=1-ghost;
  }
  pinion.visible=e<0.55;
  key.intensity=0.75+e*0.55;            // lift the prints out of the dark mid-explode
  document.body.classList.toggle('ending',st.shot>=5);
  const az=st.az+(still?0:pAz), pol=st.pol+(still?0:pPol);
  camera.position.set(
    st.look[0]+st.dist*Math.sin(pol)*Math.cos(az),
    st.look[1]+st.dist*Math.sin(pol)*Math.sin(az),
    st.look[2]+st.dist*Math.cos(pol));
  camera.lookAt(st.look[0],st.look[1],st.look[2]);
  renderer.render(scene,camera);
  // slate + rail
  if(st.shot!==lastShot){
    lastShot=st.shot;
    if(slate) slate.textContent='SHOT 0'+st.shot+' / 05 — '+NAMES[st.shot];
    for(let i=0;i<ticks.length;i++) ticks[i].className=(i<=st.shot)?'on':'';
  }
  if(angleEl){
    const deg=(ring.rotation.z*180/Math.PI)%360;
    angleEl.textContent='RING '+(deg<10?'00':deg<100?'0':'')+deg.toFixed(1)+'°';
  }
})(0);
})();
