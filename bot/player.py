from audio_format import pcm_block_size, get_audio_channels, stereo_to_mono
"""CBTC Bot ses oynatma modulu."""

import math
import struct


def generate_test_tone(duration=2, frequency=440, sample_rate=16000):
    """16-bit mono PCM test sesi uretir."""
    samples = int(duration * sample_rate)
    amplitude = 8000

    return b"".join(
        struct.pack(
            "<h",
            int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
        )
        for i in range(samples)
    )


def generate_audio_blocks(duration=180, sample_rate=16000, frequency=440):
    """Kesintisiz 100 ms PCM ses bloklari uretir."""
    samples_per_block = sample_rate // 10
    total_samples = int(duration * sample_rate)
    amplitude = 8000

    for start in range(0, total_samples, samples_per_block):
        count = min(samples_per_block, total_samples - start)
        yield b"".join(
            struct.pack(
                "<h",
                int(amplitude * math.sin(
                    2 * math.pi * frequency * (start + i) / sample_rate
                ))
            )
            for i in range(count)
        )


def send_audio_block(teamtalk, pcm_data, stream_id=1, sample_rate=16000, channels=1):
    """Bir PCM ses blogunu TeamTalk'a gonderir."""
    import ctypes
    import TeamTalk5 as tt

    if len(pcm_data) % 2:
        raise ValueError("PCM verisi 16-bit olmalidir.")

    if channels not in (1, 2):
        raise ValueError("Kanal sayisi 1 veya 2 olmali.")
    if len(pcm_data) % (2 * channels):
        raise ValueError("PCM blok boyutu kanal sayisiyla uyumsuz.")
    sample_count = len(pcm_data) // (2 * channels)
    buffer = ctypes.create_string_buffer(pcm_data)

    block = tt.AudioBlock()
    block.nStreamID = stream_id
    block.nSampleRate = sample_rate
    block.nChannels = channels
    block.lpRawAudio = ctypes.cast(buffer, ctypes.c_void_p)
    block.nSamples = sample_count
    block.uSampleIndex = 0
    block.uStreamTypes = tt.StreamType.STREAMTYPE_VOICE

    return teamtalk.insertAudioBlock(block)

def play_test_audio(teamtalk, duration=180):
    """Test sesini kontrollu sekilde TeamTalk'a gonderir."""
    import time

    blocks = generate_audio_blocks(duration=duration)
    interval = 0.1
    next_send = time.monotonic()

    for pcm_data in blocks:
        deadline = time.monotonic() + 5

        while not send_audio_block(teamtalk, pcm_data):
            if time.monotonic() >= deadline:
                print("Ses kuyrugu zaman asimina ugradi.", flush=True)
                return False

            time.sleep(0.02)

        next_send += interval
        remaining = next_send - time.monotonic()

        if remaining > 0:
            time.sleep(remaining)

    print("Test sesi gonderimi tamamlandi.", flush=True)


def read_pcm_blocks(process, block_size, stop_event=None, startup_timeout=None):
    """PCM verisini durdurma sinyalini bekletmeden 40 ms bloklara ayirir."""
    import os
    import select
    import time

    pending = bytearray()
    startup_deadline = (
        time.monotonic() + startup_timeout if startup_timeout is not None else None
    )
    while True:
        if stop_event is not None and stop_event.is_set():
            return
        if startup_deadline is not None and time.monotonic() >= startup_deadline:
            raise TimeoutError("YouTube ilk sesi zamaninda gelmedi.")
        if os.name == "posix":
            ready, _, _ = select.select([process.stdout], [], [], 0.05)
            if not ready:
                continue
            chunk = os.read(process.stdout.fileno(), 65536)
        else:
            chunk = process.stdout.read(block_size)
        if not chunk:
            if pending:
                yield bytes(pending).ljust(block_size, b"\x00")
            return
        pending.extend(chunk)
        while len(pending) >= block_size:
            if stop_event is not None and stop_event.is_set():
                return
            startup_deadline = None
            yield bytes(pending[:block_size])
            del pending[:block_size]

def play_mp3(teamtalk, filename, volume=100, stop_event=None, source_process=None,
             on_first_audio=None):
    """Yerel dosyayi veya bir ses akisinin stdout'unu TeamTalk kanalinda calar."""
    import subprocess
    import time

    volume = max(0, min(100, int(volume)))
    gain = volume / 100

    command = [
        "ffmpeg", "-nostdin", "-v", "error",
        "-i", "pipe:0" if source_process is not None else str(filename),
        "-vn",
        "-f", "s16le", "-acodec", "pcm_s16le",
        "-ar", "48000", "-ac", "2", "pipe:1"
    ]

    process = subprocess.Popen(
        command,
        stdin=source_process.stdout if source_process is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    if source_process is not None:
        source_process.stdout.close()

    interval = 0.04
    next_send = None

    previous_channels = None
    sent_blocks = 0
    try:
        block_size = pcm_block_size(48000, 2, duration_ms=40)
        for pcm_data in read_pcm_blocks(
            process, block_size, stop_event,
            startup_timeout=25 if source_process is not None else None,
        ):
            if stop_event is not None and stop_event.is_set():
                print("Muzik durdurma sinyali alindi.", flush=True)
                return False

            now = time.monotonic()
            if next_send is None or now - next_send > interval:
                next_send = now

            current_volume = getattr(
                teamtalk, "music_volume", volume
            )
            pcm_data = apply_volume(pcm_data, current_volume)

            deadline = time.monotonic() + 5

            channels = get_audio_channels(teamtalk)
            if previous_channels is not None and channels != previous_channels:
                teamtalk.insertAudioBlock(None)
                print("Kanal ses bicimi degisti. Ses akisi sifirlandi.", flush=True)
            previous_channels = channels
            output_data = (
                pcm_data if channels == 2
                else stereo_to_mono(pcm_data)
            )

            while True:
                if stop_event is not None and stop_event.is_set():
                    print("Muzik durdurma sinyali alindi.", flush=True)
                    return False
                if send_audio_block(
                    teamtalk,
                    output_data,
                    sample_rate=48000,
                    channels=channels
                ):
                    break
                if time.monotonic() >= deadline:
                    print(
                        "Ses gonderimi zaman asimi:",
                        "kanal=", channels,
                        "ornekleme=", 48000,
                        "bayt=", len(output_data),
                        "blok_suresi_ms=", len(output_data) * 1000 // (48000 * channels * 2),
                        flush=True
                    )
                    return False
                time.sleep(0.02)

            sent_blocks += 1
            if sent_blocks == 1 and on_first_audio is not None:
                try:
                    on_first_audio()
                except Exception as exc:
                    print(f"Ilk ses bildirimi hatasi: {exc}", flush=True)

            next_send += interval
            remaining = next_send - time.monotonic()

            if remaining > 0:
                if stop_event is not None:
                    stop_event.wait(remaining)
                else:
                    time.sleep(remaining)

        if stop_event is not None and stop_event.is_set():
            print("Muzik durdurma sinyali alindi.", flush=True)
            return False

        process.wait()
        source_ok = True
        if source_process is not None:
            source_ok = source_process.wait(timeout=5) == 0
        if not sent_blocks or process.returncode != 0 or not source_ok:
            print("Ses akisi tamamlanamadi.", flush=True)
            return False
        print("Ses oynatma tamamlandi.", flush=True)
        return True
    finally:
        try:
            teamtalk.insertAudioBlock(None)
            print("Mikrofon ses aktarimi kapatildi.", flush=True)
        except Exception as e:
            print("Ses aktarimi kapatma hatasi:", e, flush=True)

        process.stdout.close()
        if process.poll() is None:
            process.terminate()
        process.wait()
        if source_process is not None:
            if source_process.poll() is None:
                source_process.terminate()
            try:
                source_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                source_process.kill()
                source_process.wait()


def apply_volume(pcm_data, volume):
    """16-bit PCM ses verisine ses seviyesi uygular."""
    from array import array
    import sys

    volume = max(0, min(100, int(volume)))
    samples = array("h")
    samples.frombytes(pcm_data)

    if sys.byteorder != "little":
        samples.byteswap()

    gain = (volume / 100.0) ** 2

    for i in range(len(samples)):
        value = round(samples[i] * gain)
        samples[i] = max(-32768, min(32767, value))

    if sys.byteorder != "little":
        samples.byteswap()

    return samples.tobytes()
