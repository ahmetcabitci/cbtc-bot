"""GitHub'ın resmi yt-dlp sürümünü sessizce ve atomik olarak güncelle."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parent.parent
YOUTUBE_DIR = PROJECT_DIR / "youtube"
RELEASE_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
UPDATE_INTERVAL_SECONDS = 24 * 60 * 60
MAX_BINARY_BYTES = 20 * 1024 * 1024


def ytdlp_binary():
    return YOUTUBE_DIR / "yt-dlp"


def ytdlp_python():
    venv_python = PROJECT_DIR / ".venv-youtube" / "bin" / "python"
    return str(venv_python) if venv_python.exists() else sys.executable


def ytdlp_command():
    """Önce açık kullanıcı tercihini, sonra GitHub sürümünü kullan."""
    override = os.environ.get("CBTC_YTDLP_PYTHON")
    if override:
        return [override, "-m", "yt_dlp"]
    binary = ytdlp_binary()
    if binary.is_file():
        return [ytdlp_python(), str(binary)]
    return [ytdlp_python(), "-m", "yt_dlp"]


def _read_url(url, limit):
    request = Request(url, headers={"User-Agent": "CBTCBot-yt-dlp-updater", "Accept": "application/vnd.github+json"})
    with urlopen(request, timeout=20) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("GitHub yanıtı beklenenden büyük")
    return data


def update_once():
    """Yeni kararlı sürüm varsa indir, doğrula, sonra tek adımda değiştir."""
    release = json.loads(_read_url(RELEASE_API, 1024 * 1024))
    version = release["tag_name"]
    asset = next(asset for asset in release["assets"] if asset["name"] == "yt-dlp")
    digest = asset.get("digest") or ""
    if not digest.startswith("sha256:"):
        raise ValueError("GitHub sürümünün SHA-256 özeti bulunamadı")
    expected_hash = digest.removeprefix("sha256:")
    if len(expected_hash) != 64:
        raise ValueError("GitHub sürümünün SHA-256 özeti geçersiz")

    binary = ytdlp_binary()
    if binary.is_file():
        current = subprocess.run(
            [ytdlp_python(), str(binary), "--version"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if current.returncode == 0 and current.stdout.strip() == version:
            return False

    url = asset["browser_download_url"]
    if not url.startswith("https://github.com/yt-dlp/yt-dlp/releases/download/"):
        raise ValueError("Beklenmeyen GitHub dosya adresi")
    YOUTUBE_DIR.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=".yt-dlp-", dir=YOUTUBE_DIR)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(_read_url(url, MAX_BINARY_BYTES))
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected_hash:
            raise ValueError("yt-dlp SHA-256 doğrulaması başarısız")
        verified = subprocess.run(
            [ytdlp_python(), str(temporary), "--version"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if verified.returncode != 0 or verified.stdout.strip() != version:
            raise ValueError("İndirilen yt-dlp sürümü çalışmıyor")
        os.replace(temporary, binary)
        return True
    finally:
        temporary.unlink(missing_ok=True)


def start_auto_update():
    """Botu ve TeamTalk mesajlarını bekletmeden günlük kontrol başlat."""
    def run():
        while True:
            try:
                if update_once():
                    print("yt-dlp GitHub sürümü güncellendi.", flush=True)
            except Exception as exc:
                print(f"yt-dlp güncelleme kontrolü başarısız: {exc}", flush=True)
            threading.Event().wait(UPDATE_INTERVAL_SECONDS)

    threading.Thread(target=run, name="ytdlp-update", daemon=True).start()
