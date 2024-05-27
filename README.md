
# EczaneBot 
![](https://img.shields.io/badge/Python-Docker-blue) 

Konumunuza en yakın nöbetçi eczanelerin bilgilerini öğrenmek için hazırlanmış open source Telegram botu.



## Nasıl Çalışıyor

- Telegram üzerinden gönderilen konumun enlem ve boylamını kaydediyor.
- Hazırladığım turkeyDistricts.json dosyasını kullanarak bulunduğunuz konuma en yakın 3 ilçeyi buluyor.
- https://www.eczaneler.gen.tr üzerinden bu ilçeler için arama yapıyor.
- Bulunan eczanelerden koordinatlarınıza en yakın 4 tanesinin bilgilerini size gönderiyor.

  
## Değişkenler

Bu projeyi çalıştırmak için aşağıdaki ortam değişkenini .env dosyanıza eklemeniz gerekecek.


`TELEGRAM_BOT_TOKEN`

  
## Docker ile Local Kurulum

Projeyi klonlayın

```bash
  git clone https://github.com/lilmirac/eczaneBot.git
```

Proje dizinine gidin

```bash
  cd eczaneBot
```
[Buradan](https://t.me/BotFather) oluşturduğunuz Telegram botunuzun tokenini .env dosyasına `TELEGRAM_BOT_TOKEN` değişkenini olarak ekleyin

Projeyi docker ile buildleyin

```bash
  docker build -t eczaneBot .
```

Projeyi çalıştırın

```bash
  docker run eczaneBot
```

  
## Destek

Destek için contact@mirac.dev adresinden ulaşabilirsiniz.

  
## Lisans

[MIT](https://github.com/lilmirac/eczaneBot/blob/main/LICENSE)

  