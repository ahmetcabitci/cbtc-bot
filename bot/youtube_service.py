"""YouTube aramasi ve ses dosyasini oynaticiya hazirlama."""

import json
import subprocess
import tempfile
import time
from pathlib import Path

from ytdlp_update import ytdlp_command

PROJECT_DIR = Path(__file__).resolve().parent.parent
YOUTUBE_DIR = PROJECT_DIR / "youtube"


class YouTubeError(Exception):
    pass


def search_first(query):
    """YouTube.js ile en fazla 10 sonuc ara, ilk videoyu dondur."""
    query = query.strip()
    if not query:
        raise YouTubeError("Sarki adi bos olamaz.")
    started = time.monotonic()
    try:
        result = subprocess.run(
            ["node", str(YOUTUBE_DIR / "search-first.mjs"), query],
            cwd=YOUTUBE_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise YouTubeError(f"YouTube aramasi baslatilamadi: {exc}") from exc
    if result.returncode:
        raise YouTubeError((result.stderr or result.stdout).strip()[-500:])
    print(f"YouTube arama süresi: {time.monotonic() - started:.2f} saniye", flush=True)
    for line in reversed(result.stdout.splitlines()):
        if line.startswith("CBTC_RESULT="):
            return json.loads(line.removeprefix("CBTC_RESULT="))
    raise YouTubeError("YouTube aramasi sonuc vermedi.")


def download_audio(video_id, target_dir, cancel_event=None):
    """yt-dlp ile ilk videonun sesini gecici dizine indir."""
    if len(video_id) != 11 or not all(c.isalnum() or c in "-_" for c in video_id):
        raise YouTubeError("Gecersiz YouTube video kimligi.")
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(
            [*ytdlp_command(), "--js-runtimes", "node",
             "--no-playlist", "--max-filesize", "100M",
             "-f", "bestaudio", "-o", str(Path(target_dir) / "%(id)s.%(ext)s"),
             f"https://www.youtube.com/watch?v={video_id}"],
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + 180
        while process.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise YouTubeError("İndirme iptal edildi.")
            if time.monotonic() >= deadline:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise YouTubeError("İndirme zaman aşımına uğradı.")
            time.sleep(0.05)
        if process.returncode:
            output.seek(0)
            raise YouTubeError(output.read().decode("utf-8", errors="replace").strip()[-700:])
    files = [p for p in Path(target_dir).iterdir() if p.is_file() and p.name.startswith(video_id)]
    if not files:
        raise YouTubeError("Ses dosyasi indirilemedi.")
    return files[0]


def start_audio_stream(video_id, error_file):
    """yt-dlp ses verisini dosya beklemeden stdout'a aktarir."""
    if len(video_id) != 11 or not all(c.isalnum() or c in "-_" for c in video_id):
        raise YouTubeError("Gecersiz YouTube video kimligi.")
    return subprocess.Popen(
        [*ytdlp_command(), "--js-runtimes", "node",
         "--no-playlist", "--no-progress", "-f", "bestaudio", "-o", "-",
         f"https://www.youtube.com/watch?v={video_id}"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=error_file,
    )




def temporary_audio_dir():
    return tempfile.TemporaryDirectory(prefix="cbtc-youtube-")
