"""CBTC Bot özel mesaj komutları."""

try:
    from .audio import AudioController
except ImportError:
    from audio import AudioController


audio = AudioController()
BOT_VERSION = "0.1.0 (geliştirme)"

HELP_TEXT = f"""CBTC Bot | Yardım
Geliştirici: Ahmet Çabıtçı
Sürüm: {BOT_VERSION}
GitHub: yakında
o sanatçı şarkı - YouTube'da ara ve çal
d - Durdur | i - İleri | g - Geri
s - Ses düzeyi | s 20 - Sesi ayarla
k - Kilit aç/kapat (yönetici)
yb - Botu yeniden başlat (yönetici)
ad Yeni İsim - Adı hazırla; kaydet ile sakla (yönetici)
durum Yeni mesaj - Durumu değiştir (yönetici)
kaydet - Ayarları kaydet (yönetici)
y - Yardım"""


def handle_command(message):
    """Komutu yorumlar ve uygun yanıtı döndürür."""
    command = message.strip().lower()

    if command == "s":
        return f"Ses düzeyi: {audio.get_volume()}/{audio.max_volume}"

    if command.startswith("s "):
        try:
            value = int(command.split()[1])
            audio.set_volume(value)
            return f"Ses düzeyi {value}/{audio.max_volume} olarak ayarlandı."
        except (ValueError, IndexError):
            return f"0 ile {audio.max_volume} arasında bir değer girin."

    if command == "y":
        return HELP_TEXT

    return None
