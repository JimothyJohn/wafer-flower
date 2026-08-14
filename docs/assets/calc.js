// Wafer Halo — live parametric calculator + statics + STL preview export.
// Shared by customize.html and engineering.html. Expects the calculator
// markup block: canvas#cviz, #alert, #viewnote, the i_*/o_* sliders,
// r_*/s_* readouts, and the STL bar (#b_stl, #cadcmd, #b_copy).
// Self-contained (no fetch) — works under file:// as-is.
//
// REBUILT 2026-08-16 around NICK'S CANONICAL ARCHITECTURE (stl/mine,
// scripts/mine_stl.py): band Ri..Ro with a 10 mm face-tooth annulus at
// the rim, arched twin-wall tower carrying the tilted land, 12T spur
// pinion on a radial axis. Every slider re-derives THIS geometry — the
// legacy solid-band model (and its shipped-CAD boot special case, which
// broke the moment the manifest format changed) is gone. The coarse
// preview mesh here mirrors mine_stl's coarse tower; exact solids live
// on viewer.html.
'use strict';
(function(){
// ---- units: mm, N, MPa, g(mass), K ----
const G_ACC=9.81;
const SI ={rho:2.329e-3, E:130000, cte:2.6e-6};   // g/mm3, MPa, /K
const PLA={rho:1.240e-3, E:2300, allow:20, cte:70e-6};
const CLR=3;                     // neighbour clearance target, mm
const PLATE=0.922;               // wafer plate stiffening (1-nu^2)
// fixed architecture constants (mine_stl PARAMS not worth sliders)
const ANN_W=10;                  // tooth annulus width (gri = Ro - ANN_W)
const BASE_H=9, WALL_T=4.4, CAP_T=5.8, N20_RPM=15, PIN_T=12, M_REF=0.95833;

const canvas=document.getElementById('cviz');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true});
const scene=new THREE.Scene(); scene.background=new THREE.Color(0x0E1013);
const camera=new THREE.PerspectiveCamera(40,2,1,8000);
scene.add(new THREE.AmbientLight(0xffffff,0.45));
const key=new THREE.DirectionalLight(0xfff2e2,0.9); key.position.set(400,600,800); scene.add(key);
const fill=new THREE.DirectionalLight(0xaeb6c2,0.35); fill.position.set(-500,-200,400); scene.add(fill);

let az=0.6, pol=1.05, dist=1500, group=new THREE.Group(); scene.add(group);
let view='assembly', autoDist=true;
const ANIM={ring:null, pin:null, ratio:60};
const PIN_W=0.75;                // pinion rad/s on screen — the MASTER; the ring derives via the true ratio
function placeCam(){
  camera.position.set(dist*Math.sin(pol)*Math.cos(az), dist*Math.sin(pol)*Math.sin(az), dist*Math.cos(pol));
  camera.up.set(0,0,1); camera.lookAt(0,0,0);
}
let drag=false,px=0,py=0;
canvas.addEventListener('pointerdown',e=>{drag=true;px=e.clientX;py=e.clientY;canvas.setPointerCapture(e.pointerId);});
canvas.addEventListener('pointermove',e=>{if(!drag)return;az-=(e.clientX-px)*0.008;pol=Math.min(2.6,Math.max(0.3,pol-(e.clientY-py)*0.008));px=e.clientX;py=e.clientY;placeCam();});
canvas.addEventListener('pointerup',()=>drag=false);
canvas.addEventListener('wheel',e=>{e.preventDefault();autoDist=false;dist=Math.min(5000,Math.max(120,dist*(1+e.deltaY*0.001)));placeCam();},{passive:false});

// boots at the CANONICAL parameters (stl/mine): first render is the real design
const CANON={D:300,wt:0.775,N:9,tilt:3,R:350,Ri:320,bw:30,land:38.8,bond:1.1,G:0.06,dT:20,dens:10};
const P=Object.assign({},CANON);
const WR=()=>P.D/2, SEG=()=>2*Math.PI/P.N, HALF=()=>Math.PI/P.N;
const Rout=()=>P.Ri+P.bw, GRI=()=>Rout()-ANN_W;

// derived drive: tooth count quantised in steps of N, module retuned
function gearSpec(){
  const rref=(GRI()+Rout())/2;
  const tps=Math.max(12,Math.round(2*rref/M_REF/P.N));
  const T=tps*P.N, m=2*rref/T;
  const ratio=T/PIN_T, rp=PIN_T*m/2;
  return {tps,T,m,ratio,rp,rTip:rp+m,rRoot:rp-1.25*m,rpm:N20_RPM/ratio};
}
// tower vertical layout, derived from the land height
function towerSpec(){
  const gearF=6*1, rootZ=gearF-2.25*gearSpec().m;
  const shoulder=Math.min(14,P.land*0.36);
  return {gearF,rootZ:Math.max(1,rootZ),shoulder,
          capZ:Math.max(shoulder+4,P.land-CAP_T),
          archZ:Math.max(shoulder+3,P.land*0.53),
          twr:7.5*Math.PI/180, archA:0.6*Math.PI/180};
}

// wafer k's mid-plane z at global (x,y); tilt about its radial axis
function planeZ(x,y,k,th){
  const a=k*SEG(), tl=-Math.sin(a)*(x-P.R*Math.cos(a))+Math.cos(a)*(y-P.R*Math.sin(a));
  return tl*Math.tan(th);
}
function inFootprint(x,y,k,th){
  const a=k*SEG(), c=Math.cos(a), s=Math.sin(a);
  const xr=c*x+s*y-P.R, yt=(-s*x+c*y)/Math.cos(th);
  return (xr*xr+yt*yt)<=WR()*WR();
}
function hideWindow(th){                 // radial coverage at the joint meridian
  const m=HALF(), b=WR()*Math.cos(th);
  const f=p=>Math.pow((p*Math.cos(m)-P.R)/WR(),2)+Math.pow(p*Math.sin(m)/b,2)-1;
  const bis=(lo,hi)=>{for(let i=0;i<60;i++){const md=(lo+hi)/2;(f(lo)*f(md)<=0)?hi=md:lo=md;}return (lo+hi)/2;};
  return [bis(Math.max(1,P.R-WR()),P.R), bis(P.R,P.R+WR())];
}

// ---- bond pad: the TOWER CAP under the wafer -----------------------------
// Same integral discipline as ever, over the cap footprint [Ri, gri] x
// +/-twr; the neighbour clearance plane still kills cells it dips under.
function landStats(th){
  const ts=towerSpec(), NRi=30, NAi=60, gri=GRI();
  const drho=(gri-P.Ri)/NRi, da=2*ts.twr/NAi, cells=[];
  let A=0,Su=0,Sv=0;
  for(let i=0;i<NRi;i++)for(let j=0;j<NAi;j++){
    const rho=P.Ri+drho*(i+0.5), a=-ts.twr+da*(j+0.5);
    const x=rho*Math.cos(a), y=rho*Math.sin(a);
    if(!inFootprint(x,y,0,th)) continue;
    const zOwn=planeZ(x,y,0,th)-P.wt/2-P.bond;
    if(inFootprint(x,y,1,th) && planeZ(x,y,1,th)-P.wt/2-CLR < zOwn) continue;
    const dA=rho*drho*da;
    const u=x-P.R, v=y/Math.cos(th);
    A+=dA; Su+=u*dA; Sv+=v*dA; cells.push([u,v,dA]);
  }
  if(A<=0) return null;
  const cu=Su/A, cv=Sv/A, d=Math.hypot(cu,cv);
  const ex=d>1e-9?-cu/d:1, ey=d>1e-9?-cv/d:0;
  let I=0,cmax=0,Lmax=0;
  for(const c of cells){
    const s=(c[0]-cu)*ex+(c[1]-cv)*ey;
    I+=s*s*c[2]; if(Math.abs(s)>cmax)cmax=Math.abs(s);
    const L=Math.hypot(c[0]-cu,c[1]-cv); if(L>Lmax)Lmax=L;
  }
  return {A,cu,cv,d,S:cmax>0?I/cmax:1e-9,Lmax,rc:Math.hypot(P.R+cu,cv)};
}

// ---- segment mesh: arc-box strips (mirrors mine_stl's coarse tower) ------
// Also accumulates volume + surface area analytically for the mass model,
// and doubles as the STL preview export (every strip is a closed box).
function buildSegmentBody(){
  const th=P.tilt*Math.PI/180, H=HALF(), ts=towerSpec(), gs=gearSpec();
  const Ro=Rout(), gri=GRI();
  const zBot=-(P.wt/2+P.bond+P.land);
  const LAND=y=>zBot+P.land+y*Math.tan(th);
  const pos=[], idx=[]; let vol=0, area=0;
  function strip(r0,r1,a0,a1,z0,top){
    const n=Math.max(2,Math.ceil((a1-a0)/0.02));
    const tf=(typeof top==='function')?top:(()=>top);
    const start=pos.length/3;
    for(let j=0;j<=n;j++){
      const a=a0+(a1-a0)*j/n, c=Math.cos(a), s=Math.sin(a);
      const y0=r0*s, y1=r1*s;
      pos.push(r0*c,y0,tf(y0), r1*c,y1,tf(y1), r0*c,y0,z0, r1*c,y1,z0);
    }
    const q=(a2,b,c2,d)=>{idx.push(a2,b,c2,a2,c2,d);};
    for(let j=0;j<n;j++){
      const A=start+j*4, B=start+(j+1)*4;
      q(A,B,B+1,A+1); q(A+3,B+3,B+2,A+2); q(A+2,B+2,B,A); q(A+1,B+1,B+3,A+3);
    }
    const A=start, B=start+n*4;
    q(A,A+1,A+3,A+2); q(B+2,B+3,B+1,B);
    // analytic accumulators (mean height x annular sector)
    const hMid=((typeof top==='function')?(tf(r0*Math.sin((a0+a1)/2))+tf(r1*Math.sin((a0+a1)/2)))/2:top)-z0;
    const aSec=0.5*(r1*r1-r0*r0)*(a1-a0), arc=(a1-a0)*(r0+r1)/2;
    vol+=hMid*aSec;
    area+=2*aSec+2*arc*hMid+2*(r1-r0)*hMid;
  }
  strip(P.Ri,gri,-H+1e-4,H-1e-4,zBot,zBot+BASE_H);
  strip(P.Ri,gri,-Math.min(12*Math.PI/180,H*0.6),Math.min(12*Math.PI/180,H*0.6),zBot+BASE_H,zBot+ts.shoulder);
  strip(gri,Ro,-H+1e-4,H-1e-4,zBot,zBot+ts.rootZ);
  const pitch=2*H/gs.tps;                      // face teeth on the rim
  for(let t=0;t<gs.tps;t++){
    const ac=-H+(t+0.5)*pitch;
    strip(gri+0.5,Ro,ac-pitch*0.24,ac+pitch*0.24,zBot+ts.rootZ,zBot+ts.gearF);
  }
  for(const w of [[P.Ri,P.Ri+WALL_T],[gri-WALL_T,gri]]){
    strip(w[0],w[1],-ts.twr,-ts.archA,zBot+ts.shoulder,LAND);
    strip(w[0],w[1], ts.archA, ts.twr,zBot+ts.shoulder,LAND);
    strip(w[0],w[1],-ts.archA, ts.archA,zBot+ts.archZ,LAND);
  }
  strip(P.Ri,gri,-ts.twr,ts.twr,zBot+ts.capZ,LAND);
  return {pos,idx,vol,area,zBot,th,H,Ro,gri,ts,gs};
}

// ---- schematic 12T spur pinion (radial axis at 12 o'clock) ---------------
function pinionMesh(gs,zBot,ts){
  const NA=PIN_T*12, pos=[], idx=[];
  const wave=a=>{
    const p2=2*Math.PI/PIN_T, ph=((a%p2)+p2)%p2, f=ph/p2;
    if(f<0.10) return gs.rRoot+(gs.rTip-gs.rRoot)*(f/0.10);
    if(f<0.44) return gs.rTip;
    if(f<0.54) return gs.rTip+(gs.rRoot-gs.rTip)*((f-0.44)/0.10);
    return gs.rRoot;
  };
  const LF=6;
  for(let j=0;j<=NA;j++){
    const a=2*Math.PI*j/NA, r=wave(a);
    pos.push(r*Math.cos(a),r*Math.sin(a),0, r*Math.cos(a),r*Math.sin(a),LF);
  }
  const nCap=pos.length/3; pos.push(0,0,0, 0,0,LF);
  for(let j=0;j<NA;j++){
    const A=j*2,B=(j+1)*2;
    idx.push(A,B,B+1, A,B+1,A+1, A,nCap,B, B+1,nCap+1,A+1);
  }
  const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
  g.setIndex(idx); g.computeVertexNormals();
  const grp=new THREE.Group();
  const mesh=new THREE.Mesh(g,new THREE.MeshPhongMaterial({color:0x8B8F98,shininess:55,side:THREE.DoubleSide}));
  mesh.rotation.x=-Math.PI/2;                // spur axis -> +y (radial)
  grp.add(mesh);
  const shaft=new THREE.Mesh(new THREE.CylinderGeometry(1.5,1.5,60,20),
    new THREE.MeshPhongMaterial({color:0x3A3F46,shininess:60}));
  shaft.position.y=33; grp.add(shaft);
  const rref=(GRI()+Rout())/2;
  grp.position.set(0,rref,zBot+ts.gearF-gs.m+gs.rp);
  return grp;
}

function buildScene(){
  while(group.children.length) group.remove(group.children[0]);
  ANIM.ring=null; ANIM.pin=null;
  const body=buildSegmentBody();
  const th=body.th, zBot=body.zBot, N=P.N;
  const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.Float32BufferAttribute(body.pos,3));
  g.setIndex(body.idx); g.computeVertexNormals();
  const segMat=new THREE.MeshPhongMaterial({color:0x77808C,shininess:30,side:THREE.DoubleSide});

  const full=(view==='assembly'||view==='drive');
  const nSeg=full?N:1;
  const nWaf=full?N:(view!=='frame'?1:0);
  const rg=new THREE.Group(); group.add(rg);
  for(let k=0;k<nSeg;k++){
    const m=new THREE.Mesh(g,segMat); m.rotation.z=k*SEG(); rg.add(m);
  }
  const wg=new THREE.CylinderGeometry(WR(),WR(),P.wt,72);
  const wm=new THREE.MeshPhongMaterial({color:0x9AA0A8,shininess:95,specular:0xBFC9D4});
  for(let k=0;k<nWaf;k++){
    const w=new THREE.Mesh(wg,wm); w.rotation.x=Math.PI/2;
    const p=new THREE.Group(); p.add(w); p.position.set(P.R,0,0); p.rotation.x=th;
    const q=new THREE.Group(); q.add(p); q.rotation.z=k*SEG();
    rg.add(q);
  }
  if(view==='drive'||view==='assembly'){
    const pin=pinionMesh(body.gs,zBot,body.ts);
    group.add(pin);
    if(view==='drive'){ANIM.ring=rg; ANIM.pin=pin.children[0]; ANIM.ratio=body.gs.ratio;}
  }
  frameView(th,zBot);
  viewNote(body);
  readouts(body);
  document.getElementById('cadcmd').textContent=cadCmd();
}

function frameView(th,zBot){
  const r=WR(); let cx=0,cy=0,cz=0,extent;
  if(view==='assembly'){
    extent=P.R+r*Math.cos(th)+40;
  }else if(view==='drive'){
    cy=P.R*0.38; extent=(P.R+r*Math.cos(th)+40)*0.72;
  }else if(view==='station'){
    cx=P.R; cz=-25; extent=r*1.15;
  }else{
    cx=(P.Ri+Rout())/2; cz=zBot/2;
    extent=Math.max(P.bw*2, 2*Rout()*Math.sin(HALF()))*0.72;
  }
  group.position.set(-cx,-cy,-cz);
  if(autoDist){
    dist=extent/Math.tan(camera.fov*Math.PI/360)*1.25;
    placeCam();
  }
}

// ---- mass: skin-calibrated model, pinned to the sliced canonical ---------
// m = rho*(skin + K_INF*infill*(vol-skin)), skin ~ T_SKIN*area; CAL makes
// the canonical parameter set land exactly on the sliced 51.64 g @10%.
const T_SKIN=1.05, K_INF=0.92;
function segMass(vol,area,densPct){
  const vSkin=Math.min(vol,T_SKIN*area);
  return PLA.rho*(vSkin+K_INF*(densPct/100)*(vol-vSkin));
}
const CAL=(function(){
  const save=Object.assign({},P); Object.assign(P,CANON);
  const b=buildSegmentBody(); const m0=segMass(b.vol,b.area,10);
  Object.assign(P,save);
  return 51.64/m0;
})();

function readouts(body){
  const th=body.th, H=HALF(), N=P.N, r=WR(), Ro=body.Ro, gs=body.gs, ts=body.ts;
  const set=(id,v,cls)=>{const e=document.getElementById(id);if(!e)return;e.textContent=v;e.className='v'+(cls?' '+cls:'');};
  const alerts=[];
  // geometry
  const hw=hideWindow(th), hi=hw[0], ho=hw[1];
  const chord=2*P.R*Math.sin(H);
  const bandOK=(P.Ri>=hi-0.5)&&(Ro<=ho+0.5);
  const overlap=2*r*Math.cos(th)-chord;
  set('r_od',(2*(P.R+r*Math.cos(th))).toFixed(0)+' mm');
  set('r_depth',(P.land+P.bond+P.wt+r*Math.sin(th)).toFixed(0)+' mm');
  set('r_swing','±'+(r*Math.sin(th)).toFixed(1)+' mm');
  set('r_hide',hi.toFixed(0)+' – '+ho.toFixed(0)+' mm');
  set('r_bandok',bandOK?'HIDDEN ✓':'FRAME VISIBLE ✗',bandOK?'ok':'bad');
  set('r_ovl',overlap.toFixed(1)+' mm',overlap>5?'ok':'bad');
  set('r_gap',(2*hi*Math.sin(H)*Math.tan(th)).toFixed(1)+' mm');
  set('r_tmax',(P.land+GRI()*Math.sin(ts.twr)*Math.tan(th)).toFixed(1)+' mm');
  set('r_land',(2*ts.twr*180/Math.PI).toFixed(0)+'° of '+(360/N).toFixed(0)+'°');
  set('r_gear',gs.tps+'T×'+N+' = '+gs.T+'T face ring · m '+gs.m.toFixed(3)+' · '+PIN_T+'T pinion');
  const gearHidden=Ro<=ho+0.5;
  set('r_gearok',(gearHidden?'HIDDEN ✓ −':'VISIBLE ✗ +')+Math.abs(ho-Ro).toFixed(0)+' mm',gearHidden?'ok':'bad');
  if(!bandOK) alerts.push('⚠ Band ['+P.Ri.toFixed(0)+'–'+Ro.toFixed(0)+'] exits the hide window ['+hi.toFixed(0)+'–'+ho.toFixed(0)+'] — frame shows between wafers.');
  if(overlap<=0) alerts.push('⚠ No neighbour overlap ('+overlap.toFixed(1)+' mm): the wafers do not swirl. Reduce R or N, or raise Ø.');
  // statics
  const L=landStats(th);
  const m_w=SI.rho*Math.PI*r*r*P.wt, W_w=m_w*G_ACC/1000;
  const m_f=segMass(body.vol,body.area,P.dens)*CAL;
  const m_tot=N*(m_w+m_f), W_tot=m_tot*G_ACC/1000;
  set('s_wm',m_w.toFixed(1)+' g / '+W_w.toFixed(2)+' N');
  set('s_fm',m_f.toFixed(1)+' g');
  set('s_tot',(m_tot/1000).toFixed(2)+' kg / '+W_tot.toFixed(1)+' N');
  if(!L){
    ['r_area','s_off','s_tau','s_peel','s_th','s_gam','s_ovh','s_droop','s_sig'].forEach(id=>set(id,'no pad','bad'));
    alerts.push('⚠ The tower pad has no bondable area under the wafer — widen the band or move it inboard.');
  } else {
    const W_n=W_w*Math.sin(th), W_s=W_w*Math.cos(th);
    const tau=W_s/L.A*1000, peel=(W_n*L.d)/L.S*1000;
    const slip=(PLA.cte-SI.cte)*P.dT*L.Lmax, gam=slip/P.bond;
    const tau_th=P.G*gam*1000;
    set('r_area',(L.A/100).toFixed(0)+' cm²');
    set('s_off',L.d.toFixed(0)+' mm (pad r='+L.rc.toFixed(0)+')', L.d<25?'ok':(L.d<60?'warn':'bad'));
    set('s_tau',tau.toFixed(2)+' kPa','ok');
    set('s_peel',peel.toFixed(2)+' kPa',peel<10?'ok':(peel<40?'warn':'bad'));
    set('s_th',tau_th.toFixed(1)+' kPa',tau_th<20?'ok':(tau_th<80?'warn':'bad'));
    set('s_gam',(gam*100).toFixed(1)+' %',gam<0.15?'ok':(gam<0.3?'warn':'bad'));
    if(tau_th>80) alerts.push('⚠ Thermal shear '+tau_th.toFixed(0)+' kPa — thicker/softer bond, or a smaller pad.');
    const Lo=Math.max(0,(P.R+r)-GRI());
    const q=SI.rho*P.wt*G_ACC*1e-3;
    const Sm=P.wt*P.wt/6, Im=Math.pow(P.wt,3)/12;
    const sigFlat=q*Lo*Lo/2/Sm, sigHung=sigFlat*Math.sin(th);
    const dFlat=q*Math.pow(Lo,4)/(8*SI.E*Im)*PLATE, dHung=dFlat*Math.sin(th);
    set('s_ovh',Lo.toFixed(0)+' mm');
    set('s_droop',dHung.toFixed(2)+' / '+dFlat.toFixed(2)+' mm',dHung<CLR/3?'ok':'warn');
    set('s_sig',sigHung.toFixed(2)+' / '+sigFlat.toFixed(2)+' MPa',sigFlat<10?'ok':'warn');
    if(dHung>CLR/3) alerts.push('⚠ Tip droop '+dHung.toFixed(2)+' mm eats >1/3 of the '+CLR+' mm neighbour clearance.');
  }
  const M_j=W_tot*P.R/Math.PI;
  set('s_mj',(M_j/1000).toFixed(2)+' N·m');
  set('s_dt',gs.ratio.toFixed(0)+':1 · '+gs.rpm.toFixed(2)+' rpm ('+N20_RPM+' rpm N20)','ok');
  const zcg=(N*m_f*((body.zBot+P.land*0.45))+N*m_w*(-P.wt/2))/(m_tot||1);
  set('s_zcg',zcg.toFixed(1)+' mm / '+(W_tot*Math.abs(zcg)/1000).toFixed(2)+' N·m');

  const al=document.getElementById('alert');
  if(alerts.length){al.style.display='block';al.innerHTML=alerts.map(a=>'<div>'+a+'</div>').join('');}
  else al.style.display='none';
}

// ---- CAD command + STL preview export ------------------------------------
function cadCmd(){
  const f=v=>String(+(+v).toFixed(3));
  const gs=gearSpec();
  return 'python scripts/mine_stl.py --N '+P.N+' --tilt '+f(P.tilt)+
    ' --Ri '+f(P.Ri)+' --Ro '+f(Rout())+' --gri '+f(GRI())+
    ' --tps '+gs.tps+' --land_c '+f(P.land)+
    ' --wafer_D '+f(P.D)+' --wafer_T '+f(P.wt)+' --R '+f(P.R)+' --bond '+f(P.bond);
}
function downloadSTL(){
  const b=buildSegmentBody();
  const tris=b.idx.length/3;
  const buf=new ArrayBuffer(84+50*tris), dv=new DataView(buf);
  const hdr='Wafer Halo segment preview (coarse) '+cadCmd().slice(7,80);
  for(let i=0;i<Math.min(80,hdr.length);i++) dv.setUint8(i,hdr.charCodeAt(i)&0x7F);
  dv.setUint32(80,tris,true);
  let o=84; const p=b.pos, ix=b.idx;
  for(let i=0;i<ix.length;i+=3){
    const a=ix[i]*3,c2=ix[i+1]*3,c3=ix[i+2]*3;
    const ux=p[c2]-p[a],uy=p[c2+1]-p[a+1],uz=p[c2+2]-p[a+2];
    const vx=p[c3]-p[a],vy=p[c3+1]-p[a+1],vz=p[c3+2]-p[a+2];
    let nx=uy*vz-uz*vy, ny=uz*vx-ux*vz, nz=ux*vy-uy*vx;
    const l=Math.hypot(nx,ny,nz)||1; nx/=l;ny/=l;nz/=l;
    dv.setFloat32(o,nx,true);dv.setFloat32(o+4,ny,true);dv.setFloat32(o+8,nz,true);
    for(let v=0;v<3;v++){const q=[a,c2,c3][v];
      dv.setFloat32(o+12+v*12,p[q],true);
      dv.setFloat32(o+16+v*12,p[q+1],true);
      dv.setFloat32(o+20+v*12,p[q+2],true);}
    dv.setUint16(o+48,0,true); o+=50;
  }
  const blob=new Blob([buf],{type:'model/stl'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download='halo_segment_preview_N'+P.N+'_th'+P.tilt+'_Ri'+P.Ri+'_land'+P.land+'.stl';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(a.href),5000);
}
document.getElementById('b_stl').addEventListener('click',downloadSTL);
document.getElementById('b_copy').addEventListener('click',()=>{
  const btn=document.getElementById('b_copy');
  const done=()=>{btn.textContent='Copied ✓';setTimeout(()=>btn.textContent='Copy',1500);};
  if(navigator.clipboard&&navigator.clipboard.writeText)
    navigator.clipboard.writeText(cadCmd()).then(done,()=>{});
  else{const rr=document.createRange();rr.selectNode(document.getElementById('cadcmd'));
    const s=getSelection();s.removeAllRanges();s.addRange(rr);document.execCommand('copy');
    s.removeAllRanges();done();}
});

// ---- controls ----
const FMT={N:v=>v,tilt:v=>v+'°',R:v=>v,Ri:v=>v,bw:v=>v,land:v=>v+' mm',bond:v=>v.toFixed(1),G:v=>v.toFixed(2),dT:v=>v+' K',dens:v=>v+'%'};
const IDS=['N','tilt','R','Ri','bw','land','bond','G','dT','dens'];
IDS.forEach(k=>{
  const el=document.getElementById('i_'+k); if(!el)return;
  el.addEventListener('input',()=>{P[k]=parseFloat(el.value);const o=document.getElementById('o_'+k);if(o)o.textContent=FMT[k](P[k]);buildScene();});
});
function sync(){
  IDS.forEach(k=>{const el=document.getElementById('i_'+k);if(!el)return;el.value=P[k];const o=document.getElementById('o_'+k);if(o)o.textContent=FMT[k](P[k]);});
}
function rescaleRanges(){
  const r=WR();
  const iR=document.getElementById('i_R'); if(iR){iR.min=Math.round(r*0.6); iR.max=Math.round(r*2.2);}
  const iRi=document.getElementById('i_Ri'); if(iRi){iRi.min=Math.round(r*0.3); iRi.max=Math.round(r*2.5);}
  const ibw=document.getElementById('i_bw'); if(ibw)ibw.max=Math.round(Math.max(40,r*0.6));
}
document.querySelectorAll('button.pz[data-d]').forEach(b=>{
  b.addEventListener('click',()=>{
    document.querySelectorAll('button.pz[data-d]').forEach(x=>x.classList.remove('act'));
    b.classList.add('act');
    P.D=parseFloat(b.dataset.d); P.wt=parseFloat(b.dataset.t);
    const th=P.tilt*Math.PI/180;
    P.R=Math.round(0.81*WR()*Math.cos(th)/Math.sin(HALF())/5)*5;
    rescaleRanges(); fitHide(); sync(); buildScene();
  });
});
function fitHide(){
  const th=P.tilt*Math.PI/180, hw=hideWindow(th);
  // park the band against the hide window's OUTER edge (teeth at the rim),
  // the canonical placement
  P.bw=Math.max(25,Math.round((hw[1]-hw[0])*0.28/5)*5);
  P.Ri=Math.round(hw[1]-P.bw-2);
}
const bHide=document.getElementById('b_hide');
if(bHide)bHide.addEventListener('click',()=>{fitHide();rescaleRanges();sync();buildScene();});
const bBal=document.getElementById('b_bal');
if(bBal)bBal.addEventListener('click',()=>{fitHide();rescaleRanges();sync();buildScene();});
const bB3=document.getElementById('b_b3');
if(bB3)bB3.addEventListener('click',()=>{
  Object.assign(P,CANON);
  document.querySelectorAll('button.pz[data-d]').forEach(x=>x.classList.toggle('act',x.dataset.d==='300'));
  rescaleRanges(); sync(); buildScene();
});
document.querySelectorAll('button.pz[data-view]').forEach(b=>{
  b.addEventListener('click',()=>{
    document.querySelectorAll('button.pz[data-view]').forEach(x=>x.classList.remove('act'));
    b.classList.add('act');
    view=b.dataset.view; autoDist=true;
    if(view==='drive'){az=1.25; pol=1.95;}
    if(view==='station'){az=0.5; pol=1.5;}   // graze from below: the tower shows under the disc
    buildScene();
  });
});
function viewNote(body){
  const el=document.getElementById('viewnote'), r=WR();
  if(!el)return;
  if(view==='assembly')
    el.innerHTML='All '+P.N+' towers and wafers, re-derived live from the sliders — a coarse twin of the canonical build. Exact solids: the <b>CAD viewer</b>.';
  else if(view==='drive')
    el.innerHTML='The face ring at the rim and the '+PIN_T+'T pinion at 12 o\'clock — '+body.gs.ratio.toFixed(0)+':1, '+body.gs.rpm.toFixed(2)+' rpm at the '+N20_RPM+' rpm N20 (screen speed is a time-lapse).';
  else if(view==='station')
    el.innerHTML='One tower with its wafer — <b>'+Math.max(0,(P.R+r)-GRI()).toFixed(0)+' mm</b> of wafer overhangs the pad outboard, <b>'+Math.max(0,P.Ri-(P.R-r)).toFixed(0)+' mm</b> inboard.';
  else
    el.innerHTML='The bare tower: base band, toothed rim, arched twin walls, tilted land on top.';
}

function resize(){
  const w=canvas.clientWidth,h=canvas.clientHeight;
  renderer.setSize(w,h,false); camera.aspect=w/h; camera.updateProjectionMatrix();
}
window.addEventListener('resize',resize);
rescaleRanges(); sync(); resize(); placeCam(); buildScene();
let _tPrev=0, _ringA=0;
(function loop(t){
  requestAnimationFrame(loop);
  if(view==='drive'&&ANIM.ring){
    const dt=Math.min(t-_tPrev,100)/1000;
    _ringA+=dt*PIN_W;                              // accumulates PINION angle
    if(ANIM.pin)ANIM.pin.rotation.z=_ringA;
    ANIM.ring.rotation.z=_ringA/ANIM.ratio;        // surface speeds match at the mesh
    window.__ringAngle=_ringA/ANIM.ratio;
  }
  _tPrev=t;
  renderer.render(scene,camera);
})(0);
})();
