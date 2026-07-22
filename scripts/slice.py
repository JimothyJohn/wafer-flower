#!/usr/bin/env python3
"""STL -> Bambu H2S G-code via OrcaSlicer's CLI (free/open-source, ships with
the OrcaSlicer.app bundle -- `brew install --cask orcaslicer`).

Slices with Orca's bundled Bambu system profiles plus this project's overrides
(PETG, 45% infill, Textured PEI Plate). Emits, per input STL:
    gcode/<name>.gcode      raw G-code (inspection, or send via Bambu Studio)
    gcode/<name>.gcode.3mf  drop on the microSD card / send with Handy -- this
                            is the file the printer UI actually wants

Orca's CLI quirks this script absorbs:
  - It does NOT resolve profile "inherits" chains for JSONs loaded by path.
    Missing keys silently fall back to engine defaults -- Generic PETG sliced
    as filament_type=PLA at 200C before this script flattened the chains.
    Never hand Orca an unflattened system profile.
  - It refuses two process JSONs ("duplicate process config file"), so
    overrides are merged into the flattened process profile.
  - There is no --curr-bed-type flag in 2.4.2; curr_bed_type must ride in the
    process JSON or PETG dies on the default Cool Plate.
  - --export-3mf needs an absolute path and must not be combined with
    --outputdir (which gets prepended, breaking the path). The raw G-code is
    recovered from inside the .gcode.3mf, which is a zip.

Usage:
    python3 scripts/slice.py                      # segment.stl + pinion.stl
    python3 scripts/slice.py stl/segment.stl --copies 3
    python3 scripts/slice.py --process "0.16mm Standard @BBL H2S" foo.stl
"""

import argparse
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

ORCA_CANDIDATES = [
    "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer",
    str(Path.home() / "Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"),
]

PROFILES = Path("/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL")

DEFAULTS = {
    "machine": "Bambu Lab H2S 0.4 nozzle",
    "process": "0.20mm Standard @BBL H2S",
    "filament": "Generic PETG @BBL H2S",
}

# Project print settings (CLAUDE.md: PETG at 45% infill). Keys are OrcaSlicer
# process-config names; anything valid there can be added.
OVERRIDES = {
    "curr_bed_type": "Textured PEI Plate",
    "sparse_infill_density": "45%",
}

BED_X, BED_Y = 340.0, 320.0  # H2S build area, mm (from the machine profile)


def find_orca():
    for c in ORCA_CANDIDATES:
        if Path(c).is_file():
            return c
    c = shutil.which("orcaslicer") or shutil.which("orca-slicer")
    if c:
        return c
    sys.exit("OrcaSlicer not found. Install with: brew install --cask orcaslicer")


def stl_footprint(path):
    """XY bounding-box size of a binary STL, mm. Returns None for ASCII STL."""
    with open(path, "rb") as f:
        header = f.read(80)
        if header.lstrip().startswith(b"solid"):
            return None
        (n,) = struct.unpack("<I", f.read(4))
        lo = [float("inf")] * 2
        hi = [float("-inf")] * 2
        for _ in range(n):
            rec = f.read(50)
            for v in range(3):
                x, y = struct.unpack_from("<2f", rec, 12 + 12 * v)
                lo[0], lo[1] = min(lo[0], x), min(lo[1], y)
                hi[0], hi[1] = max(hi[0], x), max(hi[1], y)
    return hi[0] - lo[0], hi[1] - lo[1]


def flatten_profile(kind, name):
    """Resolve an Orca system profile's full 'inherits' chain (child wins)."""
    src = PROFILES / kind / f"{name}.json"
    if not src.is_file():
        sys.exit(f"No such {kind} profile: {src}")
    cfg = json.loads(src.read_text())
    parent = cfg.pop("inherits", None)
    if parent:
        merged = flatten_profile(kind, parent)
        merged.update(cfg)
        cfg = merged
    return cfg


def write_profile(kind, name, build_dir, overrides=None):
    cfg = flatten_profile(kind, name)
    cfg.update(overrides or {})
    out = build_dir / f"{kind}.json"
    out.write_text(json.dumps(cfg, indent=2))
    return out


def slice_one(orca, stl, args, profiles, out_dir):
    name = stl.stem
    fp = stl_footprint(stl)
    # bed is 340x320, not square: the part fits if either orientation does
    if fp and not (max(fp) <= BED_X and min(fp) <= BED_Y):
        print(f"SKIP {name}: footprint {fp[0]:.0f}x{fp[1]:.0f} mm exceeds "
              f"{BED_X:.0f}x{BED_Y:.0f} mm bed (ring-scale STLs are not "
              f"printable whole)")
        return False

    machine, process, filament = profiles
    three_mf = (out_dir / f"{name}.gcode.3mf").resolve()
    three_mf.unlink(missing_ok=True)
    cmd = [
        orca,
        "--load-settings", f"{machine};{process}",
        "--load-filaments", str(filament),
        "--slice", "0",
        "--arrange", "1",
        "--ensure-on-bed",
        "--debug", "1",
        "--export-3mf", str(three_mf),
    ]
    if args.copies > 1:
        cmd += ["--repetitions", str(args.copies)]
    cmd.append(str(stl))

    r = subprocess.run(cmd, capture_output=True, text=True)
    if not three_mf.is_file():
        print(r.stdout[-3000:], r.stderr[-3000:], sep="\n")
        sys.exit(f"Slice failed for {name}")
    gcode = out_dir / f"{name}.gcode"
    with zipfile.ZipFile(three_mf) as z:
        gcode.write_bytes(z.read("Metadata/plate_1.gcode"))

    stats = {}
    for line in gcode.read_text(errors="replace").splitlines():
        if "total estimated time" in line:
            stats["time"] = line.split("total estimated time:")[-1].strip()
        elif line.startswith("; filament used [g]"):
            stats["weight"] = line.split("=")[-1].strip() + " g"
        if len(stats) == 2:
            break
    where = gcode.relative_to(REPO) if gcode.is_relative_to(REPO) else gcode
    print(f"OK   {name}: {stats.get('time', '?')}, "
          f"{stats.get('weight', '? g')} -> {where} (+ .gcode.3mf)")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("stls", nargs="*", type=Path,
                    help="STL files (default: stl/segment.stl stl/pinion.stl)")
    ap.add_argument("--machine", default=DEFAULTS["machine"])
    ap.add_argument("--process", default=DEFAULTS["process"])
    ap.add_argument("--filament", default=DEFAULTS["filament"])
    ap.add_argument("--copies", type=int, default=1,
                    help="clones per plate (auto-arranged)")
    ap.add_argument("--infill", type=int, default=None, metavar="PCT",
                    help="sparse infill percent (default: OVERRIDES, 45)")
    ap.add_argument("--outdir", type=Path, default=None,
                    help="output directory (default: <repo>/gcode)")
    args = ap.parse_args()

    stls = args.stls or [REPO / "stl/segment.stl", REPO / "stl/pinion.stl"]
    for s in stls:
        if not s.is_file():
            sys.exit(f"Missing STL: {s} (run scripts/segment_stl.py first)")

    orca = find_orca()
    out_dir = args.outdir or REPO / "gcode"
    out_dir.mkdir(parents=True, exist_ok=True)

    overrides = dict(OVERRIDES)
    if args.infill is not None:
        overrides["sparse_infill_density"] = f"{args.infill}%"

    with tempfile.TemporaryDirectory() as td:
        build = Path(td)
        profiles = (
            write_profile("machine", args.machine, build),
            write_profile("process", args.process, build, overrides),
            write_profile("filament", args.filament, build),
        )
        for s in stls:
            slice_one(orca, s, args, profiles, out_dir)


if __name__ == "__main__":
    main()
