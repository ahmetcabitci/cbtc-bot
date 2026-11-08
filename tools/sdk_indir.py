"""BearWare'ın uygun TeamTalk SDK paketinden botun iki SDK dosyasını kur.

Kullanım: python3 tools/sdk_indir.py [--force] [--archive-url RESMI_BEARWARE_ADRESI]
"""

import argparse
import ast
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parent.parent
SDK_DIR = PROJECT_DIR / "sdk"
DOWNLOAD_PAGE = "https://bearware.dk/?page_id=419"
MAX_ARCHIVE_BYTES = 600 * 1024 * 1024


class SDKError(RuntimeError):
    pass


class DownloadTable(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.link = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = {"text": [], "links": []}
        elif tag == "a" and self.row is not None:
            self.link = dict(attrs).get("href")
            if self.link:
                self.row["links"].append(self.link)

    def handle_endtag(self, tag):
        if tag == "a":
            self.link = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.row is not None:
            self.row["text"].append(data)


def ubuntu_version():
    if platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        raise SDKError("Şimdilik yalnızca Linux x86_64 destekleniyor.")
    values = {}
    for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')
    if values.get("ID") != "ubuntu":
        raise SDKError("Şimdilik yalnızca Ubuntu destekleniyor.")
    return values.get("VERSION_ID", "").split(".", 1)[0]


def official_archive_url(url):
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname not in ("bearware.dk", "www.bearware.dk")
            or not re.fullmatch(r"/teamtalksdk/v[0-9.]+[a-z]?/tt5sdk_v[0-9.]+[a-z]?_ubuntu[0-9]+_x86_64\.7z", parsed.path)
            or parsed.query or parsed.fragment):
        raise SDKError("SDK adresi resmi BearWare Linux Standard SDK paketi olmalı.")
    return url


def select_archive(page_html, ubuntu_major):
    table = DownloadTable()
    table.feed(page_html)
    for row in table.rows:
        label = " ".join(" ".join(row["text"]).split())
        if ("TeamTalk 5 SDK Standard Edition" in label
                and f"Ubuntu {ubuntu_major}" in label
                and "x86_64" in label):
            for link in row["links"]:
                candidate = urljoin(DOWNLOAD_PAGE, link)
                try:
                    return official_archive_url(candidate)
                except SDKError:
                    continue
    raise SDKError(
        f"BearWare güncel SDK sayfasında Ubuntu {ubuntu_major} x86_64 paketi yok. "
        "Uyumlu resmi SDK arşivini --archive-url ile verebilirsiniz."
    )


def download(url, destination):
    request = Request(url, headers={"User-Agent": "CBTCBot-SDK-Installer"})
    total = 0
    with urlopen(request, timeout=30) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_ARCHIVE_BYTES:
                raise SDKError("SDK arşivi beklenenden büyük.")
            output.write(chunk)
    if total == 0:
        raise SDKError("Boş SDK arşivi indirildi.")


def sdk_files(folder):
    wrapper = folder / "TeamTalk5.py"
    library = folder / "libTeamTalk5.so"
    return wrapper, library


def verify_sdk(folder):
    wrapper, library = sdk_files(folder)
    if not wrapper.is_file() or not library.is_file():
        raise SDKError("TeamTalk5.py veya libTeamTalk5.so bulunamadı.")
    ast.parse(wrapper.read_text(encoding="utf-8"))
    if library.read_bytes()[:4] != b"\x7fELF":
        raise SDKError("libTeamTalk5.so geçerli bir Linux kütüphanesi değil.")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(folder) + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    result = subprocess.run(
        [sys.executable, "-c", "import TeamTalk5; print(TeamTalk5.dll.TT_GetVersion())"],
        cwd=folder, env=env, capture_output=True, text=True, timeout=20,
    )
    if result.returncode:
        raise SDKError("SDK yüklenemedi: " + result.stderr.strip()[-600:])
    return result.stdout.strip()


def install(archive_url, force=False):
    if SDK_DIR.exists() and not force:
        try:
            version = verify_sdk(SDK_DIR)
            print(f"SDK zaten hazır ({version}). Yeniden kurmak için --force kullanın.")
            return
        except (SDKError, OSError, SyntaxError):
            pass

    extractor = shutil.which("7z") or shutil.which("7zz")
    if not extractor:
        raise SDKError("7z bulunamadı. Ubuntu'da önce 'sudo apt install p7zip-full' çalıştırın.")

    with tempfile.TemporaryDirectory(prefix="cbtc-sdk-", dir=PROJECT_DIR) as temporary:
        work = Path(temporary)
        archive = work / "teamtalk-sdk.7z"
        extracted = work / "extracted"
        staged = work / "sdk"
        extracted.mkdir()
        staged.mkdir()
        print("TeamTalk SDK resmi BearWare adresinden indiriliyor...")
        download(official_archive_url(archive_url), archive)
        result = subprocess.run(
            [extractor, "x", "-y", f"-o{extracted}", str(archive)],
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode:
            raise SDKError("SDK arşivi açılamadı: " + result.stderr.strip()[-500:])
        wrappers = list(extracted.rglob("TeamTalk5.py"))
        libraries = list(extracted.rglob("libTeamTalk5.so"))
        if not wrappers or not libraries:
            raise SDKError("Arşivde gerekli Python SDK dosyaları yok.")
        wrapper = next((p for p in wrappers if "TeamTalkPy" in p.parts), wrappers[0])
        library = next((p for p in libraries if "TeamTalk_DLL" in p.parts), libraries[0])
        shutil.copy2(wrapper, staged / "TeamTalk5.py")
        shutil.copy2(library, staged / "libTeamTalk5.so")
        version = verify_sdk(staged)

        backup = PROJECT_DIR / "sdk.onceki"
        if backup.exists():
            raise SDKError("sdk.onceki yedeği zaten var; önce bu klasörü inceleyin.")
        if SDK_DIR.exists():
            SDK_DIR.rename(backup)
        try:
            staged.rename(SDK_DIR)
        except OSError:
            if backup.exists():
                backup.rename(SDK_DIR)
            raise
        print(f"TeamTalk SDK kuruldu ({version}).")
        if backup.exists():
            print("Önceki SDK sdk.onceki klasöründe saklandı.")


def main():
    parser = argparse.ArgumentParser(description="CBTC Bot TeamTalk SDK indiricisi")
    parser.add_argument("--force", action="store_true", help="Var olan SDK'yı yeniden kur")
    parser.add_argument("--archive-url", help="Uyumlu resmi BearWare SDK arşiv adresi")
    args = parser.parse_args()
    try:
        major = ubuntu_version()
        if SDK_DIR.exists() and not args.force:
            try:
                print(f"SDK zaten hazır ({verify_sdk(SDK_DIR)}).")
                return 0
            except (SDKError, OSError, SyntaxError):
                pass
        if args.archive_url:
            url = official_archive_url(args.archive_url)
            if f"_ubuntu{major}_" not in url:
                raise SDKError(f"Bu arşiv Ubuntu {major} için değil.")
        else:
            request = Request(DOWNLOAD_PAGE, headers={"User-Agent": "CBTCBot-SDK-Installer"})
            with urlopen(request, timeout=20) as response:
                html = response.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
            url = select_archive(html, major)
        install(url, force=args.force)
        return 0
    except (SDKError, OSError, SyntaxError, subprocess.TimeoutExpired) as exc:
        print(f"SDK kurulamadı: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
