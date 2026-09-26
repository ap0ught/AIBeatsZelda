"""One-shot patch: route per-room reasoning into the recording and the overlay panel.

record_run.boundaries() had two bugs - it globbed every checkpoint on disk (including abandoned
branches, so the finished video captioned rooms the bot never entered) and keyed each caption to the
frame count AFTER the segment, so every caption named the room Link had just left.
render_overlay drew a fading list of past notes; the owner wants the current objective and the reason
for it, held steady.
"""
import os as _os, sys as _sys, pathlib as _pathlib
_ROOT = _pathlib.Path(__file__).resolve().parent.parent
_sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)          # logs/, shots/, runs/ are repo-relative
del _os, _sys, _pathlib
import ast
import pathlib

CRLF = {}


def read(path):
    raw = pathlib.Path(path).read_bytes()
    CRLF[path] = b"\r\n" in raw
    return raw.decode("utf-8").replace("\r\n", "\n")


def write(path, text):
    data = text.replace("\n", "\r\n") if CRLF[path] else text
    pathlib.Path(path).write_bytes(data.encode("utf-8"))
    ast.parse(text)
    print("patched", path)


def sub(text, old, new, what):
    assert text.count(old) == 1, f"anchor not unique/found: {what}"
    return text.replace(old, new)


# ---------------------------------------------------------------- record_run.py
t = read("record_run.py")

t = sub(t, """def boundaries(name: str) -> dict[int, str]:
    out: dict[int, str] = {}
    for p in (LOGS_DIR / "checkpoints").glob(f"{name}_*.json"):
        d = json.loads(p.read_text())
        if d["segments"]:
            out[d["frames"]] = d["segments"][-1]
    return out""",
'''def boundaries(name: str) -> dict[int, str]:
    """{start_frame: segment} for the run that actually happened.

    Two bugs lived here. The glob picked up EVERY checkpoint on disk, including ones left by
    abandoned branches (a dead "Level 4 before Level 1" attempt, six whirlwind retries, a raft dock
    probe), so the finished video announced rooms the bot never visited. And each caption was keyed
    to `frames`, the count AFTER the segment finished, so every caption named the room Link had just
    left. The ordered `segments` list inside the newest checkpoint is the authority on what ran, and
    a segment starts where the previous one ended.
    """
    saved: dict[str, dict] = {}
    for p in (LOGS_DIR / "checkpoints").glob(f"{name}_*.json"):
        d = json.loads(p.read_text())
        if d.get("segments"):
            saved[d["segments"][-1]] = d
    if not saved:
        return {}
    newest = max(saved.values(), key=lambda d: d["frames"])
    out: dict[int, str] = {}
    start = 0
    for seg in newest["segments"]:
        d = saved.get(seg)
        if d is None:
            continue
        out[start] = seg
        start = d["frames"]
    return out''', "boundaries")

t = sub(t, """        i = 0
        while i < len(frames):
            if i in marks:
                seg = marks[i]
                emu.note(NARRATION.get(seg, f"segment {seg}"))
            j = i
            while j < len(frames) and frames[j] == frames[i] and j not in marks:
                j += 1
            if j == i:
                j = i + 1
            emu.step(frames[i], j - i)
            i = j""",
"""        def announce(seg: str) -> None:
            head, why = intent.for_segment(seg, NARRATION)
            emu.note(f"{head}||{why}")      # the overlay splits on || into heading and reason

        i = 0
        while i < len(frames):
            if i in marks:
                announce(marks[i])
            j = i + 1
            while j < len(frames) and frames[j] == frames[i] and j not in marks:
                j += 1
            emu.step(frames[i], j - i)
            i = j
        for fr in sorted(f for f in marks if f >= len(frames)):
            announce(marks[fr])             # the final segment's caption lands on the last frame""",
        "record_run.main loop")

t = sub(t, "from zelda import replay", "from zelda import intent, replay", "record_run import")
write("record_run.py", t)

# ---------------------------------------------------------------- render_overlay.py
u = read("render_overlay.py")

u = sub(u, '    bd.text((PX + 16, 60), "THINKING", font=F_SMALL, fill=DIM)',
        '    bd.text((PX + 16, 44), "OBJECTIVE  /  WHY", font=F_SMALL, fill=DIM)', "panel label")

u = sub(u, """    feed: list[str] = []
    ev_i = 0
    shown_events: list[str] = []
    k = 0""",
"""    # One objective on screen at a time, each with a minimum dwell: seventeen segments are shorter
    # than two seconds, and a caption that flashes past is worse than no caption. Identical
    # consecutive objectives merge, so one thought spans a corridor instead of blinking per room.
    timeline: list[tuple[int, str, str, str]] = []
    prev_head = ""
    for fr, txt in events:
        head, _, why = txt.partition("||")
        if timeline and head == timeline[-1][1] and why == timeline[-1][2]:
            continue
        start = max(fr - 1, timeline[-1][0] + 90 if timeline else 0)
        timeline.append((start, head, why, prev_head))
        prev_head = head
    ti = -1

    feed: list[str] = []
    k = 0""", "timeline precompute")

u = sub(u, """        held = set(inputs[k])
        kv = trace.get(k + 1, trace.get(k, {}))
        while ev_i < len(events) and events[ev_i][0] - 1 <= k:
            shown_events.append(events[ev_i][1])
            ev_i += 1

        # header: frame / time
        d.text((W - 16, 18), f"frame {k + 1:05d}   {fmt_time(k + 1)}", font=F_TEXT, fill=TEXT, anchor="rt")

        # thinking: newest intention bright, previous ones dim
        y = 80
        for age, txt in enumerate(reversed(shown_events[-4:])):
            col = ACCENT if age == 0 else DIM
            f = F_BIG if age == 0 else F_SMALL
            for line in textwrap.wrap(txt, 52 if age == 0 else 66)[:3]:
                d.text((PX + 16, y), line, font=f, fill=col)
                y += 20 if age == 0 else 15
            y += 6
            if y > 205:
                break""",
"""        held = set(inputs[k])
        kv = trace.get(k + 1, trace.get(k, {}))
        while ti + 1 < len(timeline) and timeline[ti + 1][0] <= k:
            ti += 1

        # header: frame / time
        d.text((W - 16, 18), f"frame {k + 1:05d}   {fmt_time(k + 1)}", font=F_TEXT, fill=TEXT, anchor="rt")

        # Objective and reason. Neither fades with age: this is what the bot is doing RIGHT NOW, and
        # a dimming objective reads as a stale one. The previous objective sits below it in grey.
        if ti >= 0:
            _, head, why, last = timeline[ti]
            y = 64
            for line in textwrap.wrap(head, 40)[:2]:
                d.text((PX + 16, y), line, font=F_BIG, fill=ACCENT)
                y += 22
            y = max(y + 4, 96)
            for line in textwrap.wrap(why, 54)[:3]:
                d.text((PX + 16, y), line, font=F_TEXT, fill=TEXT)
                y += 18
            if last:
                d.text((PX + 16, 178), "before this: " + last[:44], font=F_SMALL, fill=DIM)
        d.line((PX + 16, 200, W - 16, 200), fill=GRID)""", "objective drawing")

write("render_overlay.py", u)

from zelda import intent  # noqa: E402
print("\nsample captions:")
for n in ("start", "gleeok", "l7_feed", "ow_76", "farm53", "whirl_l6", "g9_ganon", "mystery_seg"):
    h, w = intent.for_segment(n)
    print(f"  {n:12s} {h[:38]:40s} | {w[:60]}")
