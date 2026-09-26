"""Render youtube/SCRIPT_v3.md as a readable transcript.

The script is hard-wrapped for the page and interleaves spoken prose with
[VISUAL] shot directions that were never read aloud. This walks it and emits
prose as paragraphs, cues as blockquotes, and drops the production meta-commentary
in the preamble. Run from the harness root:

    python3 script_to_transcript.py
"""
import re
import sys
from pathlib import Path

SRC = Path("youtube/SCRIPT_v3.md")
DST = Path("TRANSCRIPT.md")

VIDEO_URL = "https://www.youtube.com/watch?v=mBalZml520o"
VIDEO_TITLE = "I Gave an AI Zelda and One Rule: Don't Cheat."
CHANNEL = "Bears Gaming Den"
PUBLISHED = "2026-09-23"
DURATION = "48:17 (2,897 s)"

HEADER = f"""# Transcript — the narration script

**Video:** [{VIDEO_TITLE}]({VIDEO_URL})
Channel: {CHANNEL} - published {PUBLISHED} - {DURATION}

The harness in this repository is what made that video. This file is its
**narration script**, rendered from `youtube/SCRIPT_v3.md` by
`script_to_transcript.py` so the two cannot drift apart.

## Read this before treating it as a transcript

It is the script, not a transcript of the finished video, and the difference
matters:

* The published narration was **read aloud** and then transcribed with
  faster-whisper by `youtube/transcribe_cut.py`, which also cuts the flubs and
  long gaps and stamps the section timings. Its output -
  `youtube/voice/narration_transcript.txt` and `narration.srt` - is **not in this
  repository**; `youtube/voice/` holds the author's own recordings and was never
  committed. So the words as actually spoken, after the flubs were cut, cannot be
  recovered from here. What follows is what was *written to be read*.
* The **live intro and live outro are not here at all.** They were filmed on
  camera in unscripted words and exist only in the video.
* One line in the script's intro bullets claims the narration is the author's
  voice "cloned by the same computer". The tooling contradicts that -
  `transcribe_cut.py` describes "the owner's narration" and the section headings
  "he read aloud" - so treat the cloned-voice line as unconfirmed and the tooling
  as the better evidence.

## What the markers mean

* `> [visual]` entries are shot directions. They were never spoken. They name real
  footage or real artefacts - emulator windows, log files, the journal, the
  cartridge - and paths in them are relative to `youtube/`.
* The **on-screen reasoning panel** burned into the footage during the run is a
  separate track and is not here. It lives in `zelda/captions.py`: one entry per
  segment, giving the objective and the reason, for every segment of the verified
  37:02 run.

If you want the intro, the outro, or the as-spoken wording, the video exposes an
automatic caption track (`en-orig`). It is speech-to-text rather than an authored
transcript, and it is the only place the unscripted sections exist as text:

```
yt-dlp --write-auto-subs --sub-lang en-orig --skip-download "{VIDEO_URL}"
```

The run itself is in this repository and is better than any description of it.
`runs/run6/inputs.txt` replays from power-on to the ending, byte-exact, in about
three minutes - see `README.md`.

---

"""

VISUAL_END = re.compile(r"\]\s*`?\s*$")
# Must be anchored. The script's own preamble says "Every `[VISUAL]` line is not
# read", and a substring test opens a block there that never closes on that line -
# swallowing PART ONE and the first section whole.
VISUAL_OPEN = re.compile(r"^`?\s*\[VISUAL")


def parse(text):
    """-> list of (kind, value) with kind in head/meta/visual/text."""
    out = []
    para, bullet, visual = [], [], None

    def flush_para():
        if para:
            joined = re.sub(r"\s+", " ", " ".join(para)).strip()
            para.clear()
            if joined:
                out.append(("text", joined))

    def flush_list():
        if bullet:
            out.append(("list", list(bullet)))
            bullet.clear()

    for raw in text.splitlines():
        line = raw.strip()

        if visual is not None:                       # inside a [VISUAL] block
            visual.append(line)
            if VISUAL_END.search(line):
                joined = re.sub(r"\s+", " ", " ".join(visual))
                joined = re.sub(r"^`?\[VISUAL[^:]*:\s*", "", joined)
                joined = re.sub(r"\]\s*`?$", "", joined).strip()
                visual = None
                if joined:
                    out.append(("visual", joined))
            continue

        if VISUAL_OPEN.match(line):                 # opens a [VISUAL] block
            flush_para()
            flush_list()
            visual = [line]
            if VISUAL_END.search(line):
                joined = re.sub(r"\s+", " ", " ".join(visual))
                joined = re.sub(r"^`?\[VISUAL[^:]*:\s*", "", joined)
                joined = re.sub(r"\]\s*`?$", "", joined).strip()
                visual = None
                if joined:
                    out.append(("visual", joined))
            continue

        if line.startswith("#"):
            flush_para()
            flush_list()
            title = line.lstrip("#").strip()
            out.append(("head", title))
            continue

        if not line:
            flush_para()
            flush_list()
            continue

        # *emphasis* - one wrapped run, not a list item
        if (line.startswith("*") and line.endswith("*") and len(line) > 2
                and not line.startswith("* ")):
            flush_para()
            flush_list()
            out.append(("meta", line.strip("*")))
            continue

        # a markdown list item. Consecutive items become one list, so they must not
        # be folded into a single run-on paragraph the way prose is.
        if line.startswith("* ") or line.startswith("- "):
            flush_para()
            bullet.append(line[2:].strip())
            continue
        flush_list()

        para.append(line)

    flush_para()
    return out


def main():
    items = parse(SRC.read_text(encoding="utf-8"))
    counts = {}
    for k, _ in items:
        counts[k] = counts.get(k, 0) + 1
    print("parsed:", counts, file=sys.stderr)

    parts = []                                  # (title, [(kind, value)])
    for kind, value in items:
        if kind == "head":
            upper = value.upper()
            if upper.startswith("LIVE INTRO") or upper.startswith("LIVE OUTRO"):
                continue                          # unscripted; exists only in the video
            if value.isupper() or value.startswith("PART"):
                parts.append((value, []))
            elif parts:
                parts[-1][1].append(("head", value))
        elif parts:
            parts[-1][1].append((kind, value))

    body = []
    for title, entries in parts:
        body.append(f"\n## {title}\n")
        for kind, value in entries:
            if kind == "head":
                body.append(f"\n### {value}\n")
            elif kind == "meta":
                body.append(f"\n> *{value}*\n")
            elif kind == "visual":
                body.append(f"\n> [visual] {value}\n")
            elif kind == "list":
                body.append("\n" + "".join(f"* {item}\n" for item in value))
            else:
                body.append(f"\n{value}\n")

    DST.write_text(HEADER + "".join(body), encoding="utf-8")
    print(f"wrote {DST} - {len(parts)} parts", file=sys.stderr)


if __name__ == "__main__":
    main()
