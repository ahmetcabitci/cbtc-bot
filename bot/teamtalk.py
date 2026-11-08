import json
import os
import sys
import tempfile
import time
import threading
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SDK_DIR = PROJECT_DIR / "sdk"
sys.path.insert(0, str(SDK_DIR))

import TeamTalk5 as tt


class CBTCTeamTalk(tt.TeamTalk):
    IDLE_STATUS = "CBTC Bot hazır | Şarkı istemek için: o sanatçı şarkı"

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.bot_nickname = config.get("nickname", "CBTC Bot")
        self.desired_nickname = self.bot_nickname
        self.idle_status = config.get("status_message", self.IDLE_STATUS)
        self.nickname_change_allowed = False
        self.pending_nickname = None
        self.music_volume = 15
        self.music_thread = None
        self.music_request_id = 0
        self.current_track = None
        self.playlist = []
        self.current_index = None
        self.track_stop_event = None
        self.navigation_delta = 0
        self.navigation_pending = False
        self.navigation_lock = threading.Lock()
        self.bot_locked = False
        self.restart_requested = False
        self.channel_audio_channels = 1
        self.max_volume = 100
        self.logged_in = False
        self.joined = False

    def onConnectSuccess(self):
        print("Sunucuya baglanildi.", flush=True)
        self.doLogin(
            self.bot_nickname.encode("utf-8"),
            self.config["username"].encode("utf-8"),
            self.config["password"].encode("utf-8"),
            b"CBTC Bot"
        )

    def onCmdMyselfLoggedIn(self, userid, useraccount):
        self.logged_in = True
        nickname_locked = bool(useraccount.uUserRights & tt.UserRight.USERRIGHT_LOCKED_NICKNAME)
        self.nickname_change_allowed = not nickname_locked
        print(
            f"Bot hesap türü: {useraccount.uUserType}; "
            f"SDK anlık ad değiştirme engeli: {'etkin' if nickname_locked else 'yok'}",
            flush=True,
        )
        self.update_music_status()
        print(f"{self.config['username']} kullanicisi basariyla giris yapti.", flush=True)
        self.doJoinChannelByID(
            1,
            self.config["channel_password"].encode("utf-8")
        )


    def onCmdUserTextMessage(self, textmessage):
        if textmessage.nMsgType != tt.TextMsgType.MSGTYPE_USER:
            return

        message = textmessage.szMessage.decode("utf-8").strip()
        command = message.casefold()

        if command == "yb":
            if not self.is_admin(textmessage.nFromUserID):
                self.send_private_message(textmessage.nFromUserID, "Bu komutu yalnızca yöneticiler kullanabilir.")
                return
            self.send_private_message(textmessage.nFromUserID, "Bot yeniden başlatılıyor.")
            self.restart_requested = True
            return

        if command in ("ad", "durum", "kaydet") or command.startswith(("ad ", "durum ")):
            if not self.is_admin(textmessage.nFromUserID):
                self.send_private_message(textmessage.nFromUserID, "Bu komutu yalnızca yöneticiler kullanabilir.")
                return
            if command.startswith("ad "):
                new_name = message[3:].strip()
                if len(new_name.encode("utf-8")) > 100:
                    reply = "Bot adı en fazla 100 bayt olabilir."
                else:
                    self.desired_nickname = new_name
                    if not self.nickname_change_allowed:
                        reply = f"Yeni bot adı hazır: {new_name}. Sunucu canlı ad değişimini engelliyor; bot bağlı kalacak. Kalıcı kayıt için kaydet gönderin."
                    else:
                        command_id = self.doChangeNickname(new_name.encode("utf-8"))
                        if command_id <= 0:
                            reply = f"Yeni bot adı hazır: {new_name}. Canlı değişiklik gönderilemedi; kalıcı kayıt için kaydet gönderin."
                        else:
                            self.pending_nickname = (command_id, new_name, textmessage.nFromUserID)
                            reply = f"Canlı ad değişikliği sunucuya gönderildi: {new_name}. Kalıcı kayıt için kaydet gönderin."
            elif command.startswith("durum "):
                new_status = message[6:].strip()
                if len(new_status.encode("utf-8")) > 400:
                    reply = "Durum mesajı en fazla 400 bayt olabilir."
                else:
                    self.idle_status = new_status
                    if self.current_track is None:
                        self.update_music_status()
                    reply = "Boşta durum mesajı değiştirildi; müzik çalarken şarkı adı görünür."
            elif command == "kaydet":
                try:
                    self.save_bot_settings()
                    reply = "Bot ayarları kaydedildi."
                except OSError as exc:
                    print(f"Bot ayarları kaydedilemedi: {exc}", flush=True)
                    reply = "Bot ayarları kaydedilemedi; sunucu dosya izinlerini kontrol edin."
            else:
                reply = "Kullanım: ad Yeni İsim veya durum Yeni mesaj"
            self.send_private_message(textmessage.nFromUserID, reply)
            return

        if command == "k":
            if not self.is_admin(textmessage.nFromUserID):
                self.send_private_message(textmessage.nFromUserID, "Bu komutu yalnızca yöneticiler kullanabilir.")
                return
            self.bot_locked = not self.bot_locked
            reply = "Bot kilitlendi." if self.bot_locked else "Botun kilidi açıldı."
            self.send_private_message(textmessage.nFromUserID, reply)
            return

        if self.bot_locked and (command.startswith("o ") or command in ("o", "d", "i", "ileri", "g", "geri")
                                or command.startswith("s ")):
            self.send_private_message(textmessage.nFromUserID, "Bot kilitli. Yalnızca yönetici kilidi açabilir.")
            return

        if message[:2].casefold() == "o ":
            query = message[2:].strip()
            if not query:
                self.send_private_message(textmessage.nFromUserID, "Şarkı adı yazın: o sanatçı şarkı")
                return
            self.send_private_message(textmessage.nFromUserID, f"YouTube'da aranıyor: {query}")
            previous_stop = getattr(self, "music_stop_event", None)
            if previous_stop is not None:
                previous_stop.set()
            if self.track_stop_event is not None:
                self.track_stop_event.set()
            previous_thread = self.music_thread
            with self.navigation_lock:
                self.music_request_id += 1
                request_id = self.music_request_id
                self.playlist = []
                self.current_index = None
                self.track_stop_event = None
                self.navigation_pending = False
                self.navigation_delta = 0
                self.current_track = None
            self.update_music_status(request_id=request_id)
            self.music_stop_event = threading.Event()
            self.music_thread = threading.Thread(
                target=self.play_youtube_request,
                args=(query, textmessage.nFromUserID, self.music_stop_event,
                      previous_thread, request_id),
                daemon=True,
            )
            self.music_thread.start()
            return

        if message.casefold() == "d":
            event = getattr(self, "music_stop_event", None)
            if event is not None and not event.is_set():
                event.set()
                if self.track_stop_event is not None:
                    self.track_stop_event.set()
                self.insertAudioBlock(None)
                self.current_track = None
                self.update_music_status()
                reply = "Müzik durduruluyor."
            else:
                reply = "Şu anda çalan müzik yok."

            self.send_private_message(textmessage.nFromUserID, reply)
            return

        if message.casefold() in ("i", "ileri", "g", "geri"):
            direction = 1 if message.casefold() in ("i", "ileri") else -1
            reply = self.request_navigation(direction)
            self.send_private_message(textmessage.nFromUserID, reply)
            return

        from commands import handle_command

        reply = handle_command(message)
        if reply is None:
            return

        from commands import audio
        self.music_volume = audio.get_volume()

        self.send_private_message(textmessage.nFromUserID, reply)

    def request_navigation(self, direction):
        with self.navigation_lock:
            if (self.music_thread is None or not self.music_thread.is_alive()
                    or not self.playlist or self.current_index is None
                    or self.track_stop_event is None):
                return "Şu anda geçilecek bir parça yok."
            if self.navigation_pending:
                return "Parça geçişi sürüyor."
            target = self.current_index + direction
            if target < 0:
                return "Önceki parça yok."
            if target >= len(self.playlist):
                return "Sıradaki parça yok."
            self.navigation_pending = True
            self.navigation_delta = direction
            self.track_stop_event.set()
        self.insertAudioBlock(None)
        self.current_track = None
        self.update_music_status()
        return "Sonraki parçaya geçiliyor." if direction > 0 else "Önceki parçaya geçiliyor."

    def update_music_status(self, title=None, request_id=None):
        status = f"Çalıyor: {title}" if title else self.idle_status
        with self.navigation_lock:
            if request_id is not None and request_id != self.music_request_id:
                return
            self.doChangeStatus(0x1000, status.encode("utf-8"))

    def is_admin(self, user_id):
        user = self.getUser(user_id)
        return user.nUserID == user_id and user.uUserType == tt.UserType.USERTYPE_ADMIN

    def save_bot_settings(self):
        target = PROJECT_DIR / "config.json"
        data = json.loads(target.read_text(encoding="utf-8"))
        data["teamtalk"]["nickname"] = self.desired_nickname
        data["teamtalk"]["status_message"] = self.idle_status
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=PROJECT_DIR,
                                             prefix=".config-", suffix=".tmp",
                                             delete=False) as file:
                temporary = Path(file.name)
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
            os.replace(temporary, target)
            self.bot_nickname = self.desired_nickname
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def advance_playlist(self, index, request_id):
        with self.navigation_lock:
            if request_id != self.music_request_id:
                return None
            step = self.navigation_delta if self.navigation_pending else 1
            next_index = index + step
            self.navigation_pending = False
            self.navigation_delta = 0
            if 0 <= next_index < len(self.playlist):
                self.current_index = next_index
                self.track_stop_event = threading.Event()
            else:
                self.current_index = None
                self.track_stop_event = None
        self.current_track = None
        self.update_music_status(request_id=request_id)
        return next_index

    def send_private_message(self, user_id, message):
        msg = tt.TextMessage()
        msg.nMsgType = tt.TextMsgType.MSGTYPE_USER
        msg.nToUserID = user_id
        msg.szMessage = message.encode("utf-8")
        result = self.doTextMessage(msg)
        print(f"Ozel mesaj gonderme komut numarasi: {result}", flush=True)

    def play_youtube_request(self, query, user_id, stop_event, previous_thread, request_id):
        from tempfile import TemporaryFile
        from youtube_service import (
            search_first, download_audio, start_audio_stream, temporary_audio_dir,
        )
        from player import play_mp3

        initial_audio_announced = False
        try:
            result = search_first(query)
            videos = (result.get("videos") or [result])[:10]
            print(f"YouTube aramasi: {len(videos)} parca bulundu.", flush=True)
            if stop_event.is_set() or request_id != self.music_request_id:
                return
            if previous_thread is not None and previous_thread.is_alive():
                previous_thread.join(timeout=10)
            if stop_event.is_set() or request_id != self.music_request_id:
                return

            with self.navigation_lock:
                if stop_event.is_set() or request_id != self.music_request_id:
                    return
                self.playlist = videos
                self.current_index = 0
                self.track_stop_event = threading.Event()

            index = 0
            while index < len(videos):
                if stop_event.is_set() or request_id != self.music_request_id:
                    return
                with self.navigation_lock:
                    if request_id != self.music_request_id:
                        return
                    track_event = self.track_stop_event
                video = videos[index]
                title = video.get("title") or query
                print(f"YouTube parca {index + 1}/{len(videos)}: {title} [{video['id']}]", flush=True)
                announced = False
                track_started = time.monotonic()

                def announce_playing():
                    nonlocal announced, initial_audio_announced
                    if not announced and not stop_event.is_set() and not track_event.is_set():
                        announced = True
                        self.current_track = video
                        self.update_music_status(title, request_id=request_id)
                        print(f"İlk ses hazırlama süresi: {time.monotonic() - track_started:.2f} saniye", flush=True)
                        if index == 0 and not initial_audio_announced:
                            initial_audio_announced = True
                            self.send_private_message(user_id, f"Çalınıyor: {title}")

                played = False
                with TemporaryFile() as stream_errors:
                    try:
                        source = start_audio_stream(video["id"], stream_errors)
                        played = play_mp3(
                            self, None, self.music_volume, track_event,
                            source_process=source,
                            on_first_audio=announce_playing,
                        )
                    except Exception as stream_exc:
                        print(f"YouTube akış hatası: {stream_exc}", flush=True)
                    if not played:
                        stream_errors.seek(0)
                        print("YouTube akış çıktısı:", stream_errors.read().decode(errors="replace")[-700:], flush=True)

                if stop_event.is_set() or request_id != self.music_request_id:
                    return
                if track_event.is_set() or played:
                    index = self.advance_playlist(index, request_id)
                    if index is None:
                        return
                    continue

                print("Ses akışı çalışmadı; tam indirme deneniyor.", flush=True)
                if index == 0:
                    self.send_private_message(user_id, "Ses akışı gecikti; indirme deneniyor.")
                try:
                    with temporary_audio_dir() as temp_dir:
                        audio_file = download_audio(video["id"], temp_dir, track_event)
                        if stop_event.is_set() or request_id != self.music_request_id:
                            return
                        if track_event.is_set():
                            index = self.advance_playlist(index, request_id)
                            if index is None:
                                return
                            continue
                        played = play_mp3(
                            self, audio_file, self.music_volume, track_event,
                            on_first_audio=announce_playing,
                        )
                except Exception as video_exc:
                    print(f"Parça oynatma hatası: {video_exc}", flush=True)
                if stop_event.is_set() or request_id != self.music_request_id:
                    return
                if track_event.is_set():
                    index = self.advance_playlist(index, request_id)
                    if index is None:
                        return
                    continue
                if not played:
                    print(f"Parça çalınamadı, sıradakine geçiliyor: {title}", flush=True)
                index = self.advance_playlist(index, request_id)
                if index is None:
                    return

            print("Arama sonuçlarındaki parçalar tamamlandı.", flush=True)
        except Exception as exc:
            print(f"YouTube oynatma hatası: {exc}", flush=True)
            if not initial_audio_announced:
                self.send_private_message(user_id, f"YouTube şarkısı çalınamadı: {str(exc)[:200]}")
        finally:
            should_reset_status = False
            with self.navigation_lock:
                if request_id == self.music_request_id:
                    self.current_track = None
                    self.playlist = []
                    self.current_index = None
                    self.track_stop_event = None
                    self.navigation_pending = False
                    self.navigation_delta = 0
                    should_reset_status = True
            if should_reset_status:
                self.update_music_status(request_id=request_id)

    def onCmdUserJoinedChannel(self, user):
        if user.nUserID != self.getMyUserID():
            return
        channelid = user.nChannelID
        self.joined = True
        print("Bot kanala katildi:", channelid, flush=True)

        channel_info = self.getChannel(channelid)
        codec = channel_info.audiocodec
        self.channel_audio_channels = (
            codec.u.opus.nChannels
            if codec.nCodec == tt.Codec.OPUS_CODEC
            and codec.u.opus.nChannels in (1, 2)
            else 1
        )

        print("Kanal ses kodegi:", codec.nCodec, flush=True)

        if codec.nCodec == tt.Codec.OPUS_CODEC:
            print("Ornekleme hizi:", codec.u.opus.nSampleRate, flush=True)
            print("Kanal sayisi:", codec.u.opus.nChannels, flush=True)
            print("Bit hizi:", codec.u.opus.nBitRate, flush=True)
            print("Paket gonderim araligi:", codec.u.opus.nTxIntervalMSec, flush=True)
            print("Opus cerceve suresi:", codec.u.opus.nFrameSizeMSec, flush=True)

    def onCmdError(self, cmdid, errmsg):
        print("TeamTalk komut hatasi:", errmsg.nErrorNo, flush=True)
        if self.pending_nickname is not None and cmdid == self.pending_nickname[0]:
            _, _, user_id = self.pending_nickname
            self.pending_nickname = None
            self.send_private_message(user_id, f"Canlı ad değişmedi (TeamTalk hata kodu: {errmsg.nErrorNo}). Bot bağlı kalıyor.")

    def onCmdUserUpdate(self, user):
        if self.pending_nickname is None or user.nUserID != self.getMyUserID():
            return
        _, new_name, user_id = self.pending_nickname
        visible_name = user.szNickname
        if isinstance(visible_name, bytes):
            visible_name = visible_name.decode("utf-8", errors="replace")
        if visible_name == new_name:
            self.pending_nickname = None
            self.bot_nickname = new_name
            self.send_private_message(user_id, f"Bot adı değiştirildi: {new_name}")

    def onConnectFailed(self):
        self.connection_failed = True
        print("Sunucu baglantisi basarisiz.", flush=True)

    def onConnectionLost(self):
        self.connection_failed = True
        self.logged_in = False
        self.joined = False
        self.pending_nickname = None
        print("Sunucu baglantisi koptu.", flush=True)

    def onCmdMyselfLoggedOut(self):
        self.logged_in = False
        self.joined = False
        print("Bot oturumu kapatildi.", flush=True)

    def onCmdMyselfKickedFromChannel(self, channelid, user):
        self.kicked = True
        print("Bot yonetici tarafindan cikarildi.", flush=True)


def main():
    with open(PROJECT_DIR / "config.json", encoding="utf-8") as f:
        settings = json.load(f)
        config = settings["teamtalk"]
        audio_settings = settings["audio"]

    bot = CBTCTeamTalk(config)
    from ytdlp_update import start_auto_update
    start_auto_update()
    from commands import audio

    audio.max_volume = int(audio_settings["max_volume"])
    audio.set_volume(int(audio_settings["volume"]))

    bot.max_volume = audio.max_volume
    bot.music_volume = audio.get_volume()
    bot.test_audio_enabled = False

    print("CBTC Bot baslatiliyor...", flush=True)

    try:
        while True:
            bot.logged_in = False
            bot.joined = False
            bot.connection_failed = False
            bot.kicked = False

            print("TeamTalk baglantisi deneniyor...", flush=True)

            connected = bot.connect(
                config["host"].encode("utf-8"),
                config["tcp_port"],
                config["udp_port"],
                bEncrypted=config["encrypted"]
            )

            if connected:
                while True:
                    bot.runEventLoop(1000)

                    if bot.kicked or bot.connection_failed or bot.restart_requested:
                        break
            else:
                print("Baglanti baslatilamadi.", flush=True)

            if bot.restart_requested:
                for stop_event in (getattr(bot, "music_stop_event", None), bot.track_stop_event):
                    if stop_event is not None:
                        stop_event.set()
                print("Bot yeniden başlatılıyor...", flush=True)
                time.sleep(0.3)
                bot.disconnect()
                os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve())])

            bot.disconnect()

            if bot.kicked:
                print("Yonetici tarafindan cikarildi. Bot durduruluyor.", flush=True)
                break

            print("5 saniye sonra yeniden denenecek.", flush=True)
            time.sleep(5)

    except KeyboardInterrupt:
        print("Bot durduruluyor.", flush=True)
    finally:
        bot.disconnect()


if __name__ == "__main__":
    main()
