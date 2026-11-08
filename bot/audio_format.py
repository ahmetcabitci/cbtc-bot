"""CBTC Bot ses biçimi yardımcıları."""

def pcm_block_size(sample_rate, channels, duration_ms=100):
    """16-bit PCM için blok boyutunu bayt cinsinden hesaplar."""
    if sample_rate <= 0:
        raise ValueError("Ornekleme hizi pozitif olmali.")
    if channels not in (1, 2):
        raise ValueError("Kanal sayisi 1 veya 2 olmali.")
    if duration_ms <= 0:
        raise ValueError("Blok suresi pozitif olmali.")

    samples = sample_rate * duration_ms // 1000
    return samples * channels * 2


def get_audio_channels(teamtalk):
    """Botun bulundugu kanalin ses kanali sayisini getirir."""
    channels = getattr(teamtalk, "channel_audio_channels", 1)
    return channels if channels in (1, 2) else 1


def stereo_to_mono(pcm_data):
    """16-bit stereo PCM verisini mono PCM verisine donusturur."""
    import array

    if len(pcm_data) % 4:
        raise ValueError("Stereo PCM verisi eksik veya hatali.")

    stereo = array.array("h")
    stereo.frombytes(pcm_data)

    mono = array.array("h", (
        (stereo[i] + stereo[i + 1]) // 2
        for i in range(0, len(stereo), 2)
    ))

    return mono.tobytes()
