import telebot
import requests
from bs4 import BeautifulSoup
from math import radians, sin, cos, sqrt, atan2
import random
import time
import json
import unicodedata
from dotenv import load_dotenv
import os

districtsFile = "turkeyDistricts.json"

load_dotenv()
token = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(token)

user_agents = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, lo) Chrome/125.0.0.0 Safari/537.3"
]

def normalize_text(text):
    replaced_text = text.lower().replace('ç', 'c').replace('ö', 'o').replace('ü', 'u').replace('ğ', 'g').replace('ş', 's').replace('ı', 'i')
    normalized_text = unicodedata.normalize('NFKD', replaced_text)
    cleaned_text = ''.join(c for c in normalized_text if not unicodedata.combining(c))
    return cleaned_text

def calculate_distance(lat1, lon1, lat2, lon2):
    earth_radius = 6371.0 
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    inner_term = sin(delta_lat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(delta_lon / 2)**2
    central_angle = 2 * atan2(sqrt(inner_term), sqrt(1 - inner_term))
    distance = earth_radius * central_angle
    return distance

def get_user_location(latitude, longitude):
    address = requests.get(f"https://nominatim.openstreetmap.org/search?q={latitude}%2C+{longitude}&format=jsonv2&addressdetails=1", headers = {"User-Agent": random.choice(user_agents)}).json()[0]
    city = normalize_text(address.get('address', {}).get('province', ''))
    district = normalize_text(address.get('address', {}).get('town', ''))
    return city, district

def find_nearest_districts(city, current_district, latitude, longitude, num_districts=2, max_distance=25):
    district_data = json.load(open(districtsFile))
    distances = []
    for district_info in district_data[city]:
        district_name = district_info['district']
        district_lat, district_lon = district_info['lat'], district_info['lon']
        distance = calculate_distance(latitude, longitude, district_lat, district_lon)
        if distance <= max_distance:
            if district_name != current_district:
                distances.append((district_name, distance))
    sorted_districts = sorted(distances, key=lambda x: x[1])
    return [district for district, _ in sorted_districts[:num_districts]]

def list_pharmacies(city, districts):
    pharmacies = []
    for district in districts:
        response = requests.get(f"https://www.eczaneler.gen.tr/nobetci-{city}-{district}", headers = {"User-Agent": random.choice(user_agents)})
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            pharmacy_entries = soup.find_all('td', class_='border-bottom')
            for entry in pharmacy_entries:
                name = entry.find('span', class_='isim').text.strip()
                number = entry.find(class_='col-lg-3 py-lg-2').text.strip() if entry.find(class_='col-lg-3 py-lg-2') else None
                address = entry.find(class_='col-lg-6').text.strip().split('»')[0].strip() if entry.find(class_='col-lg-6') else None
                pharmacy_info = {"name": name, "number": number, "address": address}
                pharmacies.append(pharmacy_info)
    return pharmacies

def get_pharmacy_coords(city, pharmacies):
    for pharmacy in pharmacies:
        response = requests.get(f"https://nominatim.openstreetmap.org/search.php?street={pharmacy['name']}&city={city}&format=jsonv2", headers = {"User-Agent": random.choice(user_agents)})
        if response.json():
            pharmacy['lat'] = float(response.json()[0]['lat'])
            pharmacy['lon'] = float(response.json()[0]['lon'])
        else:
            pharmacy['lat'] = None
            pharmacy['lon'] = None
        time.sleep(random.uniform(0.2, 0.6))
    return [pharmacy for pharmacy in pharmacies if pharmacy['lat'] and pharmacy['lon']]

def sort_pharmacies(pharmacies, latitude, longitude, num_pharmacies=4):
    for pharmacy in pharmacies:
        pharmacy['distance'] = calculate_distance(latitude, longitude, pharmacy['lat'], pharmacy['lon'])
    pharmacies.sort(key=lambda x: x['distance'])
    return pharmacies[:num_pharmacies]

@bot.message_handler(content_types=['location'])
def location_handler(message):
    startTime = time.time()
    latitude, longitude = message.location.latitude, message.location.longitude
    city, district = get_user_location(latitude, longitude)
    print(f"Received location from {message.chat.id} in {city.upper()} ({latitude}, {longitude})")
    bot.reply_to(message, f"{city.upper()} şehrinde size en yakın nöbetçi eczaneler bulunuyor...")
    near_districts = find_nearest_districts(city, district, latitude, longitude)
    near_districts.append(district)
    print(f"Districts near the location: {near_districts}")
    pharmacies = list_pharmacies(city, near_districts)
    pharmacies_with_coords = get_pharmacy_coords(city, pharmacies)
    print(f"Found {len(pharmacies_with_coords)} pharmacies with coordinates")
    sorted_pharmacies = sort_pharmacies(pharmacies_with_coords, latitude, longitude)
    print(f"Execution time: {time.time() - startTime:.2f} seconds\n")
    for pharmacy in sorted_pharmacies:
        bot.send_message(
            message.chat.id, 
            f"*{pharmacy['name']}* ({pharmacy['distance']:.2f} km)\n"
            f"{pharmacy['number']}\n"
            f"{pharmacy['address']}\n"
            f"https://www.google.com/maps/place/{pharmacy['lat']},{pharmacy['lon']}"
        , parse_mode='Markdown')
        time.sleep(1)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Merhaba! Konumunuzu göndererek size en yakın nöbetçi eczaneleri öğrenebilirsiniz.")


if __name__ == '__main__':
    print("Script started.")
    bot.polling()
