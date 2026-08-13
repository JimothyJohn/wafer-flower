// Wafer Halo — the showreel engine. One fixed full-viewport canvas renders a
// self-contained parametric build of the shipped Rev B.6 geometry (same
// surface rules as calc.js, frozen at the CAD defaults): nine tilted wafers,
// the 45° bevel band, and a schematic 20T crossed pinion at 12 o'clock.
// Scroll scrubs a keyframed camera through five cinematic shots; the ring
// turns at the true ~2 rpm the whole time and the pinion counter-spins at
// 5.4:1. No fetch, no model bundle — first paint is instant and it works
// under file://. The exact checked solids live on viewer.html / customize.html.
'use strict';
(function(){
const canvas=document.getElementById('reel');
if(!canvas) return;
let renderer;
try{ renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true}); }
catch(e){ document.body.classList.add('nogl'); return; }
renderer.setClearColor(0x000000,0);

// ---- shipped Rev B.6 parameters (scripts/segment_stl.py defaults) ----
const P={D:300,wt:0.775,N:9,tilt:5,R:350,Ri:255,bw:30,tmin:15,bond:1.1};
const GEAR_F=9.5, GEAR_M=5.6, CLR=3;
const WR=P.D/2, SEG=2*Math.PI/P.N, H=Math.PI/P.N;
const TH=P.tilt*Math.PI/180, Ro=P.Ri+P.bw;

function planeZ(x,y,k){
  const a=k*SEG, tl=-Math.sin(a)*(x-P.R*Math.cos(a))+Math.cos(a)*(y-P.R*Math.sin(a));
  return tl*Math.tan(TH);
}
function inFootprint(x,y,k){
  const a=k*SEG, c=Math.cos(a), s=Math.sin(a);
  const xr=c*x+s*y-P.R, yt=(-s*x+c*y)/Math.cos(TH);
  return (xr*xr+yt*yt)<=WR*WR;
}
function gearSpec(){
  const target=Ro+1.25*GEAR_M+2;
  const tps=Math.max(6,Math.ceil(2*target/GEAR_M/P.N));
  const T=tps*P.N;
  const me=(Ro-1)/(T/2-1.25), rp=T*me/2;
  const kb=(rp+GEAR_F)/rp;
  return {tps,T,rp,tip:rp+me,root:rp-1.25*me,kb,web_i:Ro-2};
}
function toothWave(a,g){
  const pitch=2*Math.PI/g.T, ph=((a%pitch)+pitch)%pitch, f=ph/pitch;
  if(f<0.08) return g.root+(g.tip-g.root)*(f/0.08);
  if(f<0.46) return g.tip;
  if(f<0.54) return g.tip+(g.root-g.tip)*((f-0.46)/0.08);
  return g.root;
}
// z_bot with the crossed-pinion standoff (geoCtx in calc.js)
const Gz=gearSpec(), yMax=Ro*Math.sin(H);
const rhoZ=8, faceP=7;
const apexZ=(Gz.tip*Gz.kb-faceP/2)-rhoZ;
const bulge=GEAR_F/2+rhoZ*1.1+(Gz.tip*Gz.kb-apexZ)*1.1;
const gap0=yMax*Math.tan(TH)+P.bond+P.tmin-(P.wt/2+WR*Math.sin(TH));
const STAND=Math.max(0,bulge+3-gap0);
const zBot=-(yMax*Math.tan(TH)+P.bond+P.tmin+STAND);
function topZ(x,y){
  if(!inFootprint(x,y,0)) return zBot+2;
  let z=planeZ(x,y,0)-P.wt/2-P.bond;
  if(inFootprint(x,y,1)) z=Math.min(z, planeZ(x,y,1)-P.wt/2-CLR);
  return Math.max(z,zBot+1);
}

// ---- scene ----
const scene=new THREE.Scene();
scene.fog=new THREE.Fog(0x08090b,1500,3400);
const camera=new THREE.PerspectiveCamera(38,2,1,7000);
camera.up.set(0,1,0);
scene.add(new THREE.AmbientLight(0x30343c,0.55));
const key=new THREE.DirectionalLight(0xfff4e0,0.75); key.position.set(280,700,520); scene.add(key);
const magenta=new THREE.DirectionalLight(0xc2497b,0.8); magenta.position.set(-900,-250,350); scene.add(magenta);
const teal=new THREE.DirectionalLight(0x1e9e8e,0.65); teal.position.set(800,-550,240); scene.add(teal);
const gold=new THREE.DirectionalLight(0xc9a227,0.5); gold.position.set(-250,800,160); scene.add(gold);
const blue=new THREE.DirectionalLight(0x4457c4,0.45); blue.position.set(0,-900,500); scene.add(blue);

const ring=new THREE.Group(); scene.add(ring);
const stations=[];   // {grp, wp} — grp spreads radially, wp lifts the wafer

// segment top/bottom/wall grid + bevel band — one geometry each, grouped 9×
(function(){
  const NR=20, NA=80, pos=[], idx=[];
  for(let pass=0;pass<2;pass++)
    for(let i=0;i<=NR;i++)for(let j=0;j<=NA;j++){
      const rho=P.Ri+P.bw*i/NR, a=-H+2*H*j/NA;
      const x=rho*Math.cos(a), y=rho*Math.sin(a);
      pos.push(x,y,pass?zBot:topZ(x,y));
    }
  const base=(NR+1)*(NA+1);
  const quad=(a,b,c,d)=>{idx.push(a,b,c,a,c,d);};
  for(let i=0;i<NR;i++)for(let j=0;j<NA;j++){
    const A=i*(NA+1)+j;
    quad(A,A+1,A+NA+2,A+NA+1);
    const B=base+A; quad(B+NA+1,B+NA+2,B+1,B);
  }
  for(let j=0;j<NA;j++){
    const A=j,B=base+j; quad(B,B+1,A+1,A);
    const C=NR*(NA+1)+j,D=base+NR*(NA+1)+j; quad(C,C+1,D+1,D);
  }
  for(let i=0;i<NR;i++){
    const A=i*(NA+1),B=base+i*(NA+1); quad(A,A+NA+1,B+NA+1,B);
    const C=i*(NA+1)+NA,D=base+i*(NA+1)+NA; quad(D,D+NA+1,C+NA+1,C);
  }
  const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
  g.setIndex(idx); g.computeVertexNormals();
  const mat=new THREE.MeshPhongMaterial({color:0x1c2026,shininess:24,side:THREE.DoubleSide});

  // bevel tooth band: schematic wave lofted on the 45° cone (calc.js)
  const G=gearSpec();
  const fPos=[], fIdx=[], NF=Math.max(64,G.tps*10);
  for(let j=0;j<=NF;j++){
    const a=-H+2*H*j/NF, rf=toothWave(a,G), rw=toothWave(a,G)*G.kb, ri=G.web_i;
    const c=Math.cos(a), s=Math.sin(a);
    fPos.push(ri*c,ri*s,zBot+GEAR_F, rf*c,rf*s,zBot+GEAR_F,
              ri*c,ri*s,zBot,        rw*c,rw*s,zBot);
  }
  const fq=(a,b,c,d)=>{fIdx.push(a,b,c,a,c,d);};
  for(let j=0;j<NF;j++){
    const A=j*4, B=(j+1)*4;
    fq(A,A+1,B+1,B); fq(A+3,A+2,B+2,B+3); fq(A+2,A,B,B+2); fq(A+1,A+3,B+3,B+1);
  }
  const fg=new THREE.BufferGeometry();
  fg.setAttribute('position',new THREE.Float32BufferAttribute(fPos,3));
  fg.setIndex(fIdx); fg.computeVertexNormals();
  const fmat=new THREE.MeshPhongMaterial({color:0x2b313a,shininess:42,side:THREE.DoubleSide});

  // wafers — the mirror-polish stars; each carries a whisper of a different
  // oxide-film tint so the ring shimmers as it turns
  const wg=new THREE.CylinderGeometry(WR,WR,P.wt,110);
  const TINT=[0x14100a,0x120a10,0x0a0c16,0x0a1412];   // gold/magenta/blue/teal, dimmed

  for(let k=0;k<P.N;k++){
    const grp=new THREE.Group(); grp.rotation.z=k*SEG;
    grp.add(new THREE.Mesh(g,mat));
    grp.add(new THREE.Mesh(fg,fmat));
    const wm=new THREE.MeshPhongMaterial({color:0x767e88,shininess:95,
      specular:0xdde6f0,emissive:TINT[k%4],transparent:true});
    const w=new THREE.Mesh(wg,wm); w.rotation.x=Math.PI/2;
    const p=new THREE.Group(); p.add(w); p.position.set(P.R,0,0); p.rotation.x=TH;
    const wp=new THREE.Group(); wp.add(p); grp.add(wp);
    ring.add(grp);
    stations.push({grp,wp,wm,ca:Math.cos(k*SEG),sa:Math.sin(k*SEG)});
  }
})();

// 20T crossed pinion, schematic, fixed at 12 o'clock (does not ride the ring)
const pinion=new THREE.Group();
(function(){
  const T=20, depth=2.25, slope=1.1, LF=7;
  const RB=10.4;                       // big-end root; tips Ø25.3 → Ø9.9
  const spec={T:T,tip:1,root:0};
  const NA=T*12, pos=[], idx=[];
  for(let j=0;j<=NA;j++){
    const a=2*Math.PI*j/NA, w=toothWave(a,spec);
    const c=Math.cos(a), s=Math.sin(a);
    const r0=RB+w*depth, r1=(RB-slope*LF)+w*depth;
    pos.push(r0*c,r0*s,0, r1*c,r1*s,LF);
  }
  const nCap=pos.length/3;
  pos.push(0,0,0, 0,0,LF);
  for(let j=0;j<NA;j++){
    const A=j*2,B=(j+1)*2;
    idx.push(A,B,B+1, A,B+1,A+1);          // flank wall
    idx.push(A,nCap,B);                    // big-end cap
    idx.push(B+1,nCap+1,A+1);              // small-end cap
  }
  const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
  g.setIndex(idx); g.computeVertexNormals();
  const m=new THREE.MeshPhongMaterial({color:0x3a4150,shininess:60,side:THREE.DoubleSide});
  const mesh=new THREE.Mesh(g,m);
  mesh.rotation.x=Math.PI/2;               // cone axis → −y, big end down
  pinion.add(mesh);
  const shaft=new THREE.Mesh(new THREE.CylinderGeometry(1.7,1.7,150,24),
    new THREE.MeshPhongMaterial({color:0x232830,shininess:70}));
  shaft.position.y=80;
  pinion.add(shaft);
  // small end down, tangent to the band cone at 12 o'clock:
  // band silhouette z = zBot + (wall-tip radius − y); pinion lower edge
  // z = zc − (RS + slope·(y − y_small)) — meet them at mid-face
  pinion.position.set(0,303,zBot+15.3);
  scene.add(pinion);
})();

// ---- shots: camera orbits the LOOK point; scroll scrubs between keys ----
// {az,pol,dist,look,ex} — ex is the explode factor for THE BUILD
const KEYS=[
  {az:-1.12,pol:0.30,dist:1900,look:[0,-80,0],  ex:0},   // 0 TITLE
  {az:-0.58,pol:0.66,dist:1150,look:[0,40,0],   ex:0},   // 1 THE SWIRL
  {az:0.38,pol:1.24,dist:170, look:[0,296,zBot+12],ex:0}, // 2 THE DRIVE (macro, grazing)
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
const RPM2=0.21;                        // rad/s — the real ~2 rpm
let tPrev=0;
(function loop(t){
  requestAnimationFrame(loop);
  const dt=Math.min(t-tPrev,100)/1000; tPrev=t;
  if(!still){
    ring.rotation.z+=dt*RPM2;
    pinion.children[0].rotation.z-=dt*RPM2*(108/20);   // 5.4:1, counter
    const a=t*0.00012;
    magenta.position.set(-900*Math.cos(a),-250-300*Math.sin(a),350);
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
