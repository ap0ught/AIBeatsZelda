"""Cut a stretch of a run's overlay video (the whole 1280x720 frame, panel included) into a package clip:
python youtube/cut_overlay.py <video> <start s> <dur s> <name>   -> youtube/clips_v3/<name>.mp4"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from build import ENC, run
video, start, dur, name = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
out = Path("youtube/clips_v3") / f"{name}.mp4"
run(["ffmpeg", "-y", "-v", "error", "-ss", start, "-t", dur, "-i", video, "-an"] + ENC + [str(out)])
print("wrote", out)
