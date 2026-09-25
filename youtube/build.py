"""Build the documentary half from beats.py: every shot rendered to its own normalized clip (cached), then
concatenated; plus the subtitle/guide track and the timecoded SCRIPT.md.

All clips share the full run's exact format (h264 high yuv420p 1280x720 @ 150247/2500 fps, AAC 44.1k stereo), so the
final video can be joined to the unedited run WITHOUT re-encoding it.

usage (from harness/):  python youtube/build.py [clips] [part1] [script] [guide] [final]      (default: all)"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import beats   # noqa: E402
import gfx     # noqa: E402

CLIPS, OUT = HERE / "clips", HERE / "out"
CLIPS.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
FPS = "150247/2500"
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", FPS,
       "-video_track_timescale", "150247", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]
WPS, PAD, MIN = 2.45, 0.9, 3.5          # narration speed (words/second), breath per paragraph, shortest paragraph
CHAPTER_CARD = 2.4


def para_dur(text: str) -> float:
    return round(max(MIN, len(text.split()) / WPS + PAD), 2)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + " ".join(str(c) for c in cmd)[:600] + "\n" + r.stderr[-1500:])
    return r


def has_audio(src) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(src)],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def src_dur(src) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)], capture_output=True, text=True)
    return float(r.stdout.strip())


def key(spec: dict, dur: float) -> str:
    ver = 2 if spec.get("type") == "mosaic" else 1
    return hashlib.sha1(json.dumps([spec, dur, ver], sort_keys=True).encode()).hexdigest()[:10]


# ---------------------------------------------------------------------------------------------- panel art
def panel_png(path, chapter, shot, best):
    im = Image.new("RGB", (1280, 720), gfx.BG)
    d = ImageDraw.Draw(im)
    px = 768
    d.rectangle((px, 0, 1280, 720), fill=gfx.PANEL)
    for gy in range(0, 720, 24):
        d.line((px, gy, 1280, gy), fill=gfx.GRID)
    d.line((px, 0, px, 720), fill=(40, 48, 60), width=2)
    d.text((px + 16, 14), "HOW IT LEARNED", font=gfx.FB[22], fill=gfx.GOLD)
    d.text((px + 16, 46), chapter, font=gfx.F[13], fill=gfx.DIM)
    d.text((px + 16, 96), shot.get("day", ""), font=gfx.F[16], fill=gfx.BLUE)
    d.text((px + 16, 126), shot.get("title", ""), font=gfx.FB[26], fill=gfx.TEXT)
    y = 176
    for line in textwrap.wrap(shot.get("note", ""), 44):
        d.text((px + 16, y), line, font=gfx.F[18], fill=gfx.TEXT)
        y += 28
    d.text((px + 16, 590), "BEST FULL RUN SO FAR", font=gfx.F[13], fill=gfx.DIM)
    d.text((px + 16, 612), best or "none yet", font=gfx.FB[44] if best else gfx.F[26], fill=gfx.GREEN if best else gfx.DIM)
    d.text((px + 16, 676), "footage: the project's own recordings", font=gfx.F[13], fill=gfx.DIM)
    im.save(path)


def lower_png(path, text):
    im = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lines = textwrap.wrap(text, 84)
    h = 22 + 26 * len(lines)
    d.rectangle((0, 720 - h - 24, 768, 720 - 24), fill=(5, 7, 10, 225))
    d.rectangle((0, 720 - h - 24, 6, 720 - 24), fill=gfx.GOLD + (255,))
    for i, l in enumerate(lines):
        d.text((18, 720 - h - 24 + 11 + i * 26), l, font=gfx.FB[16], fill=gfx.TEXT + (255,))
    im.save(path)


def tag_png(path, text):
    im = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    w = int(d.textlength(text, font=gfx.FB[30])) + 40
    d.rectangle((640 - w // 2, 640, 640 + w // 2, 702), fill=(5, 7, 10, 235), outline=gfx.GOLD + (255,), width=3)
    d.text((640, 671), text, font=gfx.FB[30], fill=gfx.GOLD + (255,), anchor="mm")
    im.save(path)


# ---------------------------------------------------------------------------------------------- shot renderers
def render_game(spec, dur, out, chapter, best):
    png = out.with_suffix(".panel.png")
    panel_png(png, chapter, spec, best)
    sp = spec.get("speed", 1.0)
    src = ROOT / spec["src"]
    aud = has_audio(src) and sp == 1.0
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", str(spec.get("ss", 0)), "-t", str(dur * sp + 0.5), "-i", str(src), "-loop", "1", "-i", str(png)]
    if not aud:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    fc = (f"[0:v]setpts=PTS/{sp},fps={FPS},scale=768:672:flags=neighbor[g];[1:v]fps={FPS}[bg];[bg][g]overlay=0:24:shortest=0[v]")
    if aud:
        fc += ";[0:a]volume=0.22,aresample=44100[a]"
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]" if aud else "2:a", "-t", str(dur)] + ENC + [str(out)]
    run(cmd)


def render_full(spec, dur, out):
    sp = spec.get("speed", 1.0)
    src = ROOT / spec["src"]
    vol = spec.get("audio", 0.4)
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", str(spec.get("ss", 0)), "-t", str(dur * sp + 0.5), "-i", str(src)]
    fc = f"[0:v]setpts=PTS/{sp},fps={FPS}[v0]"
    last = "[v0]"
    if spec.get("lower"):
        png = out.with_suffix(".lower.png")
        lower_png(png, spec["lower"])
        cmd += ["-loop", "1", "-i", str(png)]
        fc += f";{last}[1:v]overlay=0:0:shortest=0[v1]"
        last = "[v1]"
    fc += f";[0:a]volume={vol},aresample=44100[a]"
    cmd += ["-filter_complex", fc, "-map", last, "-map", "[a]", "-t", str(dur)] + ENC + [str(out)]
    run(cmd)


def render_mosaic(spec, dur, out):
    src = ROOT / spec["src"]
    total = src_dur(src)
    sp = spec.get("speed", 1.0)
    n = 12
    offs = [total * (i + 0.5) / (n + 1) for i in range(n)]
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for o in offs:
        cmd += ["-ss", f"{o:.2f}", "-t", str(dur * sp + 0.5), "-i", str(src)]
    png = out.with_suffix(".tag.png")
    tag_png(png, spec.get("label", ""))
    cmd += ["-loop", "1", "-i", str(png), "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    fc = ";".join(f"[{i}:v]setpts=PTS/{sp},fps={FPS},scale=320:240:flags=neighbor[m{i}]" for i in range(n))
    layout = "|".join(f"{(i % 4) * 320}_{(i // 4) * 240}" for i in range(n))
    fc += ";" + "".join(f"[m{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={layout}[grid];[grid][{n}:v]overlay=0:0:shortest=0[v]"
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", f"{n + 1}:a", "-t", str(dur)] + ENC + [str(out)]
    run(cmd)


def render_frames(frames, out):
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1280x720", "-r", FPS, "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v", "-map", "1:a", "-shortest"] + ENC + [str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    last_id, last_bytes = None, None
    for im in frames:
        if id(im) != last_id:
            last_bytes = im.tobytes()
            last_id = id(im)
        p.stdin.write(last_bytes)
    p.stdin.close()
    err = p.stderr.read().decode(errors="replace")
    if p.wait() != 0:
        raise RuntimeError("ffmpeg (frames) failed: " + err[-1200:])


def chapter_card(idx, title, dur):
    n = gfx.nframes(dur)
    for k in range(n):
        t = k / gfx.FPS
        im, d = gfx.canvas()
        a = gfx.ease(t / 0.5) * (1 - gfx.ease((t - (dur - 0.4)) / 0.4))
        d.text((640, 300), f"PART ONE  -  CHAPTER {idx}", font=gfx.F[26], fill=gfx.blend(gfx.DIM, a), anchor="mm")
        d.text((640, 370), title, font=gfx.FB[72], fill=gfx.blend(gfx.GOLD, a), anchor="mm")
        yield im


# ---------------------------------------------------------------------------------------------- timeline
def timeline():
    """[(start, dur, chapter_id, chapter_title, para_index or None, text, [(spec, shot_dur)])]"""
    t, rows = 0.0, []
    for ci, ch in enumerate(beats.CHAPTERS):
        if ci > 0:
            rows.append((t, CHAPTER_CARD, ch["id"], ch["title"], None, "", [({"type": "chapter", "idx": ci, "title": ch["title"]}, CHAPTER_CARD)]))
            t += CHAPTER_CARD
        for pi, (text, shots) in enumerate(ch["paras"]):
            dur = para_dur(text)
            each = round(dur / len(shots), 2)
            rows.append((t, dur, ch["id"], ch["title"], pi, text, [(s, each) for s in shots]))
            t += each * len(shots)
    return rows, t


def build_clips():
    rows, total = timeline()
    files = []
    n = 0
    for start, dur, cid, ctitle, pi, text, shots in rows:
        ch = next(c for c in beats.CHAPTERS if c["id"] == cid)
        for spec, sdur in shots:
            n += 1
            out = CLIPS / f"{n:03d}_{cid}_{spec.get('name', spec['type'])}_{key(spec, sdur)}.mp4"
            files.append(out)
            if out.exists() and out.stat().st_size > 1000:
                continue
            for old in CLIPS.glob(f"{n:03d}_*"):
                old.unlink()
            print(f"  rendering {out.name}  ({sdur:.1f}s)", flush=True)
            if spec["type"] == "game":
                render_game(spec, sdur, out, f"chapter: {ctitle.lower()}", ch.get("best"))
            elif spec["type"] == "full":
                render_full(spec, sdur, out)
            elif spec["type"] == "mosaic":
                render_mosaic(spec, sdur, out)
            elif spec["type"] == "chapter":
                render_frames(chapter_card(spec["idx"], spec["title"], sdur), out)
            elif spec["type"] == "gen":
                kw = {k: v for k, v in spec.items() if k not in ("type", "name")}
                render_frames(gfx.GEN[spec["name"]](sdur, **kw), out)
            else:
                raise ValueError(spec)
    (OUT / "part1_files.txt").write_text("".join(f"file '{f.as_posix()}'\n" for f in files), encoding="utf-8")
    print(f"{len(files)} clips, planned length {total / 60:.2f} min")
    return files


def build_part1():
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(OUT / "part1_files.txt"), "-c", "copy", str(OUT / "part1_clean.mp4")])
    print("part1_clean.mp4:", f"{src_dur(OUT / 'part1_clean.mp4') / 60:.2f} min")


def tc(t, srt=False):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(s % 1 * 1000):03d}" if srt else f"{int(t // 60):d}:{int(t % 60):02d}"


def build_script():
    rows, total = timeline()
    srt, k = [], 0
    md = ["# CAN AI BEAT THE LEGEND OF ZELDA WITHOUT CHEATING? - narration script\n",
          f"Part one (the documentary half) runs **{tc(total)}** at a relaxed {WPS * 60:.0f} words a minute; part two is the unedited "
          "39:15 run. Timecodes match `out/part1_clean.mp4` / `out/part1_guide.mp4` (the guide cut has this script burned "
          "in as subtitles so you can read along while recording).\n",
          "Every number below is sourced from the project's journal and run archives. Square brackets are direction, not narration.\n"]
    words = 0
    for start, dur, cid, ctitle, pi, text, shots in rows:
        if pi is None:
            md.append(f"\n## {tc(start)}  {ctitle}\n")
            continue
        if pi == 0 and cid == "cold":
            md.append(f"\n## {tc(start)}  {ctitle}\n")
        words += len(text.split())
        vis = "; ".join(_describe(s) for s, _ in shots)
        md.append(f"**[{tc(start)} - {tc(start + dur)}]**  \n{text}  \n*[ON SCREEN: {vis}]*\n")
        chunks = textwrap.wrap(text, 84)
        tot = sum(len(c) for c in chunks)
        t0 = start + 0.25
        for c in chunks:
            d = (dur - 0.6) * len(c) / tot
            k += 1
            srt.append(f"{k}\n{tc(t0, True)} --> {tc(t0 + d - 0.05, True)}\n{c}\n")
            t0 += d
    md.append(f"\n---\n{words} words of narration. Then the hand-off card, and the full run plays uncut.\n")
    (OUT / "part1.srt").write_text("\n".join(srt), encoding="utf-8")
    (HERE / "SCRIPT.md").write_text("\n".join(md), encoding="utf-8")
    print(f"SCRIPT.md and part1.srt written: {words} words, {tc(total)}")


def _describe(s):
    if s["type"] == "game":
        return f"early test footage `{Path(s['src']).name}` - {s.get('title', '')}"
    if s["type"] == "full":
        nm = {"fourth": "run 4 (39:15)", "third": "run 3 (41:15)", "second": "run 2 (57:40)", "first": "run 1 (1:42)"}
        which = next((v for k_, v in nm.items() if k_ in s["src"]), s["src"])
        return f"{which} at {tc(s.get('ss', 0))}" + (f" - lower third: {s['lower'][:60]}..." if s.get("lower") else "")
    if s["type"] == "mosaic":
        return f"12-window mosaic of `{Path(s['src']).name}` - {s.get('label', '')}"
    return {"title_card": "title card", "rules_card": "the rules, revealed line by line", "terminal": "real log lines in a terminal",
            "architecture": "diagram: Claude -> Python -> bridge -> emulator", "ramvision": "the game with the AI's memory reads overlaid",
            "tilelearn": "tile grid overlay + the bot's real tile notes", "quote": "quote from the AI's journal",
            "lookahead": "the nine futures and their scores (real branches)", "disclosure": "practice vs final-run card",
            "disasm": "scrolling disassembly of the game", "breakdown": "run 1 time breakdown bars", "complaints": "my review notes, typed out",
            "chart": "run times vs the world record", "wr_route": "the record route with its glitches marked",
            "map": "the overworld decoded from the ROM, route drawn on it", "handoff": "PART TWO card",
            "numbers": "what it took: the project by the numbers"}.get(s.get("name"), s.get("name", "?"))


def build_guide():
    run(["ffmpeg", "-y", "-v", "error", "-i", "part1_clean.mp4", "-vf",
         "subtitles=part1.srt:force_style='FontName=Consolas,FontSize=13,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=6'",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "copy", "part1_guide.mp4"], cwd=str(OUT))
    print("part1_guide.mp4 written")


def build_final():
    lst = OUT / "final_files.txt"
    lst.write_text(f"file '{(OUT / 'part1_clean.mp4').as_posix()}'\nfile '{(ROOT / beats.RUN4).as_posix()}'\n", encoding="utf-8")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart",
         str(OUT / "zelda_ai_full_video.mp4")])
    print("zelda_ai_full_video.mp4:", f"{src_dur(OUT / 'zelda_ai_full_video.mp4') / 60:.2f} min")


def build_description():
    """YouTube description with chapter timestamps for both halves (part two's come from the run's own checkpoints)."""
    import glob
    import os
    rows, total = timeline()
    part1 = src_dur(OUT / "part1_clean.mp4") if (OUT / "part1_clean.mp4").exists() else total
    ck = {}
    for f in glob.glob(str(ROOT / "logs/archive/fourth_run_20260919/checkpoints/fullgame_*.json")):
        ck[os.path.basename(f)[9:-5]] = json.load(open(f))["frames"] / 60.0988
    lines = ["0:00 Cold open"]
    for start, dur, cid, ctitle, pi, text, shots in rows:
        if pi is None:
            lines.append(f"{tc(start)} {ctitle.title()}")
    marks = [("THE FULL RUN - power on", 0.0), ("Level 3", ck["ow_74"]), ("Heart rock, 100 rupees, blue candle", ck["L3_done"]),
             ("The White Sword", ck["ws_0a"]), ("Level 1", ck["ow1_37"]), ("Heart tree, raft to Level 4", ck["L1_done"]),
             ("Level 4", ck["l4_sail"]), ("100 rupees under a tree", ck["L4_done"]), ("Level 8", ck["l8a_6d"]), ("Level 2", ck["L8_done"]),
             ("Level 5", ck["L2_done"]), ("Whirlwind to the shops: arrows and bait", ck["L5_done"]), ("Level 7", ck["p7b_42"]),
             ("The Magical Sword", ck["L7_done"]), ("Level 6", ck["ms_sword"]), ("Death Mountain", ck["L6_done"]),
             ("Level 9", ck["dm9_05"]), ("Ganon", ck["g9_42"]), ("Zelda - 39:15", ck["g9_32"])]
    for name, t in marks:
        lines.append(f"{tc(part1 + t)} {name}")
    body = """Can an AI beat The Legend of Zelda (NES, 1986) without cheating - and how close can it get to the human world record?

The first half is how it was built: an AI (Claude, running as a coding agent) wrote its own hands and eyes, learned the
game by experiment and by reading the cartridge's code, rehearsed every room, and got from 1h42m to 39:15 in four runs.
The second half is the complete 39:15 run, uncut. The panel on the right is the AI's own reasoning for every room.

THE RULES: unmodified game - controller inputs only - one continuous run from power-on - no memory editing - no glitches -
no human input. Every run is replayed from power-on in a fresh emulator and the final memory must match byte for byte.
THE CATCH: this is a tool-assisted run. The AI reads the game's memory and rehearses each room from bookmarks (up to 60
takes, keeping the best); the final recording uses none of that - it is one unbroken take. Human records (27:40, any% no
up+a) are set live on real hardware and allow glitches this run refuses to use.

CHAPTERS
""" + chr(10).join(lines) + """

Emulator: BizHawk 2.11.1. Game disassembly consulted: github.com/aldonunez/zelda1-disassembly. Record route reference:
Order of the Ate (sites.google.com/view/orderoftheate). Leaderboard: speedrun.com/the_legend_of_zelda.
"""
    (OUT / "youtube_description.txt").write_text(body, encoding="utf-8")
    print("youtube_description.txt written;", len(lines), "chapters")


if __name__ == "__main__":
    want = sys.argv[1:] or ["clips", "part1", "script", "guide", "final", "description"]
    if "description" in want and len(want) == 1:
        build_description()
        sys.exit(0)
    if "clips" in want:
        build_clips()
    if "part1" in want:
        build_part1()
    if "script" in want:
        build_script()
    if "guide" in want:
        build_guide()
    if "final" in want:
        build_final()
    if "description" in want:
        build_description()
