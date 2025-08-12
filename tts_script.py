"""
Non-interactive & CI-friendly TTS script
- DRY_RUN=1: skip model download, synthesize silence segments, export WAV
- MODE=1 or MODE=2 to skip prompts; if not set and no TTY, defaults to MODE=2
"""

import os
import re
import sys
from pydub import AudioSegment

DRY_RUN = os.getenv("DRY_RUN") == "1"
MODE_ENV = os.getenv("MODE")  # "1" or "2"

# Config
text_file = "text.txt"
voices_dir = "voices"
music_dir = "music"
output_dir = "outputs"
default_pause = 0.5  # seconds
music_volume_db = -12  # dB
fade_ms = 600  # ms

# Read text
if not os.path.exists(text_file):
    print("❌ Missing text.txt.")
    raise SystemExit(1)
with open(text_file, "r", encoding="utf-8") as f:
    raw_text = f.read().strip()
if not raw_text:
    print("❌ No text in text.txt.")
    raise SystemExit(1)

os.makedirs(output_dir, exist_ok=True)

# Lazy import TTS only if not dry-run
tts = None
if not DRY_RUN:
    print("\n🔄 Loading XTTS v2 model...")
    from TTS.api import TTS  # heavy import; avoid in DRY_RUN
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False)

def synth_text_to_wav(token_text: str, voice_path: str | None, tmp_wav: str) -> AudioSegment:
    """XTTS in normal mode; silence placeholder in DRY_RUN."""
    if DRY_RUN:
        approx_sec = max(0.6, min(6.0, len(token_text) / 90.0))  # rough timing stand-in
        seg = AudioSegment.silent(duration=int(approx_sec * 1000))
        seg.export(tmp_wav, format="wav")
        return seg
    else:
        if voice_path:
            tts.tts_to_file(text=token_text, speaker_wav=voice_path, language="en", file_path=tmp_wav)
        else:
            tts.tts_to_file(text=token_text, file_path=tmp_wav)
        return AudioSegment.from_wav(tmp_wav)

def run_multi_voice(raw_text: str):
    token_pattern = r"(\[voice:.*?\]|\[pause:.*?\]|\[bgmusic:.*?\])"
    tokens = re.split(token_pattern, raw_text, flags=re.I)

    final_segments = []
    current_music = None
    current_voice_path = None

    for token in tokens:
        token = token.strip()
        if not token:
            continue

        if token.lower().startswith("[voice:"):
            voice_name = token[7:-1].strip().lower()
            path = os.path.join(voices_dir, f"{voice_name}.wav")
            if os.path.exists(path):
                current_voice_path = path
                print(f"🎙 Switched to voice: {voice_name}")
            else:
                print(f"⚠️ Voice '{voice_name}' not found. Using default voice.")
                current_voice_path = None

        elif token.lower().startswith("[pause:"):
            try:
                pause_time = float(token[7:-1].strip())
                print(f"⏸ Pause for {pause_time} seconds")
                final_segments.append(AudioSegment.silent(duration=int(pause_time * 1000)))
            except ValueError:
                print("⚠️ Invalid pause tag. Using default pause.")
                final_segments.append(AudioSegment.silent(duration=int(default_pause * 1000)))

        elif token.lower().startswith("[bgmusic:"):
            music_name = token[9:-1].strip()
            music_path = os.path.join(music_dir, music_name)
            if os.path.exists(music_path):
                print(f"🎼 Switching background music to {music_name}")
                current_music = AudioSegment.from_file(music_path).apply_gain(music_volume_db)
            else:
                print(f"⚠️ Music file '{music_name}' not found. No background music will play.")
                current_music = None

        else:
            print(f"💬 Speaking: {token[:60]}...")
            tmp_wav = os.path.join(output_dir, "temp.wav")
            voice_seg = synth_text_to_wav(token, current_voice_path, tmp_wav)

            if current_music:
                mus = current_music
                if len(mus) < len(voice_seg):
                    loops = (len(voice_seg) // len(mus)) + 1
                    mus = mus * loops
                mus = mus[:len(voice_seg)].fade_in(fade_ms).fade_out(fade_ms)
                voice_seg = mus.overlay(voice_seg)

            final_segments.append(voice_seg)
            final_segments.append(AudioSegment.silent(duration=int(default_pause * 1000)))

    combined = AudioSegment.silent(duration=0)
    for seg in final_segments:
        combined += seg

    out_name = "multi_voice_with_music"
    out_ext = "wav" if DRY_RUN else "mp3"
    out_path = os.path.join(output_dir, f"{out_name}.{out_ext}")
    combined.export(out_path, format=out_ext)
    print(f"\n✅ Multi-voice track{' (DRY_RUN WAV)' if DRY_RUN else ''} saved as '{out_path}'")

def run_single_voice(raw_text: str):
    available_voices = [f for f in os.listdir(voices_dir) if f.lower().endswith(".wav")] if os.path.exists(voices_dir) else []
    selected_voice_path = None

    if available_voices:
        print("\n🎤 Available voices:")
        for i, v in enumerate(available_voices, 1):
            print(f"  {i}. {v}")
        print("  0. All voices")

        try:
            choice = input("\nSelect voice number (or press Enter for default): ").strip()
        except EOFError:
            # Non-interactive (CI): default to first voice if available
            choice = "1" if available_voices else ""

        if choice.isdigit():
            choice_num = int(choice)
            if choice_num == 0:
                for voice in available_voices:
                    name = os.path.splitext(voice)[0]
                    print(f"🎙 Generating for {name}...")
                    tmp_wav = os.path.join(output_dir, f"{name}.wav")
                    seg = synth_text_to_wav(raw_text, os.path.join(voices_dir, voice), tmp_wav)
                    out_ext = "wav" if DRY_RUN else "mp3"
                    seg.export(os.path.join(output_dir, f"{name}.{out_ext}"), format=out_ext)
                print(f"\n✅ All voices complete. Files saved in '{output_dir}'")
                raise SystemExit(0)
            elif 1 <= choice_num <= len(available_voices):
                selected_voice_path = os.path.join(voices_dir, available_voices[choice_num - 1])

    tmp_wav = os.path.join(output_dir, "single.wav")
    seg = synth_text_to_wav(raw_text, selected_voice_path, tmp_wav)
    out_ext = "wav" if DRY_RUN else "mp3"
    seg.export(os.path.join(output_dir, f"output.{out_ext}"), format=out_ext)
    print(f"\n✅ Single voice track saved as '{os.path.join(output_dir, f'output.{out_ext}')}'")

def choose_mode() -> str:
    if MODE_ENV in ("1", "2"):
        return MODE_ENV
    if not sys.stdin.isatty():   # CI / non-interactive
        return "2"
    try:
        print("\nSelect mode:")
        print("1. Single voice (choose at prompt)")
        print("2. Multi-voice script ([voice:], [pause:], [bgmusic:] tags)")
        return input("Choice (1 or 2): ").strip()
    except EOFError:
        return "2"

if __name__ == "__main__":
    mode = choose_mode()
    if mode == "2":
        run_multi_voice(raw_text)
    else:
        run_single_voice(raw_text)
