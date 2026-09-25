"""The owner's narration: transcribe with word timestamps, find the section headings he read aloud, cut the flubs and
long gaps out, and write the cleaned narration plus its section timing for build_v3.py.

usage (with his venv, which has faster-whisper):
  "G:/Faceless youtube channel/tools/vibevoice-env/Scripts/python.exe" youtube/transcribe_cut.py youtube/voice/<recording>
Outputs in youtube/voice/: narration_raw_16k.wav, narration_words.json, narration.wav (cleaned, 48 kHz),
narration_sections.json, narration.srt, narration_transcript.txt"""
import json, re, subprocess, sys
from pathlib import Path
try:
    import truststore; truststore.inject_into_ssl()
except ImportError:
    pass
import os; os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")

src = Path(sys.argv[1]); V = src.parent
raw16 = V / "narration_raw_16k.wav"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ac", "1", "-ar", "16000", str(raw16)], check=True)
from faster_whisper import WhisperModel
m = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
segs, _ = m.transcribe(str(raw16), language="en", word_timestamps=True, beam_size=5, condition_on_previous_text=True)
words = [(w.start, w.end, w.word.strip(), w.probability) for s in segs for w in (s.words or [])]
json.dump(words, open(V / "narration_words.json", "w"), indent=0)
print(len(words), "words,", f"{words[-1][1] / 60:.1f} min raw")

# section headings from the script, matched against the read ("Section four, practice" / "four, practice" / "practice")
script = (V.parent / "SCRIPT_v3.md").read_text(encoding="utf-8")
heads = re.findall(r"^### (.+)$", script.split("## PART ONE", 1)[1].split("## PART TWO", 1)[0], re.M)
def norm(s): return re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()
text_words = [norm(w[2]) for w in words]
flat = [(i, t[0]) for i, t in enumerate(text_words) if t]
marks = []
for h in heads:
    key = norm(re.sub(r"^\d+b?\.\s*", "", h))[:3]         # first three words of the heading
    best = None
    for j in range(len(flat) - len(key) + 1):
        if [flat[j + k][1] for k in range(len(key))] == key and (best is None or (marks and flat[j][0] > marks[-1][1])):
            best = flat[j][0]; break
    marks.append((h, best))
    print(f"{'found' if best is not None else 'MISSING':8s} {h}  ->  word {best}")

# flubs: a restarted sentence = the same 3+ words repeated within 6 seconds; keep the LAST reading, drop the earlier
drop = set()
for i in range(len(words)):
    for j in range(i + 3, min(len(words), i + 40)):
        if words[j][0] - words[i][1] > 6: break
        if [t for t in text_words[i:i + 3]] == [t for t in text_words[j:j + 3]] and all(text_words[i:i + 3]):
            for k in range(i, j): drop.add(k)
            break
# a review file: every dropped span with what replaced it, so a wrong cut can be spotted and undone
rev = []
i = 0
while i < len(words):
    if i in drop:
        j = i
        while j in drop: j += 1
        dropped = ' '.join(w[2] for w in words[i:j]); kept = ' '.join(w[2] for w in words[j:j + (j - i)])
        rev.append(f"[{words[i][0]:7.1f}] DROPPED: {dropped}" + chr(10) + f"          KEPT:    {kept}")
        i = j
    else:
        i += 1
(V / "narration_cuts_review.txt").write_text(chr(10).join(rev), encoding="utf-8")
# keep list -> cut list in the raw timeline (words kept, gaps > 0.9 s shortened to 0.55 s)
keep = [w for i, w in enumerate(words) if i not in drop]
cuts = []; t = keep[0][0] - 0.3; cur_a = max(0.0, t)
out_t = 0.0; secs = {}; srt = []; kept_map = []
for i, w in enumerate(keep):
    gap = w[0] - (keep[i - 1][1] if i else w[0])
    if i and gap > 0.9:
        cuts.append((cur_a, keep[i - 1][1] + 0.35)); out_t += cuts[-1][1] - cuts[-1][0] + 0.55; cur_a = w[0] - 0.2
    kept_map.append((w, out_t + (w[0] - cur_a)))
cuts.append((cur_a, keep[-1][1] + 0.5))
# section starts in the cleaned timeline
raw2clean = {}
for w, ot in kept_map: raw2clean[w] = ot
sections = []
for (h, widx), (h2, nidx) in zip(marks, marks[1:] + [(None, None)]):
    if widx is None: continue
    w = words[widx]; start = next((ot for ww, ot in kept_map if ww[0] >= w[0]), None)
    end = next((ot for ww, ot in kept_map if nidx is not None and ww[0] >= words[nidx][0]), None)
    sections.append({"section": h, "start": start, "end": end})
total = sum(b - a for a, b in cuts) + 0.55 * (len(cuts) - 1)
for s in sections:
    if s["end"] is None: s["end"] = total
json.dump(sections, open(V / "narration_sections.json", "w"), indent=1)
# render the cleaned narration with ffmpeg: concat of the kept spans with 0.55 s silence between
parts = []
for k, (a, b) in enumerate(cuts):
    p = V / f"_cut_{k:03d}.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(a), "-to", str(b), "-i", str(src), "-ac", "2", "-ar", "48000", str(p)], check=True)
    parts.append(p)
    if k < len(cuts) - 1:
        g = V / f"_gap_{k:03d}.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "0.55", str(g)], check=True)
        parts.append(g)
lst = V / "_narration.txt"; lst.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts), encoding="utf-8")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", str(V / "narration.wav")], check=True)
for p in parts: p.unlink()
# transcript and srt in the cleaned timeline
def ts(x): return f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int((x % 1) * 1000):03d}"
lines = []; buf = []; t0 = None
for w, ot in kept_map:
    if t0 is None: t0 = ot
    buf.append(w[2])
    if len(buf) >= 9 or w[2].endswith((".", "?", "!")):
        lines.append((t0, ot + (w[1] - w[0]), " ".join(buf))); buf = []; t0 = None
if buf: lines.append((t0, kept_map[-1][1] + 0.5, " ".join(buf)))
(V / "narration.srt").write_text("".join(f"{i + 1}\n{ts(a)} --> {ts(b)}\n{txt}\n\n" for i, (a, b, txt) in enumerate(lines)), encoding="utf-8")
(V / "narration_transcript.txt").write_text("\n".join(f"[{a:7.1f}] {txt}" for a, b, txt in lines), encoding="utf-8")
print(f"cleaned narration {total / 60:.1f} min ({len(drop)} flubbed words dropped, {len(cuts) - 1} gaps shortened); sections:")
for s in sections: print(f"  {s['start']:7.1f} - {s['end']:7.1f}  {s['section']}")
