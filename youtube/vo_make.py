# -*- coding: utf-8 -*-
"""Narration for the documentary in the owner's cloned voice, generated locally with VibeVoice.

Reuses the owner's own VibeVoice setup (G:\\Faceless youtube channel\\tools: the 7B model at 4-bit, his cleaned
reference voice, and the same gates his vo_runner2.py applies - a whisper garble check with a cfg retry ladder, a
between-words noise floor, and a level-drift check). Nothing in that folder is modified.

Run with HIS venv python, only when his own VO queue is idle (the 7B model needs the whole 8 GB card):
  "G:\\Faceless youtube channel\\tools\\vibevoice-env\\Scripts\\python.exe" youtube\\vo_make.py [--ref path] [--only 3,7]

Input : youtube/SCRIPT_v2.md - PART ONE paragraphs (visual notes and headings are skipped)
Output: youtube/vo/chunks/NN.wav, youtube/vo/narration.wav (chunks joined with a paragraph pause),
        youtube/vo/manifest.json (chunk text, timing in the joined file, gate scores)"""
import argparse
import difflib
import io
import json
import os
import re
import sys
import time

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")

TOOLS = r"G:\Faceless youtube channel\tools"
MODEL = os.environ.get("VV_MODEL", os.path.join(TOOLS, "models", "VibeVoice-Large"))
QUANT = os.environ.get("VV_QUANT", "4bit")
HOUSE_REF = os.path.join(TOOLS, "voice_ref", "mrowe-ref-calm-clean.wav")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "vo")
MAX_WORDS = 170            # words per generation: VibeVoice speeds up on long single turns
PAUSE = 0.55               # seconds of silence between paragraphs in the joined narration
GARBLE_MIN = 0.90
FLOOR_MAX_DB = -65.0
DRIFT_MAX_DB = 3.0

NUMWORDS = set("""zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen
sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million
point half quarter percent first second third fourth fifth""".split())


def norm(s):
    s = s.lower().replace("-", " ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return [t for t in s.split() if not t.isdigit() and not re.match(r"^\d", t) and t not in NUMWORDS]


def script_chunks(path):
    """PART ONE of the script as (section, chunk_text) pairs: paragraphs grouped up to MAX_WORDS, never across a
    section heading, so every join lands on a paragraph pause."""
    text = io.open(path, encoding="utf-8").read()
    body = text.split("## PART ONE", 1)[1].split("## PART TWO", 1)[0]
    sections = []
    cur = None
    for block in re.split(r"\n\s*\n", body):
        lines = []
        in_visual = False
        for ln in block.strip().splitlines():
            if in_visual:                                  # a visual note that wraps over several lines
                in_visual = not ln.rstrip().endswith("]`")
                continue
            if ln.startswith("### "):
                cur = ln[4:].strip()
                sections.append((cur, []))
            elif ln.startswith("`[VISUAL"):
                in_visual = not ln.rstrip().endswith("]`")
            elif ln.startswith("#") or ln.strip() == "(cloned voice)":
                continue
            else:
                lines.append(ln)
        b = " ".join(lines).strip()
        if not b:
            continue
        para = " ".join(b.split())
        if cur is None:
            cur = "intro"
            sections.append((cur, []))
        sections[-1][1].append(para)
    chunks = []
    for sec, paras in sections:
        buf = []
        for p in paras:
            if buf and len(" ".join(buf + [p]).split()) > MAX_WORDS:
                chunks.append((sec, buf))
                buf = []
            buf.append(p)
        if buf:
            chunks.append((sec, buf))
    return chunks


def quiet_floor(path):
    import numpy as np
    import soundfile as sf
    a, sr = sf.read(path)
    if a.ndim > 1:
        a = a.mean(axis=1)
    n = int(0.1 * sr)
    if len(a) < 2 * n:
        return None
    fr = [a[i:i + n] for i in range(0, len(a) - n, n)]
    db = np.array([20 * np.log10(np.sqrt(np.mean(f ** 2)) + 1e-12) for f in fr])
    peak = float(np.percentile(db, 95))
    silent = db[db < peak - 35.0]
    if len(silent) >= max(3, int(0.02 * len(db))):
        return float(np.median(silent))
    return float(np.percentile(db, 12))


def mean_db(a, sr, t0, t1):
    import numpy as np
    seg = a[int(t0 * sr):int(t1 * sr)]
    return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12) if len(seg) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default=HOUSE_REF)
    ap.add_argument("--only", default="", help="comma-separated chunk numbers to (re)generate")
    ap.add_argument("--script", default=os.path.join(HERE, "SCRIPT_v2.md"))
    ap.add_argument("--tag", default="", help="suffix for the output folder (A/B of references)")
    ap.add_argument("--steps", type=int, default=int(os.environ.get("VV_STEPS", "20")))
    args = ap.parse_args()
    out = OUT + (("_" + args.tag) if args.tag else "")
    os.makedirs(os.path.join(out, "chunks"), exist_ok=True)
    chunks = script_chunks(args.script)
    only = {int(x) for x in args.only.split(",") if x.strip()}
    print(f"{len(chunks)} chunks, {sum(len(' '.join(c).split()) for _, c in chunks)} words; ref {args.ref}", flush=True)

    import torch
    import soundfile as sf
    import numpy as np
    from faster_whisper import WhisperModel
    from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalGenerationInference
    from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor

    t0 = time.time()
    processor = VibeVoiceProcessor.from_pretrained(MODEL)
    kw = dict(torch_dtype=torch.bfloat16, device_map="cuda", attn_implementation="sdpa")
    if QUANT == "4bit":
        from transformers import BitsAndBytesConfig
        kw.pop("torch_dtype")
        kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                       bnb_4bit_compute_dtype=torch.bfloat16,
                                                       bnb_4bit_use_double_quant=True)
    model = VibeVoiceForConditionalGenerationInference.from_pretrained(MODEL, **kw)
    model.eval()
    try:
        model.set_ddpm_inference_steps(args.steps)
    except Exception as e:
        print("ddpm steps:", str(e)[:80])
    whisper = WhisperModel("base", device="cpu", compute_type="int8")
    print(f"models ready in {time.time() - t0:.0f}s", flush=True)

    def generate(text, path, cfg):
        script = "Speaker 1: " + " ".join(text.split())
        inputs = processor(text=[script], voice_samples=[[args.ref]], padding=True, return_tensors="pt",
                           return_attention_mask=True)
        o = model.generate(**inputs, max_new_tokens=None, cfg_scale=cfg, tokenizer=processor.tokenizer,
                           generation_config={"do_sample": False}, verbose=False)
        processor.save_audio(o.speech_outputs[0], output_path=path)

    mpath = os.path.join(out, "manifest.json")
    manifest = json.load(io.open(mpath, encoding="utf-8")) if os.path.exists(mpath) else {}
    for i, (sec, paras) in enumerate(chunks, 1):
        key = f"{i:02d}"
        wav = os.path.join(out, "chunks", key + ".wav")
        text = " ".join(paras)
        done = manifest.get(key, {})
        if only and i not in only:
            continue
        if not only and done.get("status") == "PASS" and os.path.exists(wav) and done.get("text") == text:
            continue
        best = None
        for tries, cfg in enumerate((1.3, 1.45, 1.6), 1):
            t1 = time.time()
            cand = wav + f".try{tries}.wav"
            try:
                generate(text, cand, cfg)
            except Exception as e:
                print(f"[{key}] GEN_ERROR {str(e)[:100]}", flush=True)
                break
            dur = sf.info(cand).duration
            segs, _ = whisper.transcribe(cand, language="en", vad_filter=True)
            hyp = " ".join(s.text for s in segs)
            g = difflib.SequenceMatcher(None, norm(text), norm(hyp)).ratio()
            floor = quiet_floor(cand)
            a, sr = sf.read(cand)
            if a.ndim > 1:
                a = a.mean(axis=1)
            drift = abs((mean_db(a, sr, 0, 15) or 0) - (mean_db(a, sr, max(0, dur - 15), dur) or 0)) if dur >= 20 else 0.0
            ok = g >= GARBLE_MIN and (floor is None or floor <= FLOOR_MAX_DB) and drift <= DRIFT_MAX_DB
            rec = {"try": tries, "cfg": cfg, "garble": round(g, 3), "floor_db": None if floor is None else round(floor, 1),
                   "drift_db": round(drift, 2), "dur": round(dur, 2), "path": cand, "ok": ok, "hyp": hyp}
            print(f"[{key}] {sec[:28]:28s} try {tries} cfg {cfg}: {dur:5.1f}s garble {g:.3f} floor {floor} drift {drift:.1f} "
                  f"{'PASS' if ok else 'fail'} ({time.time() - t1:.0f}s)", flush=True)
            if best is None or (ok and not best["ok"]) or (ok == best["ok"] and g > best["garble"]):
                best = rec
            if ok:
                break
        if best is None:
            manifest[key] = {"status": "GEN_ERROR", "text": text, "section": sec}
        else:
            os.replace(best["path"], wav)
            for tries in (1, 2, 3):
                p = wav + f".try{tries}.wav"
                if os.path.exists(p):
                    os.remove(p)
            manifest[key] = {"status": "PASS" if best["ok"] else "SOFT", "text": text, "section": sec, "words": len(text.split()),
                             **{k: v for k, v in best.items() if k not in ("path", "ok")}}
        io.open(mpath, "w", encoding="utf-8").write(json.dumps(manifest, indent=1))

    # join
    import soundfile as sf
    import numpy as np
    parts = []
    t = 0.0
    timing = []
    sr0 = None
    for i, (sec, paras) in enumerate(chunks, 1):
        key = f"{i:02d}"
        wav = os.path.join(out, "chunks", key + ".wav")
        if not os.path.exists(wav):
            continue
        a, sr = sf.read(wav)
        if a.ndim > 1:
            a = a.mean(axis=1)
        sr0 = sr0 or sr
        timing.append({"chunk": key, "section": sec, "start": round(t, 3), "end": round(t + len(a) / sr, 3),
                       "text": " ".join(paras)})
        parts.append(a)
        parts.append(np.zeros(int(PAUSE * sr)))
        t += len(a) / sr + PAUSE
    if parts:
        sf.write(os.path.join(out, "narration.wav"), np.concatenate(parts), sr0)
        io.open(os.path.join(out, "timing.json"), "w", encoding="utf-8").write(json.dumps(timing, indent=1))
        print(f"narration.wav: {t / 60:.1f} min, {len(timing)} chunks", flush=True)


if __name__ == "__main__":
    main()
