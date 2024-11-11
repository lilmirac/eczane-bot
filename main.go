package main

import (
	"encoding/json"
	"fmt"
	"html"
	"io/ioutil"
	"log"
	"math"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
	"unicode"

	"github.com/joho/godotenv"
	"github.com/microcosm-cc/bluemonday"
	tele "gopkg.in/telebot.v3"
)

type NominatimResponse struct {
	Address struct {
		City, Town, Province, County, State string
	}
}

type District struct {
	District string  `json:"district"`
	Lat, Lon float64 `json:"lat,lon"`
}

type DistrictsData map[string][]District

type Pharmacy struct {
	Name, Number, Address, District string `json:"name,number,address,district"`
	Lat, Lon                       float64 `json:"lat,lon"`
}

type Config struct {
	MaxRequestsPerDay    int           `json:"maxRequestsPerDay"`
	MaxConcurrentJobs    int           `json:"maxConcurrentJobs"`
	MaxDistanceKM        float64       `json:"maxDistanceKM"`
	MaxPharmaciesReturn  int           `json:"maxPharmaciesReturn"`
	MaxNearbyDistricts   int           `json:"maxNearbyDistricts"`
	HTTPClientTimeout    time.Duration `json:"httpClientTimeout"`
	GeocodingDelay      time.Duration `json:"geocodingDelay"`
	BotPollingTimeout   time.Duration `json:"botPollingTimeout"`
}

var (
	config = Config{
		MaxRequestsPerDay:    5,
		MaxConcurrentJobs:    1,
		MaxDistanceKM:        25.0,
		MaxPharmaciesReturn:  6,
		MaxNearbyDistricts:   2,
		HTTPClientTimeout:    10 * time.Second,
		GeocodingDelay:      300 * time.Millisecond,
		BotPollingTimeout:    10 * time.Second,
	}
	
	rateLimits = make(map[int64]struct {
		count    int
		lastDate time.Time
	})
	rateMutex sync.RWMutex
	
	processQueue = make(chan struct{}, config.MaxConcurrentJobs)
)


func normalizeText(text string) string {
	if len(text) > 100 {
		return ""
	}
	
	valid := true
	for _, r := range text {
		if !unicode.IsLetter(r) && !unicode.IsNumber(r) && !unicode.IsPunct(r) && !unicode.IsSpace(r) {
			valid = false
			break
		}
	}
	if !valid {
		return ""
	}
	
	replacer := strings.NewReplacer("ç", "c", "ğ", "g", "ı", "i", "ö", "o", "ş", "s", "ü", "u")
	return replacer.Replace(strings.ToLower(text))
}

func getUserLocation(lat, lng float64) (city, district string, err error) {
	if !validateCoordinates(lat, lng) {
		return "", "", fmt.Errorf("invalid coordinates")
	}
	
	var result NominatimResponse
	if err := makeRequest(
		fmt.Sprintf("https://nominatim.openstreetmap.org/reverse?lat=%f&lon=%f&format=json", lat, lng),
		&result,
	); err != nil {
		return "", "", err
	}
	
	city = normalizeText(strings.TrimSpace(coalesce(result.Address.Province, result.Address.City, result.Address.State)))
	district = normalizeText(strings.TrimSpace(coalesce(result.Address.Town, result.Address.County)))
	return
}

func coalesce(strings ...string) string {
	for _, s := range strings {
		if s != "" {
			return s
		}
	}
	return ""
}

func makeRequest(url string, target interface{}) error {
	client := &http.Client{Timeout: config.HTTPClientTimeout}
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return fmt.Errorf("error creating request: %w", err)
	}
	req.Header.Set("User-Agent", "TelegramBot/1.0")
	
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("error making request: %w", err)
	}
	defer resp.Body.Close()
	
	return json.NewDecoder(resp.Body).Decode(target)
}

func calculateDistance(lat1, lon1, lat2, lon2 float64) float64 {
	const R = 6371.0
	lat1Rad := lat1 * math.Pi / 180
	lon1Rad := lon1 * math.Pi / 180
	lat2Rad := lat2 * math.Pi / 180
	lon2Rad := lon2 * math.Pi / 180
	dLat := lat2Rad - lat1Rad
	dLon := lon2Rad - lon1Rad
	
	a := math.Sin(dLat/2)*math.Sin(dLat/2) +
		 math.Cos(lat1Rad)*math.Cos(lat2Rad)*
		 math.Sin(dLon/2)*math.Sin(dLon/2)
	
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
	
	distance := R * c
	return math.Round(distance*100)/100
}

func findNearestDistricts(city, currentDistrict string, latitude, longitude float64, districts DistrictsData) []string {
	type distanceInfo struct {
		district string
		distance float64
	}
	
	var distances []distanceInfo

	if cityDistricts, ok := districts[city]; ok {
		distances = append(distances, distanceInfo{
			district: currentDistrict,
			distance: 0,
		})

		for _, d := range cityDistricts {
			if normalizeText(d.District) == currentDistrict {
				continue
			}
			
			distance := calculateDistance(latitude, longitude, d.Lat, d.Lon)
			if distance <= config.MaxDistanceKM {
				distances = append(distances, distanceInfo{
					district: d.District,
					distance: distance,
				})
			}
		}
	}

	sort.Slice(distances, func(i, j int) bool {
		return distances[i].distance < distances[j].distance
	})
	result := make([]string, 0, config.MaxNearbyDistricts+1)
	for i := 0; i < len(distances) && i < config.MaxNearbyDistricts+1; i++ {
		result = append(result, distances[i].district)
	}

	return result
}

func listPharmacies(city, district string) ([]Pharmacy, error) {
	client := &http.Client{Timeout: 15 * time.Second}
	req, err := http.NewRequest("GET", fmt.Sprintf("https://www.eczaneler.gen.tr/nobetci-%s-%s", city, district), nil)
	if err != nil {
		return nil, fmt.Errorf("error creating request: %w", err)
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
	
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("error making request: %w", err)
	}
	defer resp.Body.Close()
	
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("error reading response: %w", err)
	}

	regexes := map[string]*regexp.Regexp{
		"name":    regexp.MustCompile(`<span class="isim">(.*?)</span>`),
		"number":  regexp.MustCompile(`<div class='col-lg-3 py-lg-2'>(.*?)</div>`),
		"address": regexp.MustCompile(`<div class='col-lg-6'>(.*?)(?:<div|<br>|</div>)`),
	}
	
	matches := make(map[string][][]string)
	for key, regex := range regexes {
		matches[key] = regex.FindAllStringSubmatch(string(body), -1)
	}
	
	var pharmacies []Pharmacy
	for i := 0; i < len(matches["name"]); i++ {
		pharmacies = append(pharmacies, Pharmacy{
			Name:     strings.TrimSpace(matches["name"][i][1]),
			Number:   strings.TrimSpace(matches["number"][i][1]),
			Address:  strings.TrimSpace(matches["address"][i][1]),
			District: district,
		})
	}
	
	return pharmacies, nil
}

func getPharmacyCoords(city string, pharmacies []Pharmacy) ([]Pharmacy, error) {
	client := &http.Client{Timeout: config.HTTPClientTimeout}
	var result []Pharmacy

	for _, pharmacy := range pharmacies {
		url := fmt.Sprintf("https://nominatim.openstreetmap.org/search.php?street=%s&city=%s&format=jsonv2",
			url.QueryEscape(pharmacy.Name), url.QueryEscape(city))
		
		req, err := http.NewRequest("GET", url, nil)
		if err != nil {
			continue
		}
		req.Header.Set("User-Agent", "TelegramBot/1.0")
		
		resp, err := client.Do(req)
		if err != nil {
			continue
		}
		defer resp.Body.Close()

		var locations []struct {
			Lat string `json:"lat"`
			Lon string `json:"lon"`
		}
		
		if err := json.NewDecoder(resp.Body).Decode(&locations); err != nil {
			continue
		}

		if len(locations) > 0 {
			lat, _ := strconv.ParseFloat(locations[0].Lat, 64)
			lon, _ := strconv.ParseFloat(locations[0].Lon, 64)
			pharmacy.Lat = lat
			pharmacy.Lon = lon
			result = append(result, pharmacy)
		}

		time.Sleep(config.GeocodingDelay)
	}

	return result, nil
}

func sortPharmacies(pharmacies []Pharmacy, latitude, longitude float64, numPharmacies int) []Pharmacy {
	sort.Slice(pharmacies, func(i, j int) bool {
		distI := calculateDistance(latitude, longitude, pharmacies[i].Lat, pharmacies[i].Lon)
		distJ := calculateDistance(latitude, longitude, pharmacies[j].Lat, pharmacies[j].Lon)
		return distI < distJ
	})

	if len(pharmacies) > numPharmacies {
		return pharmacies[:numPharmacies]
	}
	return pharmacies
}

func checkRateLimit(userID int64) bool {
	rateMutex.Lock()
	defer rateMutex.Unlock()
	
	now := time.Now()
	userData, exists := rateLimits[userID]
	
	if !exists || !isSameDay(userData.lastDate, now) {
		rateLimits[userID] = struct {
			count    int
			lastDate time.Time
		}{1, now}
		return true
	}
	
	if userData.count >= config.MaxRequestsPerDay {
		return false
	}
	
	userData.count++
	userData.lastDate = now
	rateLimits[userID] = userData
	return true
}

func isSameDay(t1, t2 time.Time) bool {
	y1, m1, d1 := t1.Date()
	y2, m2, d2 := t2.Date()
	return y1 == y2 && m1 == m2 && d1 == d2
}

func validateCoordinates(lat, lng float64) bool {
	return lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180
}

func sanitizeText(text string) string {
	p := bluemonday.StrictPolicy()
	sanitized := p.Sanitize(text)
	sanitized = html.EscapeString(sanitized)
	return sanitized
}


func main() {
	districtsFile, err := os.ReadFile("turkeyDistricts.json")
	if err != nil {
		log.Fatalf("Error reading districts file: %v", err)
	}

	var districts DistrictsData
	if err := json.Unmarshal(districtsFile, &districts); err != nil {
		log.Fatalf("Error parsing districts data: %v", err)
	}

	if err := godotenv.Load(); err != nil {
		log.Printf("Warning: Error loading .env file: %v", err)
	}

	botToken := os.Getenv("TELEGRAM_BOT_TOKEN")
	if botToken == "" {
		log.Fatal("TELEGRAM_BOT_TOKEN is required")
	}

	pref := tele.Settings{
		Token:  botToken,
		Poller: &tele.LongPoller{Timeout: config.BotPollingTimeout},
	}

	bot, err := tele.NewBot(pref)
	if err != nil {
		log.Fatalf("Error creating bot: %v", err)
	}

	bot.Handle("/start", func(c tele.Context) error {
		return c.Send("Merhaba! Ben size en yakın nöbetçi eczaneleri bulmak için buradayım. Konum göndererek çevrenizdeki eczaneleri öğrenebilirsiniz.")
	})

	bot.Handle(tele.OnLocation, func(c tele.Context) error {
		loc := c.Message().Location
		
		if !validateCoordinates(float64(loc.Lat), float64(loc.Lng)) {
			return c.Send("Invalid location coordinates provided.")
		}
		
		if !checkRateLimit(c.Sender().ID) {
			return c.Send(fmt.Sprintf("Günlük %d sorgu limitinizi aştınız. Lütfen yarın tekrar deneyin.", config.MaxRequestsPerDay))
		}
		
		select {
		case processQueue <- struct{}{}:
			defer func() { <-processQueue }()
		default:
			return c.Send("Başka bir istek işleniyor. Lütfen 1 dakika sonra tekrar deneyin.")
		}
		city, district, err := getUserLocation(float64(loc.Lat), float64(loc.Lng))
		if err != nil {
			log.Printf("Error getting location details: %v", err)
			return c.Send("Üzgünüm, konum bilgilerini alamadım. Lütfen daha sonra tekrar deneyin.")
		}

		nearestDistricts := findNearestDistricts(city, district, float64(loc.Lat), float64(loc.Lng), districts)
		
		response := "Konum algılama başarılı. Eczane taraması başlatılıyor..."
		sentMsg, err := c.Bot().Send(c.Chat(), response)
		if err != nil {
			log.Printf("Error sending initial message: %v", err)
			return err
		}

		var allPharmacies []Pharmacy
		totalPharmacyCount := 0

		for _, dist := range nearestDistricts {
			pharmacies, err := listPharmacies(city, dist)
			if err != nil {
				log.Printf("Error fetching pharmacies for %s-%s: %v", city, dist, err)
				continue
			}
			
			
			totalPharmacyCount += len(pharmacies)
			estimatedWaitSeconds := totalPharmacyCount / 2
			progressMsg := fmt.Sprintf("📍 Yakınızdaki nöbetçi eczaneler aranıyor...\n⏰ Tahmini süre: %d saniye", estimatedWaitSeconds)
			
			_, err = c.Bot().Edit(sentMsg, progressMsg)
			if err != nil {
				log.Printf("Error updating progress message: %v", err)
			}
			
			pharmaciesWithCoords, err := getPharmacyCoords(city, pharmacies)
			if err != nil {
				log.Printf("Error getting coordinates: %v", err)
				continue
			}
			
			allPharmacies = append(allPharmacies, pharmaciesWithCoords...)
		}

		closestPharmacies := sortPharmacies(allPharmacies, float64(loc.Lat), float64(loc.Lng), config.MaxPharmaciesReturn)

		var finalResponse strings.Builder
		
		for _, pharmacy := range closestPharmacies {
			searchQuery := url.QueryEscape(fmt.Sprintf("%s %s", pharmacy.Name, pharmacy.District))
			finalResponse.WriteString(fmt.Sprintf("*%s*\n%s\n%s\n[Haritada Aç](https://www.google.com/maps/search/%s/@%f,%f,17z)\n\n",
				sanitizeText(pharmacy.Name),
				sanitizeText(pharmacy.Number),
				sanitizeText(pharmacy.Address),
				searchQuery,
				pharmacy.Lat,
				pharmacy.Lon))
		}

		if len(closestPharmacies) == 0 {
			finalResponse.WriteString("\nYakınınızda hiç nöbetçi eczane bulamadım.")
		}

		_, err = c.Bot().Edit(sentMsg, finalResponse.String(), &tele.SendOptions{
				ParseMode: tele.ModeMarkdown,
				DisableWebPagePreview: true,
			})
		return err
	})

	log.Println("Bot started successfully")
	bot.Start()
}