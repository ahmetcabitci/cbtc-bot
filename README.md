# CBTC Bot

CBTC Bot, TeamTalk kanallarında müzik çalmak için geliştirilen bir bottur. Yerel müzikleri ve YouTube'da aranan şarkıları oynatır. Bir aramada en fazla 10 sonuç alır, ilk sonucu çalar ve sonraki parçalara geçebilir.

## Kurulum

Ubuntu 24.04 üzerinde sıfırdan kurulum için [KURULUM.txt](KURULUM.txt) dosyasını açın. Dosyada her komut çalıştırılacak sırada verilmiş ve ne işe yaradığı açıklanmıştır. TeamTalk SDK'nın Ubuntu sürümüne uygun olması gerekir.

## Kullanım

Botu özel mesajla yönetebilirsiniz. `o sanatçı şarkı` komutu YouTube'da arar ve ilk sonucu çalar. `d` çalmayı durdurur. `i` sonraki, `g` önceki parçaya geçer. `y` yardım menüsünü gösterir. Yönetici ayarları ve diğer komutlar da yardım menüsünde açıklanır.

Bot arka planda systemd servisiyle çalışabilir. YouTube sesini almak için kullanılan yt-dlp bileşeni, yeni kararlı sürümleri GitHub üzerinden arka planda kontrol eder.

## Geliştirici ve iletişim

CBTC Bot'u geliştiren ve kurulum kılavuzunu hazırlayan: Ahmet Çabıtçı.

Öneri ve görüşler: cabitciahmet@gmail.com

Telegram grubu: [CBTC Bot](https://t.me/cabitcibot)
