"""Assemble part one against the owner's own narration.

Inputs
  youtube/voice/narration.wav           his read of SCRIPT_v3, cleaned by cut_narration.py
  youtube/voice/narration_sections.json section timing in the cleaned narration: [{"section", "start", "end"}, ...]
                                        (an "outro" section, if present, is built separately and placed after the run)
  youtube/beats_v3.py                   SHOTS: section title -> list of clip specs {"clip", "in", "out"}
Output
  youtube/out_v3/part1.mp4              picture cut to the narration, narration as the audio track, no subtitles
  youtube/out_v3/outro.mp4              the outro's picture with its narration (if the narration has one)

Each section's clips are laid end to end and fitted to the section's narration length: a section that runs longer
than its clips holds the last frame; one that runs shorter trims the last clip. Clips are all 1280x720 at the run's
frame rate, so the final join is a stream copy.
usage: python youtube/build_v3.py [sections.json] [narration.wav]"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build import ENC, FPS, run          # noqa: E402
import beats_v3                          # noqa: E402

HERE = Path(__file__).parent
OUT = HERE / "out_v3"
OUT.mkdir(exist_ok=True)
VOICE = HERE / "voice"


def dur_of(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True).stdout.strip())


def concat_list(paths, name):
    lst = OUT / name
    lst.write_text("".join("file '" + p.resolve().as_posix() + "'\n" for p in paths), encoding="utf-8")
    return lst


def fit(specs, length, out):
    """concatenate the section's clips and fit them to `length` seconds (trim, or hold the last frame)"""
    parts = []
    t = 0.0
    for i, sp in enumerate(specs):
        src = HERE / sp["clip"]
        d = dur_of(src)
        a = sp.get("in", 0.0)
        b = min(d, sp.get("out", d))
        take = min(b - a, max(0.0, length - t))
        if take <= 0:
            break
        seg = OUT / f"_{out.stem}_{i}.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-ss", str(a), "-t", str(take), "-i", str(src), "-an"] + ENC + [str(seg)])
        parts.append(seg)
        t += take
    if t < length - 0.05 and parts:
        hold = OUT / f"_{out.stem}_hold.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.04", "-i", str(parts[-1]), "-frames:v", "1", "-f", "image2", str(OUT / "_last.png")])
        run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(OUT / "_last.png"), "-t", str(length - t), "-r", FPS] + ENC + [str(hold)])
        parts.append(hold)
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list(parts, f"_{out.stem}.txt")), "-c", "copy", str(out)])


def with_audio(video, audio, start, length, out):
    run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-ss", str(start), "-t", str(length), "-i", str(audio),
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", "-shortest", str(out)])


def main():
    sec_path = Path(sys.argv[1]) if len(sys.argv) > 1 else VOICE / "narration_sections.json"
    audio = Path(sys.argv[2]) if len(sys.argv) > 2 else VOICE / "narration.wav"
    sections = json.load(open(sec_path, encoding="utf-8"))
    outro = next((s for s in sections if s["section"] == "outro"), None)
    sections = [s for s in sections if s["section"] != "outro"]
    pieces = []
    for i, s in enumerate(sections):
        specs = beats_v3.SHOTS.get(s["section"])
        if not specs:
            print("no shots for", s["section"])
            continue
        length = s["end"] - s["start"]
        out = OUT / f"sec_{i:02d}.mp4"
        fit(specs, length, out)
        pieces.append(out)
        print(f"{s['section'][:40]:40s} {length:6.1f}s -> {out.name}", flush=True)
    video = OUT / "_part1_video.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list(pieces, "_part1.txt")), "-c", "copy", str(video)])
    with_audio(video, audio, sections[0]["start"], sections[-1]["end"] - sections[0]["start"], OUT / "part1.mp4")
    print("wrote", OUT / "part1.mp4")
    if outro:
        length = outro["end"] - outro["start"]
        fit(beats_v3.SHOTS.get("outro", []), length, OUT / "sec_outro.mp4")
        with_audio(OUT / "sec_outro.mp4", audio, outro["start"], length, OUT / "outro.mp4")
        print(f"wrote {OUT / 'outro.mp4'} ({length:.0f} s)")


if __name__ == "__main__":
    main()
