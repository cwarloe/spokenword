
from TTS.api import TTS
from pydub import AudioSegment
import os, re

# Config
text_file = "text.txt"
voices_dir = "voices"
music_dir = "music"
output_dir = "outputs"
default_pause = 0.5  # default pause in seconds
music_volume_db = -12  # background music gain (negative = quieter)
fade_ms = 600  # music fade in/out

# Read text
if not os.path.exists(text_file):
    print("❌ Missing text.txt.")
    raise SystemExit(1)

with open(text_file, "r", encoding="utf-8") as f:
    raw_text = f.read().strip()
if not raw_text:
    print("❌ No text in text.txt.")
    raise SystemExit(1)

# Prepare output folder
os.makedirs(output_dir, exist_ok=True)

# Load model
print("\n🔄 Loading XTTS v2 model...")
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False)

# Ask for mode
print("\nSelect mode:")
print("1. Single voice (choose at prompt)")
print("2. Multi-voice script ([voice:], [pause:], [bgmusic:] tags)")
mode = input("Choice (1 or 2): ").strip()

final_segments = []
current_music = None

if mode == "2":
    token_pattern = r"(\[voice:.*?\]|\[pause:.*?\]|\[bgmusic:.*?\])"
    tokens = re.split(token_pattern, raw_text, flags=re.I)

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
            # Spoken text
            print(f"💬 Speaking: {token[:60]}...")
            tmp_wav = os.path.join(output_dir, "temp.wav")
            if current_voice_path:
                tts.tts_to_file(text=token, speaker_wav=current_voice_path, language="en", file_path=tmp_wav)
            else:
                tts.tts_to_file(text=token, file_path=tmp_wav)

            voice_seg = AudioSegment.from_wav(tmp_wav)

            # Overlay music if active
            if current_music:
                mus = current_music
                if len(mus) < len(voice_seg):
                    loops = (len(voice_seg) // len(mus)) + 1
                    mus = mus * loops
                mus = mus[:len(voice_seg)].fade_in(fade_ms).fade_out(fade_ms)
                voice_seg = mus.overlay(voice_seg)

            final_segments.append(voice_seg)
            final_segments.append(AudioSegment.silent(duration=int(default_pause * 1000)))

    # Combine and export
    combined = AudioSegment.silent(duration=0)
    for seg in final_segments:
        combined += seg

    out = os.path.join(output_dir, "multi_voice_with_music.mp3")
    combined.export(out, format="mp3")
    print(f"\n✅ Multi-voice track with music saved as '{out}'")

else:
    # Single voice mode
    available_voices = [f for f in os.listdir(voices_dir) if f.lower().endswith(".wav")] if os.path.exists(voices_dir) else []
    selected_voice_path = None

    if available_voices:
        print("\n🎤 Available voices:")
        for i, v in enumerate(available_voices, 1):
            print(f"  {i}. {v}")
        print("  0. All voices")

        choice = input("\nSelect voice number (or press Enter for default): ").strip()

        if choice.isdigit():
            choice_num = int(choice)
            if choice_num == 0:
                for voice in available_voices:
                    name = os.path.splitext(voice)[0]
                    print(f"🎙 Generating for {name}...")
                    tmp_wav = os.path.join(output_dir, f"{name}.wav")
                    tts.tts_to_file(text=raw_text, speaker_wav=os.path.join(voices_dir, voice), language="en", file_path=tmp_wav)
                    AudioSegment.from_wav(tmp_wav).export(os.path.join(output_dir, f"{name}.mp3"), format="mp3")
                print(f"\n✅ All voices complete. MP3s saved in '{output_dir}'")
                raise SystemExit(0)
            elif 1 <= choice_num <= len(available_voices):
                selected_voice_path = os.path.join(voices_dir, available_voices[choice_num - 1])

    if selected_voice_path:
        tmp_wav = os.path.join(output_dir, "single.wav")
        tts.tts_to_file(text=raw_text, speaker_wav=selected_voice_path, language="en", file_path=tmp_wav)
    else:
        tmp_wav = os.path.join(output_dir, "default.wav")
        tts.tts_to_file(text=raw_text, file_path=tmp_wav)

    AudioSegment.from_wav(tmp_wav).export(os.path.join(output_dir, "output.mp3"), format="mp3")
    print(f"\n✅ Single voice track saved as '{os.path.join(output_dir, 'output.mp3')}'")
