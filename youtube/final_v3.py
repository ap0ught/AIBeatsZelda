"""The upload: [live intro] + part one (narration-timed) + the run (37:02, stream-copied) + [live outro].
usage: python youtube/final_v3.py [--intro file] [--outro file]     -> youtube/out_v3/zelda_ai_v3_full.mp4
Intro/outro (phone footage) are re-encoded to the package's exact parameters so the join stays a stream copy."""
import argparse, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from build import ENC, FPS, run
HERE = Path(__file__).parent; OUT = HERE / "out_v3"
RUN = HERE.parent / "video/sixth_run_2026-09-22/zelda_ai_run6_37m02s_overlay.mp4"
ap = argparse.ArgumentParser(); ap.add_argument("--intro"); ap.add_argument("--outro"); a = ap.parse_args()
def conform(src, name):
    dst = OUT / f"{name}_conformed.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1",
         "-r", FPS] + ENC + ["-ar", "44100", "-ac", "2", str(dst)])
    return dst
parts = []
if a.intro: parts.append(conform(a.intro, "intro"))
parts.append(OUT / "part1.mp4")
parts.append(RUN)
if a.outro: parts.append(conform(a.outro, "outro"))
elif (OUT / "outro.mp4").exists(): parts.append(OUT / "outro.mp4")
lst = OUT / "_final.txt"; lst.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts), encoding="utf-8")
run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(OUT / "zelda_ai_v3_full.mp4")])
print("wrote", OUT / "zelda_ai_v3_full.mp4")
