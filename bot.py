import telebot
import requests
from bs4 import BeautifulSoup
from math import radians, sin, cos, sqrt, atan2
import random
import time
import json
import threading
import unicodedata

bot = telebot.TeleBot('6881791338:AAGONxCAQ3SB1Hz7VcBWCh0fObI87k-xqqk')
pharmacies_file = 'pharmacies.json'

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def clear_pharmacies_data():
    while True:
        current_time = time.localtime()
        next_clear_time = ((24 - current_time.tm_hour + 9) % 24) * 3600 - current_time.tm_min * 60 - current_time.tm_sec
        time.sleep(next_clear_time)
        
        with open(pharmacies_file, 'r') as file:
            pharmacies_data = json.load(file)
        
        for city in pharmacies_data:
            pharmacies_data[city] = []
        
        with open(pharmacies_file, 'w') as file:
            json.dump(pharmacies_data, file, ensure_ascii=False, indent=4)
        
        print("Pharmacy data cleared at 9 am local time")
        time.sleep(86400 - (time.time() % 86400) + 32400)  # Sleep until the next 9 AM

def initialize_pharmacies_file():
    try:
        with open(pharmacies_file, 'r') as file:
            pharmacies_data = json.load(file)
        # Clear the pharmacy data
        for city in pharmacies_data:
            pharmacies_data[city] = []
    except (FileNotFoundError, json.JSONDecodeError):
        cities = ["adana", "adiyaman", "afyonkarahisar", "agri", "aksaray", "amasya", "ankara", "antalya", "ardahan", 
                  "artvin", "aydin", "balikesir", "bartin", "batman", "bayburt", "bilecik", "bingol", "bitlis", 
                  "bolu", "burdur", "bursa", "canakkale", "cankiri", "corum", "denizli", "diyarbakir", "duzce", 
                  "edirne", "elazig", "erzincan", "erzurum", "eskisehir", "gaziantep", "giresun", "gumushane", 
                  "hakkari", "hatay", "igdir", "isparta", "istanbul", "izmir", "kahramanmaras", "karabuk", 
                  "karaman", "kars", "kastamonu", "kayseri", "kirikkale", "kirklareli", "kirsehir", "kilis", 
                  "kocaeli", "konya", "kutahya", "malatya", "manisa", "mardin", "mersin", "mugla", "mus", 
                  "nevsehir", "nigde", "ordu", "osmaniye", "rize", "sakarya", "samsun", "sanliurfa", "siirt", 
                  "sinop", "sirnak", "sivas", "tekirdag", "tokat", "trabzon", "tunceli", "usak", "van", "yalova", 
                  "yozgat", "zonguldak"]
        pharmacies_data = {city: [] for city in cities}
    
    with open(pharmacies_file, 'w') as file:
        json.dump(pharmacies_data, file, ensure_ascii=False, indent=4)
    print("Pharmacy data cleared at script start")

def get_user_location(latitude, longitude):
    address = requests.get(f"https://nominatim.openstreetmap.org/search?q={latitude}%2C+{longitude}&format=jsonv2&addressdetails=1", headers=headers).json()[0]
    city = address.get('address', {}).get('province', '')
    town = address.get('address', {}).get('town', '')
    city = unicodedata.normalize('NFKD', city).encode('ascii', 'ignore').decode('utf-8').lower()
    town = unicodedata.normalize('NFKD', town).encode('ascii', 'ignore').decode('utf-8').lower()
    return city, town

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def get_pharmacy_coords(pharmacies, city, baselatitude, baselongitude):
    print(f"Found {len(pharmacies)} pharmacies in {city}")
    for pharmacy in pharmacies:
        name = pharmacy['name']
        response = requests.get(f"https://nominatim.openstreetmap.org/search.php?street={name}&city={city}&format=jsonv2", headers=headers)
        if response.json():
            pharmacy['lat'] = float(response.json()[0]['lat'])
            pharmacy['lon'] = float(response.json()[0]['lon'])
        else:
            pharmacy['lat'] = None
            pharmacy['lon'] = None
        time.sleep(random.uniform(0.4, 0.6))
    valid_pharmacies = [pharmacy for pharmacy in pharmacies if pharmacy['lat'] and pharmacy['lon']]
    return valid_pharmacies

def calculate_distances_and_sort(pharmacies, latitude, longitude):
    for pharmacy in pharmacies:
        pharmacy['distance'] = calculate_distance(latitude, longitude, pharmacy['lat'], pharmacy['lon'])
    pharmacies.sort(key=lambda x: x['distance'])
    return pharmacies[:3]

def list_pharmacies(city):
    city = city.lower().replace('ç', 'c').replace('ö', 'o').replace('ü', 'u').replace('ğ', 'g').replace('ş', 's').replace('ı', 'i')
    link = f"https://www.eczaneler.gen.tr/nobetci-{city}"
    response = requests.get(link, headers=headers)
    if response.status_code == 200:
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        pharmacy_entries = soup.find_all('td', class_='border-bottom')
        pharmacies = []
        for entry in pharmacy_entries:
            name = entry.find('span', class_='isim').text.strip()
            number_tag = entry.find(class_='col-lg-3 py-lg-2')
            number = number_tag.text.strip() if number_tag else None
            district = entry.find(class_='bg-info').text.strip() if entry.find(class_='bg-info') else None
            address = entry.find(class_='col-lg-6').text.strip().split('»')[0].strip() if entry.find(class_='col-lg-6') else None
            direction_tag = entry.find(class_='font-italic') if entry.find(class_='font-italic') else None
            direction = direction_tag.text.strip() if direction_tag else ''
            pharmacy_info = {
                "name": name,
                "number": number,
                "district": district,
                "address": address,
                "direction": direction
            }
            pharmacies.append(pharmacy_info)
        return pharmacies
    else:
        return []
    

def check_and_update_pharmacies(city, latitude, longitude):
    with open(pharmacies_file, 'r') as file:
        pharmacies_data = json.load(file)
    if pharmacies_data[city]:
        print(f"Using cached data for {city}")
        return pharmacies_data[city]
    else:
        pharmacies_list = list_pharmacies(city)
        closest_pharmacies = get_pharmacy_coords(pharmacies_list, city, latitude, longitude)
        with open(pharmacies_file, 'r') as file:
            pharmacies_data = json.load(file)
        pharmacies_data[city] = closest_pharmacies
        with open(pharmacies_file, 'w') as file:
            json.dump(pharmacies_data, file, ensure_ascii=False, indent=4)
        return closest_pharmacies

@bot.message_handler(content_types=['location'])
def handle_location(message):
    startTime = time.time()
    latitude, longitude = message.location.latitude, message.location.longitude
    city, town = get_user_location(latitude, longitude)
    pharmacies_data = {}
    with open(pharmacies_file, 'r') as file:
        pharmacies_data = json.load(file)
    if city.lower() in pharmacies_data and pharmacies_data[city.lower()]:  # Check if cached data exists and contains pharmacies for the city
        bot.reply_to(message, f"{city.upper()} şehrinde size en yakın nöbetçi eczaneler listeleniyor.")
        time.sleep(2)
    else:
        bot.reply_to(message, f"{city.upper()} şehrindeki {len(list_pharmacies(city))} nöbetçi eczaneler arasında size en yakın olanlar listeleniyor. Bu işlem 1-2 dakika sürebilir.")
    closest_pharmacies = check_and_update_pharmacies(city, latitude, longitude)
    for pharmacy in closest_pharmacies:
        pharmacy['distance'] = calculate_distance(latitude, longitude, pharmacy['lat'], pharmacy['lon'])
    closest_pharmacies.sort(key=lambda x: x['distance'])
    for pharmacy in closest_pharmacies[:3]:
        google_maps_link = f"https://www.google.com/maps/place/{pharmacy['lat']},{pharmacy['lon']}"
        bot.send_message(
            message.chat.id, 
            f"*{pharmacy['name']}* ({pharmacy['distance']:.2f} km)\n"
            f"{pharmacy['number']}\n"
            f"{pharmacy['address']}\n"
            f"{google_maps_link}\n"
        , parse_mode='Markdown')
        time.sleep(0.5)
    print(f"Execution time: {time.time() - startTime:.2f} seconds")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Merhaba! Konumunuzu göndererek size en yakın nöbetçi eczaneleri öğrenebilirsiniz.")


initialize_pharmacies_file()
clearing_thread = threading.Thread(target=clear_pharmacies_data)
clearing_thread.start()

bot.polling()
