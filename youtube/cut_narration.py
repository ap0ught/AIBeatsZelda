"""Script-guided cleanup of the owner's narration (post-processing only; uses narration_words.json from
transcribe_cut.py, so the forty-minute transcription is not repeated).

The owner's note on the first cut: "many times I'll start a sentence, it will chop, and then I'll restart the same
words - very herky jerky." Two causes, both fixed here:
  * the alignment to the script used to match the ABANDONED first start of a sentence ("The map is...") and then throw
    the complete re-read away as a stumble. The alignment now prefers the LAST reading of every script word (a longest-
    common-subsequence run on the reversed sequences), so a restart's first fragment is what gets dropped;
  * joins were hard cuts at word edges. They are now placed in the middle of the silence around each kept span and
    given short fades, and the audio is assembled in one pass.
Also: restarts are pruned on the raw stream first (a phrase said again within a few seconds keeps only the last
reading); his own markers ("oh god let me just redo this whole thing", "scrub that whole part") are found and honoured;
headings he read aloud, stumbled numbers and whisper garbage are dropped; section boundaries come from the alignment;
"for the live outro..." splits an outro section that goes after the run.
Outputs (youtube/voice/): narration.wav (cleaned, loudnorm), narration_sections.json, narration.srt,
narration_transcript.txt, narration_review.txt (per section: what he said; then every dropped stretch)."""
import json
import re
import subprocess
import sys
from array import array
from pathlib import Path

import numpy as np

V = Path("youtube/voice")
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else V / "Recording (133).m4a"
words = json.load(open(V / "narration_words.json"))
ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
        "seventeen eighteen nineteen").split()
TENS = "zero ten twenty thirty forty fifty sixty seventy eighty ninety".split()
NUMW = set(ONES + TENS + ["hundred", "thousand"])
PAUSE = 0.5
GARBAGE = re.compile(r"(..)\1{3,}")


def n2w(n):
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if n < 1000:
        return ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + n2w(n % 100))
    if n < 1000000:
        return n2w(n // 1000) + " thousand" + ("" if n % 1000 == 0 else " " + n2w(n % 1000))
    return str(n)


def norm(s):
    s = s.lower().replace("-", " ").replace("'", "")
    s = re.sub(r"(\d+),(\d{3})", r"\1\2", s)
    s = re.sub(r"\d+", lambda m: n2w(int(m.group())) if len(m.group()) < 7 else m.group(), s)
    s = re.sub(r"[^a-z ]", " ", s)
    return s.split()


def word_ok(i):
    s = words[i][2].lower()
    return len(s) <= 18 and not GARBAGE.search(s)


# ---- the script as spoken words, with each section's first word index
text = (V.parent / "SCRIPT_v3.md").read_text(encoding="utf-8").split("## PART ONE", 1)[1].split("## PART TWO", 1)[0]
script = []
sec_start = []
in_vis = False
for ln in text.splitlines():
    if in_vis:
        in_vis = not ln.rstrip().endswith("]`")
        continue
    if ln.startswith("### "):
        sec_start.append((ln[4:].strip(), len(script)))
        continue
    if ln.startswith("`[VISUAL"):
        in_vis = not ln.rstrip().endswith("]`")
        continue
    if ln.startswith("#") or ln.strip() == "(cloned voice)":
        continue
    script += norm(ln)

# ---- transcript words -> tokens
tok = []
owner = []
for i, w in enumerate(words):
    for t in norm(w[2]):
        tok.append(t)
        owner.append(i)
lw = [w[2].lower().strip(".,!?") for w in words]

# ---- 1. restarts on the raw stream: the LAST copy within the window wins
drop_tok = set()
for n_gram, window in ((5, 16.0), (4, 8.0)):
    x = 0
    while x < len(tok) - n_gram:
        if x in drop_tok:
            x += 1
            continue
        g = tok[x:x + n_gram]
        hit = None
        for y in range(x + n_gram, min(len(tok) - n_gram + 1, x + 120)):
            if words[owner[y]][0] - words[owner[x]][1] > window:
                break
            if tok[y:y + n_gram] == g:
                hit = y
        if hit is not None:
            for k in range(x, hit):
                drop_tok.add(k)
            x = hit
        else:
            x += 1
live = [k for k in range(len(tok)) if k not in drop_tok]
tok2 = [tok[k] for k in live]

# ---- 2. alignment that prefers the LAST reading: LCS on the reversed sequences, backtracked from the front
S = script[::-1]
T = tok2[::-1]
n, m = len(S), len(T)
ids = {}
Si = [ids.setdefault(t, len(ids)) for t in S]
Ti = [ids.get(t, -1) for t in T]
dp = [array("H", [0]) * (m + 1) for _ in range(n + 1)]
for i in range(n - 1, -1, -1):
    row, nxt = dp[i], dp[i + 1]
    si = Si[i]
    for j in range(m - 1, -1, -1):
        if Ti[j] == si:
            row[j] = nxt[j + 1] + 1
        else:
            a, b = nxt[j], row[j + 1]
            row[j] = a if a >= b else b
pairs = []                                  # (script index forward, tok2 index forward)
i = j = 0
while i < n and j < m:
    if Ti[j] == Si[i] and dp[i][j] == dp[i + 1][j + 1] + 1:
        pairs.append((n - 1 - i, m - 1 - j))
        i += 1
        j += 1
    elif dp[i + 1][j] >= dp[i][j + 1]:
        i += 1
    else:
        j += 1
pairs.sort()
s2t = {}
for s_, t_ in pairs:
    s2t.setdefault(s_, live[t_])


def stutter(span):
    bad = set()
    for i in range(len(span)):
        if i >= 2 and span[i] == span[i - 1] == span[i - 2]:
            bad |= {i, i - 1, i - 2}
    return bad


keep_tok = set()
prev_s, prev_t = -1, -1
for s_, t_ in pairs + [(len(script), len(tok2))]:
    gap_t = list(range(prev_t + 1, t_))
    gap_s = s_ - prev_s - 1
    if gap_t:
        span = [tok2[k] for k in gap_t]
        garbled = len(span) >= 6 and len(set(span)) / len(span) < 0.5
        bad = stutter(span)
        if gap_s > 0 and len(gap_t) <= 40 and not garbled:            # his own words for a script span
            keep_tok |= {live[gap_t[k]] for k in range(len(gap_t)) if k not in bad}
        elif len(gap_t) >= 20 and not garbled and len(set(span)) / len(span) >= 0.5:    # a long ad-lib
            keep_tok |= {live[gap_t[k]] for k in range(len(gap_t)) if k not in bad}
    if t_ < len(tok2):
        keep_tok.add(live[t_])
    prev_s, prev_t = s_, t_
keep_words = sorted({owner[k] for k in keep_tok if word_ok(owner[k])})

# ---- 3. scrub markers
SCRUB = re.compile(r"^(oh god |okay |ok |um |uh )*(let me |lets |i m going to |im going to |i ll |ill )?(just )?"
                   r"(redo|scrub|scratch|start over|start again|do that again|do this again|try that again|try this again|say that again)"
                   r"( that| this)?( whole)?( part| thing| sentence| paragraph| line)?( again| over)?$")
i = 0
while i < len(words):
    phrase = None
    for k in range(10, 0, -1):
        if SCRUB.match(" ".join(norm(" ".join(lw[i:i + k])))):
            phrase = k
            break
    if phrase is None:
        i += 1
        continue
    m_end = i + phrase
    start = None
    for off in range(0, 4):
        after = [t for j in range(m_end + off, min(len(words), m_end + off + 6)) for t in norm(words[j][2])][:4]
        for j in range(i - 1, max(-1, i - 80), -1):
            toks = [t for jj in range(j, min(i, j + 6)) for t in norm(words[jj][2])][:4]
            if after and toks == after:
                start = j
                break
        if start is not None:
            break
    if start is None:
        limit = 40 if "whole" in " ".join(lw[i:m_end]) else 25
        start = i - 1
        while start > 0 and i - start < limit and not words[start - 1][2].endswith((".", "?", "!")):
            start -= 1
    for k in range(max(0, start), m_end):
        if k in keep_words:
            keep_words.remove(k)
    i = m_end

# headings read aloud ("number four, practice") and stumbled numbers
heads = [norm(re.sub(r"^\d+b?\.\s*", "", h))[:2] for h, _ in sec_start]
i = 0
while i < len(words) - 1:
    if lw[i] in ("number", "section", "chapter") and norm(lw[i + 1])[:1] and norm(lw[i + 1])[0] in NUMW:
        j = i + 2
        nxt = [t for jj in range(j, min(len(words), j + 3)) for t in norm(words[jj][2])][:2]
        n_extra = 0
        for h in heads:
            if h and nxt[:len(h)] == h:
                n_extra = len(h)
        for k in range(i, min(len(words), j + n_extra)):
            if k in keep_words:
                keep_words.remove(k)
        i = j + n_extra
    else:
        i += 1
run = []
for k in list(keep_words) + [None]:
    isnum = k is not None and norm(words[k][2]) and all(t in NUMW for t in norm(words[k][2]))
    if isnum:
        run.append(k)
    else:
        if len(run) >= 4:
            for r in run:
                keep_words.remove(r)
        run = []
for i in range(len(words)):                      # the "part one" marker he read aloud
    if lw[i] == "part" and i + 1 < len(words) and lw[i + 1] == "one":
        for k in (i, i + 1):
            if k in keep_words:
                keep_words.remove(k)

# ---- 4. sections, and the outro he ad-libbed
sections = []
for name, si in sec_start:
    t = next((s2t[k] for k in range(si, min(len(script), si + 40)) if k in s2t), None)
    if t is None:
        print("no alignment for", name)
        continue
    sections.append([name, owner[t]])
if keep_words and sections and keep_words[0] < sections[0][1]:
    sections.insert(0, ["preamble", keep_words[0]])
outro_at = None
for i in range(len(words) - 3):
    if " ".join(lw[i:i + 4]) in ("for the live outro", "for the outro i", "for the outro im"):
        j = i
        while j < min(len(words), i + 25) and lw[j] != "so":
            j += 1
        for k in range(i, j + 1):
            if k in keep_words:
                keep_words.remove(k)
        outro_at = j + 1
        break
keep_set = set(keep_words)
kept = [(i, words[i]) for i in keep_words]
dropped = [i for i in range(len(words)) if i not in keep_set]

# ---- 5. spans of kept words; cut points in the middle of the surrounding silence; fades; one-pass assembly
spans = []                                     # [first kept word index, last kept word index]
for n_, (i, w) in enumerate(kept):
    if n_ and i - kept[n_ - 1][0] == 1 and w[0] - kept[n_ - 1][1][1] <= 0.9:
        spans[-1][1] = i
    else:
        spans.append([i, i])


def edge(i, side):
    """where to cut around word i: halfway into the silence before/after it, at most 0.3 s out"""
    w = words[i]
    if side == "a":
        prev_end = words[i - 1][1] if i > 0 else 0.0
        return max(prev_end, w[0] - min(0.3, (w[0] - prev_end) / 2)) if w[0] > prev_end else w[0]
    nxt_start = words[i + 1][0] if i + 1 < len(words) else w[1] + 1.0
    return min(nxt_start, w[1] + min(0.3, (nxt_start - w[1]) / 2)) if nxt_start > w[1] else w[1]


cuts = [(edge(a, "a"), edge(b, "b")) for a, b in spans]
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(SRC), "-ac", "1", "-ar", "48000", "-f", "f32le", "-"], capture_output=True).stdout
audio = np.frombuffer(raw, dtype=np.float32)
SR = 48000
FADE = int(0.015 * SR)
ramp = np.linspace(0.0, 1.0, FADE, dtype=np.float32)
pieces = []
out_t = 0.0
w2out = {}
for (a, b), (wa, wb) in zip(cuts, spans):
    seg = audio[int(a * SR):int(b * SR)].copy()
    if len(seg) > 2 * FADE:
        seg[:FADE] *= ramp
        seg[-FADE:] *= ramp[::-1]
    for i in range(wa, wb + 1):
        if i in keep_set:
            w2out[i] = out_t + (words[i][0] - a)
    pieces.append(seg)
    pieces.append(np.zeros(int(PAUSE * SR), dtype=np.float32))
    out_t += len(seg) / SR + PAUSE
total = out_t
mix = np.concatenate(pieces)
tmp = V / "_narration_mono.f32"
tmp.write_bytes(mix.tobytes())
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", "48000", "-ac", "1", "-i", str(tmp), "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11", "-ac", "2", str(V / "narration.wav")], check=True)
tmp.unlink()

sec_out = []
for name, wi in sections:
    k = next((i for i, w in kept if i >= wi), None)
    sec_out.append({"section": name, "start": w2out[k] if k is not None else None})
if outro_at is not None:
    k = next((i for i, w in kept if i >= outro_at), None)
    if k is not None:
        sec_out.append({"section": "outro", "start": w2out[k]})
for n_, s in enumerate(sec_out):
    s["end"] = sec_out[n_ + 1]["start"] if n_ + 1 < len(sec_out) else total
json.dump(sec_out, open(V / "narration_sections.json", "w"), indent=1)


def ts(x):
    return f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int((x % 1) * 1000):03d}"


lines = []
buf = []
t0 = None
for i, w in kept:
    ot = w2out[i]
    if t0 is None:
        t0 = ot
    buf.append(w[2])
    if len(buf) >= 9 or w[2].endswith((".", "?", "!")):
        lines.append((t0, ot + (w[1] - w[0]) + 0.2, " ".join(buf)))
        buf = []
        t0 = None
if buf:
    lines.append((t0, total, " ".join(buf)))
(V / "narration.srt").write_text("".join(f"{k + 1}\n{ts(a)} --> {ts(b)}\n{txt}\n\n" for k, (a, b, txt) in enumerate(lines)), encoding="utf-8")
(V / "narration_transcript.txt").write_text("\n".join(f"[{a:7.1f}] {txt}" for a, b, txt in lines), encoding="utf-8")
rev = []
for s in sec_out:
    rev.append(f"\n=== {s['section']}   {s['start']:.1f} - {s['end']:.1f} s  ({s['end'] - s['start']:.0f} s)\n")
    rev.append(" ".join(w[2] for i, w in kept if s["start"] <= w2out[i] < s["end"]))
rev.append("\n\n=== DROPPED (raw time: words)\n")
k = 0
while k < len(dropped):
    q = k
    while q + 1 < len(dropped) and dropped[q + 1] == dropped[q] + 1:
        q += 1
    rev.append(f"[{words[dropped[k]][0]:7.1f}] " + " ".join(words[x][2] for x in dropped[k:q + 1]))
    k = q + 1
(V / "narration_review.txt").write_text("\n".join(rev), encoding="utf-8")
print(f"kept {len(kept)} of {len(words)} words; cleaned narration {total / 60:.1f} min; {len(spans)} spans")
for s in sec_out:
    print(f"  {s['start']:7.1f} - {s['end']:7.1f}  ({s['end'] - s['start']:5.0f} s)  {s['section']}")
