#!/usr/bin/env python3
"""v3 -> DXF: everything needed to build segment + jig in OnShape."""
import math

# params (match halo_v3)
N=9; R=350.0; TILT=math.radians(20); WR=150.0; WT=0.775; BOND=0.5
RI=175.0; RO=245.0; BT=8.0
DTR=12.0; DTT=16.0; DTD=8.0; DTC=0.25
MARGIN=3.0; FCLR=0.3; WALL=5.0
SEG=360.0/N
ct=math.cos(TILT)

def hdr(f): f.write("0\nSECTION\n2\nENTITIES\n")
def ftr(f): f.write("0\nENDSEC\n0\nEOF\n")
def circ(f,x,y,r,l): f.write(f"0\nCIRCLE\n8\n{l}\n10\n{x:.4f}\n20\n{y:.4f}\n30\n0.0\n40\n{r:.4f}\n")
def ln(f,a,b,c,d,l): f.write(f"0\nLINE\n8\n{l}\n10\n{a:.4f}\n20\n{b:.4f}\n30\n0.0\n11\n{c:.4f}\n21\n{d:.4f}\n31\n0.0\n")
def arc(f,x,y,r,a1,a2,l): f.write(f"0\nARC\n8\n{l}\n10\n{x:.4f}\n20\n{y:.4f}\n30\n0.0\n40\n{r:.4f}\n50\n{a1:.4f}\n51\n{a2:.4f}\n")
def txt(f,x,y,h,s,l): f.write(f"0\nTEXT\n8\n{l}\n10\n{x:.4f}\n20\n{y:.4f}\n30\n0.0\n40\n{h:.4f}\n1\n{s}\n")
def poly(f,pts,l):
    for p,q in zip(pts,pts[1:]): ln(f,p[0],p[1],q[0],q[1],l)

def local_to_plan(x,y):
    """wafer-local (x radial, y tangential) -> global plan projection"""
    return (R + x, y*ct)

def ellipse_pts(shrink, segs=120):
    a=WR-shrink; pts=[]
    for i in range(segs+1):
        t=2*math.pi*i/segs
        pts.append(local_to_plan(a*math.cos(t), a*math.sin(t)))
    return pts

# ---------------- segment_profiles.dxf ----------------
with open("segment_profiles.dxf","w") as f:
    hdr(f)
    ha=math.radians(SEG/2)
    # sector outline (plan) - base extrude profile, 8mm down
    arc(f,0,0,RI,-SEG/2,SEG/2,"SECTOR")
    arc(f,0,0,RO,-SEG/2,SEG/2,"SECTOR")
    for s in (-1,1):
        ln(f,RI*math.cos(ha),s*RI*math.sin(ha),RO*math.cos(ha),s*RO*math.sin(ha),"SECTOR")
    # land footprint (projected wafer edge, -3mm): riser intersect profile
    poly(f,ellipse_pts(MARGIN),"LAND_FOOTPRINT")
    poly(f,ellipse_pts(0.0),"WAFER_EDGE_REF")
    # nubs (d4 circles, extrude 0.5 from land plane)
    for lx,lyy in [(-130,0),(-115,35),(-115,-35)]:
        x,y=local_to_plan(lx,lyy); circ(f,x,y,2.0,"NUBS_D4")
    # radial tilt axis (construction: plane pivot line)
    ln(f,RI-30,0,R+WR+30,0,"TILT_AXIS")
    circ(f,R,0,2,"WAFER_CENTER")
    # keyhole (underside)
    kx=(RI+RO)/2
    circ(f,kx,0,4.5,"KEYHOLE"); circ(f,kx,-6,2,"KEYHOLE")
    ln(f,kx-2,-6,kx-2,0,"KEYHOLE"); ln(f,kx+2,-6,kx+2,0,"KEYHOLE")
    # dovetail profiles, drawn off to the side (extrude on end faces)
    ox,oy=300,-260
    for tag,c in (("DT_MALE",0.0),("DT_FEMALE",DTC)):
        pts=[(ox-DTR/2-c,oy),(ox+DTR/2+c,oy),(ox+DTT/2+c,oy+DTD+c),(ox-DTT/2-c,oy+DTD+c),(ox-DTR/2-c,oy)]
        poly(f,pts,tag); ox+=40
    txt(f,RI,RO+20,10,f"SEGMENT: sector {SEG:.1f}deg Ri{RI:.0f} Ro{RO:.0f}, base 8 thick","NOTES")
    txt(f,RI,RO+35,10,"riser: extrude LAND_FOOTPRINT up 40, cut with land plane (see recipe)","NOTES")
    ftr(f)

# ---------------- jig_profiles.dxf ----------------
with open("jig_profiles.dxf","w") as f:
    hdr(f)
    ha=math.radians(SEG/2-1)
    # straddle rails
    for r1,r2,tag in ((RI-WALL-0.3,RI-0.3,"RAIL_IN"),(RO+0.3,RO+WALL+0.3,"RAIL_OUT")):
        arc(f,0,0,r1,-(SEG/2-1),SEG/2-1,tag); arc(f,0,0,r2,-(SEG/2-1),SEG/2-1,tag)
        for s in (-1,1):
            ln(f,r1*math.cos(ha),s*r1*math.sin(ha),r2*math.cos(ha),s*r2*math.sin(ha),tag)
    # fence arcs (projected polylines): local angle 270+-30 and 180+-10
    for cen,span,tag in ((270,60,"FENCE_DOWNHILL"),(180,20,"FENCE_PUSH")):
        for rr,sub in ((WR+FCLR,"IN"),(WR+FCLR+WALL,"OUT")):
            pts=[local_to_plan(rr*math.cos(math.radians(cen-span/2+span*i/40)),
                               rr*math.sin(math.radians(cen-span/2+span*i/40))) for i in range(41)]
            poly(f,pts,tag+"_"+sub)
    # clamp: hole over land centroid, bridge footprint
    hx,hy=local_to_plan(-122,0)
    circ(f,hx,hy,2.65,"CLAMP_HOLE_M5")
    poly(f,[(hx-25,hy-12),(hx+25,hy-12),(hx+25,hy+12),(hx-25,hy+12),(hx-25,hy-12)],"BRIDGE_FOOTPRINT")
    txt(f,RI,RO+30,10,"JIG plan. Fences rise to land plane +5. Bridge spans rails, hole normal to WAFER plane","NOTES")
    ftr(f)

print("wrote segment_profiles.dxf jig_profiles.dxf")
print(f"land plane: through radial line at wafer center (X axis thru {R},0,0), {math.degrees(TILT)}deg from Top, then OFFSET -{WT/2+BOND:.3f}mm (below)")
print(f"nub plan positions: {[tuple(round(v,2) for v in local_to_plan(*p)) for p in [(-130,0),(-115,35),(-115,-35)]]}")
print(f"clamp hole plan position: ({hx:.2f}, {hy:.2f})")
