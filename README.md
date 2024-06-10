
# eczane-bot

Konumunuza en yakın nöbetçi eczanelerin bilgilerini veren Telegram botu

<img alt="Screenshot1" width="250px" height="300" src="images/Screenshot1.png" />

## Kullanılan Teknolojiler

* ![](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

## Nasıl Çalışıyor

- Telegram üzerinden gönderilen konumun koordinatlarını kullanarak hazırladığım [turkeyDistricts.json](https://github.com/lilmirac/eczane-bot/blob/main/turkeyDistricts.json) dosyasında bulunduğunuz konuma en yakın 3 ilçeyi buluyor.
- [eczaneler.gen.tr](https://www.eczaneler.gen.tr) üzerinden bu ilçeler için nöbetçi eczane araması yapıyor.
- Bulunan nöbetçi eczanelerden konumunuza en yakın 4 eczanenin bilgilerini ve konumlarını size gönderiyor.

## Demo
[Bu telegram bot linki](https://t.me/EczaneProBot) üzerinden hazırladığım demoyu test edebilirsiniz.
  
## Kurulum

Projeyi klonlayın

```sh
  git clone https://github.com/lilmirac/eczane-bot.git
```

Proje dizinine gidin

```sh
  cd eczane-bot
```
[Buradan](https://t.me/BotFather) oluşturduğunuz Telegram botunuzun tokenini .env dosyasına `TELEGRAM_BOT_TOKEN` değişkenini olarak ekleyin

Projeyi docker ile buildleyin

```sh
  docker build -t eczane-bot .
```

Projeyi çalıştırın

```sh
  docker run eczane-bot
```

  
## Destek

Miraç - [contact@mirac.dev](mailto:contact@mirac.dev?subject=[GitHub])

[![Website](https://img.shields.io/badge/website-000000?style=for-the-badge&logo=About.me&logoColor=white)](https://mirac.dev)

  
## Lisans

Bu proje MIT kapsamında lisanslanmıştır. Daha fazla bilgi için [Lisans](https://github.com/lilmirac/eczane-bot/blob/main/LICENSE)'a bakınız.
  
