
#alert.py
"""
High-risk alarm sound.

    play_alert_sound_async()   start the alarm (no-op if already sounding)
    stop_alert_sound()         silence it
    is_alarm_playing()         True while it is sounding

The alarm is a CONTINUOUS loop -- an evacuation-style rising siren
("whoop-whoop-whoop") alternating with a fast two-tone klaxon -- and
keeps going until stop_alert_sound() is called, i.e. until the operator
dismisses the banner or the well drops back below the threshold.

The sound is synthesised once into assets/alarm.wav so it is identical
on every machine. Drop your own alarm.wav into assets/ to override it.

Playback:
    Windows      winsound (looped, asynchronous, no extra packages)
    macOS        afplay, looped from a background thread
    Linux        paplay / aplay / ffplay, looped from a background thread
    fallback     winsound.Beep siren (Windows) or the terminal bell
"""

import os
import sys
import math
import wave
import struct
import shutil
import threading
import subprocess

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

try:
    from config import ALARM_MAX_SECONDS
except ImportError:
    ALARM_MAX_SECONDS = 0          # 0 = sound until dismissed


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
WAV_PATH = os.path.join(ASSETS_DIR, "alarm.wav")

SAMPLE_RATE = 44100

_lock = threading.Lock()
_stop_event = threading.Event()
_player_thread = None
_player_process = None
_playing = False
_timeout_timer = None


# ----------------------------------------------------------------
# Sound synthesis
# ----------------------------------------------------------------
def _harsh_wave(phase):
    """Square wave with a little sine mixed in: piercing but not a pure
    buzz, the character of a real fire-alarm sounder."""
    s = math.sin(phase)
    return 0.9 * (1.0 if s >= 0 else -1.0) + 0.9 * s


def _sweep(samples, f_start, f_end, seconds):
    """Exponential frequency sweep (siren 'whoop')."""
    n = int(SAMPLE_RATE * seconds)
    phase = 0.0
    ratio = f_end / f_start
    for i in range(n):
        t = i / n
        freq = f_start * (ratio ** t)
        phase += 2 * math.pi * freq / SAMPLE_RATE
        # short fade in/out so the loop never clicks
        env = min(1.0, i / 300, (n - i) / 200)
        samples.append(_harsh_wave(phase) * env)


def _tone(samples, freq, seconds):
    n = int(SAMPLE_RATE * seconds)
    for i in range(n):
        phase = 2 * math.pi * freq * i / SAMPLE_RATE
        env = min(1.0, i / 200, (n - i) / 100)
        samples.append(_harsh_wave(phase) * env)


def _build_alarm_wav(path):
    """Writes one ~3 s cycle designed to be looped seamlessly."""

    samples = []

    # Section 1: three rising "whoops" (evacuation siren)
    for _ in range(3):
        _sweep(samples, 220, 9350, 0.55)

    # Section 2: fast hi-lo klaxon
    for _ in range(5):
        _tone(samples, 8250, 0.13)
        _tone(samples, 750, 0.13)

    peak = max(abs(s) for s in samples) or 1.0
    scale = 0.9 * 32767 / peak

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(b"".join(
            struct.pack("<h", int(s * scale)) for s in samples
        ))


def _ensure_wav():
    """Returns the WAV path, building the file on first use."""
    if not os.path.isfile(WAV_PATH):
        try:
            _build_alarm_wav(WAV_PATH)
        except Exception as error:
            print(f"alerts: could not build alarm wav: {error}")
            return None
    return WAV_PATH


# ----------------------------------------------------------------
# Playback backends
# ----------------------------------------------------------------
def _find_cli_player():
    if sys.platform == "darwin" and shutil.which("afplay"):
        return ["afplay"]
    for candidate in (["paplay"], ["aplay", "-q"],
                      ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]):
        if shutil.which(candidate[0]):
            return candidate
    return None


def _cli_loop(player, path):
    """Background thread: replays the WAV until told to stop."""
    global _player_process

    while not _stop_event.is_set():
        try:
            _player_process = subprocess.Popen(player + [path])
            while _player_process.poll() is None:
                if _stop_event.wait(0.1):
                    _player_process.terminate()
                    break
        except Exception as error:
            print(f"alerts: playback failed: {error}")
            break

    _player_process = None


def _beep_loop():
    """Last-resort siren using winsound.Beep (or the terminal bell)."""
    while not _stop_event.is_set():
        if WINSOUND_AVAILABLE:
            for freq in list(range(500, 1400, 100)) + list(range(1400, 500, -100)):
                if _stop_event.is_set():
                    return
                winsound.Beep(freq, 45)
            for _ in range(4):
                if _stop_event.is_set():
                    return
                winsound.Beep(1250, 120)
                winsound.Beep(850, 120)
        else:
            sys.stdout.write("\a")
            sys.stdout.flush()
            if _stop_event.wait(0.5):
                return


# ----------------------------------------------------------------
# Public API
# ----------------------------------------------------------------
def is_alarm_playing():
    return _playing


def play_alert_sound_async():
    """Starts the continuous alarm. Safe to call repeatedly."""
    global _player_thread, _playing, _timeout_timer

    with _lock:
        if _playing:
            return
        _playing = True
        _stop_event.clear()

        path = _ensure_wav()

        if path and WINSOUND_AVAILABLE:
            # Looped + async: Windows keeps it going with no thread of ours.
            try:
                winsound.PlaySound(
                    path,
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP,
                )
            except RuntimeError as error:
                print(f"alerts: winsound failed ({error}), using beep siren")
                _player_thread = threading.Thread(target=_beep_loop, daemon=True)
                _player_thread.start()

        else:
            player = _find_cli_player() if path else None
            target = (lambda: _cli_loop(player, path)) if player else _beep_loop
            _player_thread = threading.Thread(target=target, daemon=True)
            _player_thread.start()

        if ALARM_MAX_SECONDS and ALARM_MAX_SECONDS > 0:
            _timeout_timer = threading.Timer(ALARM_MAX_SECONDS, stop_alert_sound)
            _timeout_timer.daemon = True
            _timeout_timer.start()


def stop_alert_sound():
    """Silences the alarm immediately. Safe to call when nothing is playing."""
    global _playing, _player_thread, _timeout_timer

    with _lock:
        if not _playing:
            return
        _playing = False
        _stop_event.set()

        if _timeout_timer is not None:
            _timeout_timer.cancel()
            _timeout_timer = None

        if WINSOUND_AVAILABLE:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except RuntimeError:
                pass

        process = _player_process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except Exception:
                pass

        _player_thread = None


if __name__ == "__main__":
    # Quick manual test: sounds the alarm for 8 seconds.
    import time
    print("Sounding alarm for 8 seconds...")
    play_alert_sound_async()
    time.sleep(8)
    stop_alert_sound()
    print("Stopped.")