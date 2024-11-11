# pharmacy-bot

An open-source Telegram bot that provides information about the nearest on-duty pharmacies to your location in Turkey

<img alt="Screenshot1" width="250px" height="300" src="images/Screenshot1.png" />

## Built with

 ![](https://img.shields.io/badge/go-%2300ADD8.svg?style=for-the-badge&logo=go&logoColor=white)

## How?

- Extracts latitude and longitude coordinates from telegram message.
- Identifies the 3 nearest districts to the user's location using a [turkeyDistricts.json](https://github.com/lilmirac/eczane-bot/blob/main/turkeyDistricts.json) database which is prepared by me.
- Queries [eczaneler.gen.tr](https://www.eczaneler.gen.tr) to retrieve on-duty pharmacy information for the identified districts.
- Utilizes the Nominatim API to geocode pharmacy addresses into coordinates.
- Calculates distances to determine the nearest pharmacies and returns relevant information to the user

## Try now
You can test the bot in action at [t.me/NobetciEczaneAra_bot](https://t.me/NobetciEczaneAra_bot)
  
## Variables

*only if you want to run the bot locally*

`TELEGRAM_BOT_TOKEN="Bot Token Received from https://t.me/BotFather"`

## Help

[![Email](https://img.shields.io/badge/Email-000000?style=for-the-badge&logo=gmail&logoColor=white)](mailto:contact@mirac.dev?subject=[GitHub])
[![Website](https://img.shields.io/badge/website-000000?style=for-the-badge&logo=About.me&logoColor=white)](https://mirac.dev)

  
## License

This project is licensed under the MIT License. For more information, see the [LICENSE](https://github.com/lilmirac/eczane-bot/blob/main/LICENSE) file.
  
