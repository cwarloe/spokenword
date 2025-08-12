
# Coqui XTTS Local TTS Project (Ready-to-Run)

This repo is a **ready-to-run** offline TTS setup using **Coqui XTTS v2**. It demonstrates:

- Single-voice OR multi-voice generation
- Inline pauses: `[pause:seconds]`
- Background music: `[bgmusic:filename]` (uses `music/calm.wav` by default)
- One-click run on Windows via `script.bat`

> **Note:** The four files in `voices/` are **placeholder WAVs** (simple tones) so the project runs immediately. Replace them later with real, license-free 6–10s speech clips for proper voice cloning (e.g., from Mozilla Common Voice CC0 or LibriVox public domain).

## Quick Start (Windows)

1. Double-click `script.bat` (first run sets up a virtual environment and installs deps).
2. Choose **2** (multi-voice mode) at the prompt to hear tag parsing with pauses & music.
3. Find the result in `outputs/`.

## Quick Start (Mac/Linux)

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install TTS pydub
python tts_script.py
```

## Replacing the placeholder voices

Drop real WAVs (mono, 16-bit, ≥22kHz, ~6–10s) into `voices/`:
- `teen_male.wav`
- `teen_female.wav`
- `mid_male.wav`
- `mid_female.wav`

Or add new names and reference them in `text.txt` using `[voice:your_name]`.

## Licensing
This repo contains only orchestration code and synthetic placeholder audio. You are responsible for ensuring any real `voices/` or `music/` assets are used in compliance with their licenses and with consent.
