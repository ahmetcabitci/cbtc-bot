
# CBTC Bot

CBTC Bot, TeamTalk kanallarında müzik çalmak için geliştirilen bir bottur. Yerel müzikleri ve YouTube'da aranan şarkıları oynatır. Bir aramada en fazla 10 sonuç alır, ilk sonucu çalar ve sonraki parçalara geçebilir.

## Resmî Web Sitesi

CBTC Bot hakkında ayrıntılı bilgi almak, özelliklerini incelemek ve proje tanıtımını okumak için resmî web sitesini ziyaret edebilirsiniz:

[CBTC Bot – Resmî Web Sitesi](https://www.ahmetcabitci.com.tr/cbtc-bot/)

## Kurulum

Ubuntu 24.04 ve 26.04 x86_64 üzerinde sıfırdan kurulum için [KURULUM.txt](KURULUM.txt) dosyasını açın. Dosyada PuTTY'de çalıştırılacak komutlar sırayla verilmiş ve ne işe yaradıkları açıklanmıştır. Git kurmadan, GitHub ZIP bağlantısı üzerinden bot indirilir. Ubuntu 24 SDK dosyaları GitHub paketinde bulunmaz; bunları geliştiriciden ayrı ZIP olarak alıp kurulum kılavuzundaki klasöre yerleştirin. `tools/sdk_indir.py` bu dosyaları doğrular. Ubuntu 26'da aynı araç uygun SDK paketini BearWare'ın resmî sayfasından indirir. Ubuntu 26 kurulumu henüz gerçek sunucuda doğrulanmadı.

## Kullanım

Botu özel mesajla yönetebilirsiniz. `o sanatçı şarkı` komutu YouTube'da arar ve ilk sonucu çalar. `d` çalmayı durdurur. `i` sonraki, `g` önceki parçaya geçer. `y` yardım menüsünü gösterir. Yönetici ayarları ve diğer komutlar da yardım menüsünde açıklanır.

Bot arka planda systemd servisiyle çalışabilir. YouTube sesini almak için kullanılan yt-dlp bileşeni, yeni kararlı sürümleri GitHub üzerinden arka planda kontrol eder.

## Geliştirici ve İletişim

**Geliştirici:** Ahmet Çabıtçı

**E-posta:** cabitciahmet@gmail.com

**Telegram grubu:** [CBTC Bot](https://t.me/cabitcibot)


## Lisans

CBTC Bot, GNU General Public License v3.0 (GPL-3.0) kapsamında yayımlanan ücretsiz ve açık kaynaklı bir yazılımdır.

Yazılımı lisans koşullarına uygun olarak kullanabilir, inceleyebilir, değiştirebilir ve yeniden dağıtabilirsiniz.

Lisansın tüm koşulları için [LICENSE](LICENSE) dosyasını inceleyebilirsiniz.

## Projeye Katkıda Bulunma

CBTC Bot'un geliştirilmesine katkıda bulunmak isteyen herkesi bekliyoruz.

Hataları GitHub üzerinden bildirebilir, yeni özellikler önerebilir ve geliştirmelerinizi pull request yoluyla projeye gönderebilirsiniz.

Katkıda bulunmak isteyen geliştiriciler GitHub deposunu ziyaret edebilir:

[CBTC Bot GitHub Deposu](https://github.com/ahmetcabitci/cbtc-bot)

