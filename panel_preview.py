#!/usr/bin/env python3
"""Render the video's reasoning panel on a real game frame, without the video.

The panel in the published video is drawn by render_overlay.py, which composites
it over frames decoded from video/<name>.mkv. Recording is dead under Mono on
Linux (see FINDINGS.md 3.1), so there is no .mkv to decode - but the panel drawing
needs nothing from the video except a game image.

So: replay the run's input log to chosen frames, screenshot each one through the
bridge, and run render_overlay's own drawing code over the stills. The result is
the same panel, on a real frame, at any point in the run.

usage:  python3 panel_preview.py [name] [frame ...]
        python3 panel_preview.py milestone3            # a few representative frames
        python3 panel_preview.py fullgame 10000 20000  # specific frames
"""
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

import render_overlay as R
from zelda import BizHawk, replay

OUT = Path("shots/panel")


def timeline_for(events, min_dwell=30):
    """The same merge + minimum-dwell rule render_overlay uses, so the panel
    shows what the video showed rather than a caption that flashes past."""
    # Prefer caption events. milestone3 interleaves the bot's own diagnostics
    # ("SEGMENT x: best of 30 attempts") with the caption at the same frame, and
    # the last event at a frame wins - so without this the panel shows the
    # diagnostic instead of the caption.
    if any("||" in t for _, t in events):
        events = [(fr, t) for fr, t in events if "||" in t]
    tl, prev = [], ""
    for i, (fr, txt) in enumerate(events):
        head, _, why = txt.partition("||")
        if tl and head == tl[-1][1] and why == tl[-1][2]:
            continue
        nxt = events[i + 1][0] if i + 1 < len(events) else fr + 10 ** 6
        if nxt - fr < min_dwell:
            continue
        tl.append((max(fr - 1, 0), head, why, prev))
        prev = head
    return tl


def frame_index_for(timeline, k):
    """Which timeline entry is on screen at stepped frame k."""
    ti = -1
    while ti + 1 < len(timeline) and timeline[ti + 1][0] <= k:
        ti += 1
    return ti


def panel_base():
    base = Image.new("RGB", (R.W, R.H), R.BG)
    bd = ImageDraw.Draw(base)
    bd.rectangle((R.PX, 0, R.W, R.H), fill=R.PANEL_BG)
    for gy in range(0, R.H, 24):
        bd.line((R.PX, gy, R.W, gy), fill=R.GRID)
    bd.line((R.PX, 0, R.PX, R.H), fill=(40, 48, 60), width=2)
    bd.text((R.PX + 16, 14), "AI CONTROLLER", font=R.F_TITLE, fill=R.ACCENT)
    bd.text((R.PX + 16, 44), "OBJECTIVE  /  WHY", font=R.F_SMALL, fill=R.DIM)
    bd.text((R.PX + 16, 214), "INPUT", font=R.F_SMALL, fill=R.DIM)
    bd.text((R.PX + 16, 334), "GAME STATE (read from RAM)", font=R.F_SMALL, fill=R.DIM)
    bd.text((R.PX + 16, 434), "FRAME STREAM", font=R.F_SMALL, fill=R.DIM)
    return base


def wrap_cols(font, avail_px):
    """How many monospace columns fit in `avail_px` for THIS font.

    render_overlay hardcodes 40 and 54, which are Consolas metrics. With a
    substituted face (DejaVu on Linux) the same character count is wider and the
    third line runs off the panel, so measure the real advance width instead.
    """
    ch = font.getlength("0") or 1
    return max(20, int(avail_px // ch))


def draw_panel(base, game_png, k, inputs, state, timeline, recent):
    inner = R.PW - 32
    head_cols = wrap_cols(R.F_BIG, inner)
    why_cols = wrap_cols(R.F_TEXT, inner)
    im = base.copy()
    im.paste(game_png.convert("RGB").resize((R.GW, R.GH), Image.NEAREST), (R.GX, R.GY))
    d = ImageDraw.Draw(im)

    held = set(inputs[k]) if k < len(inputs) else set()
    kv = {}
    if state is not None:
        for f_ in ("mode", "level", "room", "x", "y", "dir", "hp", "rupees",
                   "keys", "bombs", "sword", "triforce", "lag"):
            kv[f_] = getattr(state, f_, 0)
        kv["hearts"] = state.hearts
        kv["containers"] = state.containers

    d.text((R.W - 16, 18), f"frame {k + 1:05d}   {R.fmt_time(k + 1)}",
           font=R.F_TEXT, fill=R.TEXT, anchor="rt")

    ti = frame_index_for(timeline, k)
    if ti >= 0:
        _, head, why, last = timeline[ti]
        y = 64
        for line in textwrap.wrap(head, head_cols)[:2]:
            d.text((R.PX + 16, y), line, font=R.F_BIG, fill=R.ACCENT)
            y += 22
        y = max(y + 4, 96)
        for line in textwrap.wrap(why, why_cols)[:3]:
            d.text((R.PX + 16, y), line, font=R.F_TEXT, fill=R.TEXT)
            y += 18
        if last:
            d.text((R.PX + 16, 178), "before this: " + last[:head_cols], font=R.F_SMALL, fill=R.DIM)
    d.line((R.PX + 16, 200, R.W - 16, 200), fill=R.GRID)

    R.draw_controller(d, R.PX + 16, 232, held)
    btxt = " + ".join(inputs[k]) if k < len(inputs) and inputs[k] else "(none)"
    d.text((R.PX + 270, 250), "HOLDING", font=R.F_SMALL, fill=R.DIM)
    d.text((R.PX + 270, 268), btxt, font=R.F_BIG, fill=R.ACCENT if held else R.DIM)

    if kv:
        mode = kv.get("mode", 0)
        d.text((R.PX + 16, 352), R.MODES.get(mode, str(mode)), font=R.F_BIG, fill=R.TEXT)
        d.text((R.PX + 270, 352), f"LEVEL {kv.get('level', 0)}", font=R.F_BIG, fill=R.TEXT)
        d.text((R.PX + 380, 352), f"ROOM {kv.get('room', 0):02X}", font=R.F_BIG, fill=R.TEXT)
        d.text((R.PX + 16, 378), f"x {kv.get('x', 0):3d}   y {kv.get('y', 0):3d}   dir {kv.get('dir', 0)}",
               font=R.F_TEXT, fill=R.TEXT)
        # render_overlay.hearts() reads the PACKED trace byte (low nybble = full
        # hearts, high = containers-1). State has already unpacked it, so format
        # from the parsed values rather than feeding it the wrong shape.
        cur = state.hearts if state is not None else 0
        cont = state.containers if state is not None else 0
        d.text((R.PX + 16, 400), f"{cur:g}/{cont}", font=R.F_TEXT,
               fill=R.RED if cur < 1 else R.TEXT)
        d.text((R.PX + 200, 400), f"rupees {kv.get('rupees', 0):3d}", font=R.F_TEXT, fill=R.TEXT)
        d.text((R.PX + 330, 400), f"bombs {kv.get('bombs', 0):2d}", font=R.F_TEXT, fill=R.TEXT)
        d.text((R.PX + 430, 400), f"keys {kv.get('keys', 0)}", font=R.F_TEXT, fill=R.TEXT)
        d.text((R.PX + 16, 420), f"sword {kv.get('sword', 0)}   triforce {kv.get('triforce', 0):02x}   lag {kv.get('lag', 0)}",
               font=R.F_SMALL, fill=R.DIM)

    # the frame feed, built from the trace the same way render_overlay does:
    # one line per recent frame, shaded by age, newest in Zelda green
    rows = []
    for age, (kk, st) in enumerate(recent):
        b = " + ".join(inputs[kk]) if kk < len(inputs) and inputs[kk] else "-"
        q = {"mode": st.mode, "room": st.room, "x": st.x, "y": st.y,
             "sword": st.sword, "lag": st.lag}
        rows.append(f"f{kk + 1:05d} {b[:11]:<11} m={q['mode']:02X} r={q['room']:02X} "
                    f"({q['x']:3d},{q['y']:3d}) sw={q['sword']} lag={q['lag']}")
    for i, line in enumerate(rows):
        age = len(rows) - 1 - i
        shade = max(70, 220 - age * 10)
        d.text((R.PX + 16, 454 + i * 15), line, font=R.F_FEED,
               fill=(shade, shade, shade) if age else R.GREEN)
    return im


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "milestone3"
    inputs, events, trace = R.load_logs(name)
    if not trace:
        # milestone3 calls save_inputs(), which writes inputs + events but no
        # trace; only record=True runs write one, and recording is dead on Linux.
        # Not a problem: the panel reads its state from live RAM, below.
        print("no .trace.txt - reading GAME STATE from live RAM instead")
    print(f"{name}: {len(inputs)} frames, {len(events)} events, {len(trace)} trace rows")

    if len(sys.argv) > 2:
        wanted = [int(a) for a in sys.argv[2:]]
    else:
        # One frame from the middle of a few well-separated *captioned* segments.
        # The events file also carries the bot's own setup notes ("POWER ON.
        # Waiting for the title screen...") which are not captions and read badly
        # in the objective slot, so only take events carrying a ||.
        caps = [(fr, txt) for fr, txt in events if "||" in txt]
        wanted = []
        for i, (fr, txt) in enumerate(caps):
            nxt = caps[i + 1][0] if i + 1 < len(caps) else fr
            if nxt - fr > 200:                 # a segment with real duration
                wanted.append(fr + (nxt - fr) // 2)
            if len(wanted) >= 4:
                break

    timeline = timeline_for(events)
    print(f"timeline entries after the dwell rule: {len(timeline)}")

    base = panel_base()
    OUT.mkdir(parents=True, exist_ok=True)
    targets = sorted(set(min(w, len(inputs) - 1) for w in wanted))
    print("rendering frames:", targets)

    states = {}
    with BizHawk(log_name="panel.log") as emu:
        i = 0
        for target in targets:
            while i <= target:
                j = i
                while j < len(inputs) and inputs[j] == inputs[i]:
                    j += 1
                emu.step(inputs[i], j - i)
                states[j - 1] = emu.state()
                i = j
            states[target] = emu.state()      # targets can be mid-batch
            shot = emu.screenshot(f"_panel_src_{target:06d}")
            recent = [(kk, states[kk]) for kk in sorted(states) if target - 16 <= kk <= target]
            im = draw_panel(base, Image.open(shot), target, inputs, states[target], timeline, recent)
            p = OUT / f"{name}_f{target:06d}.png"
            im.save(p)
            head = timeline[frame_index_for(timeline, target)][1] if timeline else "(none)"
            print(f"  {p}   [{head}]")

    print("done ->", OUT)


if __name__ == "__main__":
    main()
