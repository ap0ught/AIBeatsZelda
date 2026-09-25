# Voice-over plan (owner's decision, 2026-09-21)

Owner dropped `voice/Recording (127).m4a` (4:23). When run 5 is done: transcribe it, learn how he talks, tidy stutters
and pauses, write the script in HIS voice, and generate the whole narration locally with VibeVoice as a clone of him.
His on-camera intro and outro stay live. Disclose in the video that the narration is his cloned voice.

Research (2026-09-21, agent report; unverified items flagged there):
* Code: MIT fork https://github.com/vibevoice-community/VibeVoice (pins transformers==4.51.3; Microsoft removed the TTS
  code from its own repo). flash-attn optional (SDPA fallback).
* Model that fits the RTX 3060 Ti 8 GB: `microsoft/VibeVoice-1.5B` (5.41 GB, bf16, ~6-7 GB VRAM). Optional quality
  upgrade: `DevParker/VibeVoice7b-low-vram` folder `4bit/` (6.63 GB, NF4, only just fits - nothing else on the GPU).
  EMULATORS MUST BE CLOSED while it runs (they hold ~7.9 GB VRAM between them).
* Reference: a clean 30-60 s `.wav` cut from his recording -> `demo/voices/en-Scott_man.wav` (24 kHz mono is made
  internally); select with `--speaker_names Scott`; every script line starts `Speaker 1:`.
* Long narration: 150-250 words per generation, same reference + same seed, join at paragraph pauses, re-roll bad
  sections; cfg_scale 1.3; no sampling; spell out numbers ("thirty-nine fifteen"); avoid openers like "Welcome to"
  (they trigger background music).
* Speech-to-text: faster-whisper on CPU int8, `large-v3-turbo` (1.62 GB) or `small.en` (0.49 GB), word timestamps.
* Downloads needing the owner's OK: torch 2.14.0+cu126 wheel (2.60 GB, download.pytorch.org), fork + deps (~0.3 GB,
  GitHub/PyPI), VibeVoice-1.5B (5.41 GB, huggingface.co/microsoft/VibeVoice-1.5B), faster-whisper (~65 MB, PyPI) +
  whisper large-v3-turbo CT2 (1.62 GB, huggingface.co/mobiuslabsgmbh/faster-whisper-large-v3-turbo). Optional: 7B NF4
  (6.63 GB) + bitsandbytes (39 MB).
* YouTube: cloning one's own voice for voice-over is listed as NOT needing the altered-content label
  (support.google.com/youtube/answer/14328491) - disclose anyway, it is on-theme.

## Found on this machine (2026-09-21)
The owner ALREADY runs VibeVoice locally for another project: a process
`G:\Faceless youtube channel\tools\vibevoice-env\Scripts\pythonw.exe -u vo_runner2.py td-batch3-fixes.json` was live
(and holding the GPU) while I worked. So there is an installed environment (`...\tools\vibevoice-env`) and a working
runner script (`vo_runner2.py`) - probably no downloads are needed at all. That folder is outside this project: ask
before reading or reusing it, never touch its running jobs, and do not run GPU work while his batch is going.
