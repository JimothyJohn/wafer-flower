// Wafer Halo — landing-page hero. A self-contained parametric render of the
// shipped Rev B.6 build (same surface rules as calc.js, frozen at the CAD
// defaults): nine tilted wafers on the segment ring with the 45° bevel band,
// turning at the true ~2 rpm. No fetch, no model bundle — first paint is
// instant and it works under file://. The exact checked solids live on
// viewer.html / customize.html.
'use strict';
(function(){
const canvas=document.getElementById('hero3d');
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
scene.fog=new THREE.Fog(0x08090b,1500,3200);
const camera=new THREE.PerspectiveCamera(38,2,1,6000);
camera.up.set(0,1,0);
scene.add(new THREE.AmbientLight(0x30343c,0.5));
const key=new THREE.DirectionalLight(0xfff4e0,0.75); key.position.set(280,700,520); scene.add(key);
const magenta=new THREE.DirectionalLight(0xc2497b,0.8); magenta.position.set(-900,-250,350); scene.add(magenta);
const teal=new THREE.DirectionalLight(0x1e9e8e,0.65); teal.position.set(800,-550,240); scene.add(teal);
const gold=new THREE.DirectionalLight(0xc9a227,0.5); gold.position.set(-250,800,160); scene.add(gold);
const blue=new THREE.DirectionalLight(0x4457c4,0.45); blue.position.set(0,-900,500); scene.add(blue);

const ring=new THREE.Group(); scene.add(ring);

// segment top/bottom/wall grid — one geometry instanced 9× by rotation
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

  for(let k=0;k<P.N;k++){
    const m=new THREE.Mesh(g,mat); m.rotation.z=k*SEG; ring.add(m);
    const f=new THREE.Mesh(fg,fmat); f.rotation.z=k*SEG; ring.add(f);
  }
})();

// wafers — the mirror-polish stars of the show; each carries a whisper of a
// different oxide-film tint so the ring shimmers as it turns
(function(){
  const wg=new THREE.CylinderGeometry(WR,WR,P.wt,110);
  const TINT=[0x14100a,0x120a10,0x0a0c16,0x0a1412];   // gold/magenta/blue/teal, dimmed
  for(let k=0;k<P.N;k++){
    const wm=new THREE.MeshPhongMaterial({color:0x767e88,shininess:95,
      specular:0xdde6f0,emissive:TINT[k%4]});
    const w=new THREE.Mesh(wg,wm); w.rotation.x=Math.PI/2;
    const p=new THREE.Group(); p.add(w); p.position.set(P.R,0,0); p.rotation.x=TH;
    const q=new THREE.Group(); q.add(p); q.rotation.z=k*SEG;
    ring.add(q);
  }
})();

// ---- camera: near-frontal wall view, slightly below and left of axis ----
let az=-1.12, pol=0.30, dist=1900;
let pAz=0, pPol=0;                     // pointer parallax targets
function placeCam(){
  const a=az+pAz, p=pol+pPol;
  camera.position.set(dist*Math.sin(p)*Math.cos(a),
                      dist*Math.sin(p)*Math.sin(a),
                      dist*Math.cos(p));
  camera.lookAt(0,-80,0);              // ring rides high; copy owns the lower third
}
addEventListener('pointermove',e=>{
  const nx=e.clientX/innerWidth*2-1, ny=e.clientY/innerHeight*2-1;
  pAz=nx*0.10; pPol=ny*0.05;
});
function resize(){
  const w=canvas.clientWidth, h=canvas.clientHeight;
  const dpr=Math.min(devicePixelRatio||1,1.75);
  renderer.setSize(Math.round(w*dpr),Math.round(h*dpr),false);
  camera.aspect=w/h; camera.updateProjectionMatrix();
}
addEventListener('resize',resize);
resize(); placeCam();

const still=matchMedia('(prefers-reduced-motion: reduce)').matches;
const RPM2=0.21;                        // rad/s — the real ~2 rpm
let tPrev=0;
(function loop(t){
  requestAnimationFrame(loop);
  const dt=Math.min(t-tPrev,100)/1000; tPrev=t;
  if(!still){
    ring.rotation.z+=dt*RPM2;
    // slow orbit of the magenta rim light: the iridescent sweep
    const a=t*0.00012;
    magenta.position.set(-900*Math.cos(a),-250-300*Math.sin(a),350);
  }
  placeCam();
  renderer.render(scene,camera);
})(0);
})();
