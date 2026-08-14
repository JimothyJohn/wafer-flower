// Wafer Halo — the showreel engine. One fixed full-viewport canvas renders a
// self-contained parametric build of NICK'S CANONICAL ARCHITECTURE
// (stl/mine, RE'd by scripts/mine_stl.py): nine tilted wafers on arched
// twin-wall towers over a 320–350 band, the 720-tooth FACE ring on the
// outer annulus, and the flat 12T spur pinion at 12 o'clock. Scroll scrubs
// a keyframed camera through five cinematic shots; the ring turn is a
// time-lapse (~2 rpm on screen; the real piece runs 0.25 rpm at 60:1).
// No fetch, no model bundle — first paint is instant and it works under
// file://. The exact checked solids live on viewer.html / customize.html.
'use strict';
(function(){
const canvas=document.getElementById('reel');
if(!canvas) return;
let renderer;
try{ renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true}); }
catch(e){ document.body.classList.add('nogl'); return; }
renderer.setClearColor(0x000000,0);

// ---- canonical architecture parameters (scripts/mine_stl.py defaults) ----
const P={D:300,wt:0.775,N:9,tilt:3,R:350,Ri:320,bw:30,bond:1.1};
const GRI=340, GEAR_F=6, ROOT_Z=3.84, BASE_H=9, SHOULDER=14;
const LAND_C=38.8, TOWER_A=7.5*Math.PI/180, WALL_T=4.4, CAP_Z=33;
const ARCH_Z=20.5, ARCH_A=0.6*Math.PI/180;
const TPS=80;                               // face-teeth per segment (720 ring)
const WR=P.D/2, SEG=2*Math.PI/P.N, H=Math.PI/P.N;
const TH=P.tilt*Math.PI/180, Ro=P.Ri+P.bw;
// world frame: wafer mid-plane ~z=0 (the old scene convention) — the wall
// face sits at zW, the tilted land at LAND(y)
const zW=-(LAND_C+P.bond+P.wt/2);
const LAND=function(y){ return zW+LAND_C+y*Math.tan(TH); };

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

// one segment = arc-box strips: base slab, toothed rim, shoulder, arched
// twin-wall tower, tilted cap. Built once, grouped 9×.
(function(){
  const pos=[], idx=[];
  // closed arc box [r0,r1]×[a0,a1]×[z0, topFn(y)] (topFn may be a constant)
  function strip(r0,r1,a0,a1,z0,top){
    const NA2=Math.max(2,Math.ceil((a1-a0)/0.02));
    const tf=(typeof top==='function')?top:function(){return top;};
    const start=pos.length/3;
    for(let j=0;j<=NA2;j++){
      const a=a0+(a1-a0)*j/NA2, c=Math.cos(a), s=Math.sin(a);
      const y0=r0*s, y1=r1*s;
      pos.push(r0*c,y0,tf(y0), r1*c,y1,tf(y1), r0*c,y0,z0, r1*c,y1,z0);
    }
    const q=function(a2,b,c2,d){ idx.push(a2,b,c2,a2,c2,d); };
    for(let j=0;j<NA2;j++){
      const A=start+j*4, B=start+(j+1)*4;
      q(A,B,B+1,A+1);       // top
      q(A+3,B+3,B+2,A+2);   // bottom
      q(A+2,B+2,B,A);       // inner wall
      q(A+1,B+1,B+3,A+3);   // outer wall
    }
    const A=start, B=start+NA2*4;
    q(A,A+1,A+3,A+2); q(B+2,B+3,B+1,B);   // end caps
  }
  // base slab + shoulder + toothed rim body
  strip(P.Ri,GRI,-H,H,zW,zW+BASE_H);
  strip(P.Ri,GRI,-12*Math.PI/180,12*Math.PI/180,zW+BASE_H,zW+SHOULDER);
  strip(GRI,Ro,-H,H,zW,zW+ROOT_Z);
  // face teeth: TPS radial ridges on the rim, root->tip
  const pitch=2*H/TPS;
  for(let t=0;t<TPS;t++){
    const ac=-H+(t+0.5)*pitch;
    strip(GRI+0.5,Ro,ac-pitch*0.24,ac+pitch*0.24,zW+ROOT_Z,zW+GEAR_F);
  }
  // tower: two walls, each split by the central arch (legs to ARCH_Z, a
  // bridge above it), then the cap slab up to the tilted land
  const walls=[[P.Ri,P.Ri+WALL_T],[GRI-WALL_T,GRI]];
  for(let w=0;w<2;w++){
    const r0=walls[w][0], r1=walls[w][1];
    strip(r0,r1,-TOWER_A,-ARCH_A,zW+SHOULDER,LAND);
    strip(r0,r1, ARCH_A, TOWER_A,zW+SHOULDER,LAND);
    strip(r0,r1,-ARCH_A, ARCH_A,zW+ARCH_Z,LAND);
  }
  strip(P.Ri,GRI,-TOWER_A,TOWER_A,zW+CAP_Z,LAND);
  const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
  g.setIndex(idx); g.computeVertexNormals();
  const mat=new THREE.MeshPhongMaterial({color:0x1c2026,shininess:24,side:THREE.DoubleSide});

  // wafers — the mirror-polish stars; each carries a whisper of a different
  // oxide-film tint so the ring shimmers as it turns
  const wg=new THREE.CylinderGeometry(WR,WR,P.wt,110);
  const TINT=[0x0b0b0c,0x0d0d0e,0x0a0a0b,0x0c0c0d];   // near-neutral — no oxide rainbow

  for(let k=0;k<P.N;k++){
    const grp=new THREE.Group(); grp.rotation.z=k*SEG;
    grp.add(new THREE.Mesh(g,mat));
    const wm=new THREE.MeshPhongMaterial({color:0x767e88,shininess:95,
      specular:0xdde6f0,emissive:TINT[k%4],transparent:true});
    const w=new THREE.Mesh(wg,wm); w.rotation.x=Math.PI/2;
    const p=new THREE.Group(); p.add(w); p.position.set(P.R,0,0); p.rotation.x=TH;
    const wp=new THREE.Group(); wp.add(p); grp.add(wp);
    ring.add(grp);
    stations.push({grp,wp,wm,ca:Math.cos(k*SEG),sa:Math.sin(k*SEG)});
  }
})();

// 12T flat spur pinion, schematic, fixed at 12 o'clock over the face ring
// (axis RADIAL — the motor points at the halo centre, lying on the wall)
const pinion=new THREE.Group();
(function(){
  const T=12, rTip=6.71, rRoot=4.79, LF=6;
  const NA=T*12, pos=[], idx=[];
  function wave(a){
    const p2=2*Math.PI/T, ph=((a%p2)+p2)%p2, f=ph/p2;
    if(f<0.10) return rRoot+(rTip-rRoot)*(f/0.10);
    if(f<0.44) return rTip;
    if(f<0.54) return rTip+(rRoot-rTip)*((f-0.44)/0.10);
    return rRoot;
  }
  for(let j=0;j<=NA;j++){
    const a=2*Math.PI*j/NA, r=wave(a);
    const c=Math.cos(a), s=Math.sin(a);
    pos.push(r*c,r*s,0, r*c,r*s,LF);
  }
  const nCap=pos.length/3;
  pos.push(0,0,0, 0,0,LF);
  for(let j=0;j<NA;j++){
    const A=j*2,B=(j+1)*2;
    idx.push(A,B,B+1, A,B+1,A+1);
    idx.push(A,nCap,B);
    idx.push(B+1,nCap+1,A+1);
  }
  const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
  g.setIndex(idx); g.computeVertexNormals();
  const m=new THREE.MeshPhongMaterial({color:0x3a4150,shininess:60,side:THREE.DoubleSide});
  const mesh=new THREE.Mesh(g,m);
  mesh.rotation.x=-Math.PI/2;              // spur axis → +y (radial at 12 o'clock)
  pinion.add(mesh);
  const shaft=new THREE.Mesh(new THREE.CylinderGeometry(1.5,1.5,90,24),
    new THREE.MeshPhongMaterial({color:0x232830,shininess:70}));
  shaft.position.y=48;
  pinion.add(shaft);
  // face width spans the tooth annulus middle; axis z = tip plane − m + rp
  pinion.position.set(0,345,zW+10.79);
  scene.add(pinion);
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
const RPM2=0.21;   // rad/s on screen — a time-lapse of the true 0.25 rpm
let tPrev=0;
(function loop(t){
  requestAnimationFrame(loop);
  const dt=Math.min(t-tPrev,100)/1000; tPrev=t;
  if(!still){
    ring.rotation.z+=dt*RPM2;
    // sense follows the rack (Nick 2026-08-16); heavily damped on
    // screen so the 12 teeth read as motion instead of strobe
    pinion.children[0].rotation.z+=dt*RPM2*1.2;
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
