import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from datetime import date, timedelta

# Extraction des données

# Date
fin = date.today() - timedelta(days=1)
debut = fin - timedelta(days=30)

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://historical-forecast-api.open-meteo.com/v1/forecast"

# Liste des villes pour lesquelles nous voulons récupérer les données météorologiques
villes = ["Paris", "Belfort", "Marseille", "Lyon", "Strasbourg"]

params = {
	"latitude": [48.8534, 47.6422, 43.297, 45.7491, 48.5839],
	"longitude": [2.3488, 6.8539, 5.3811, 4.8479, 7.7455],
	"hourly": ["temperature_2m", "relative_humidity_2m", "weather_code", "wind_speed_10m", "precipitation", "apparent_temperature"],
	"models": "meteofrance_seamless",
	"timezone": "auto",
	"start_date": debut.isoformat(),
	"end_date": fin.isoformat(),
}
responses = openmeteo.weather_api(url, params = params)

# Variable qui contiendra tous les dataframes pour chaque ville
all_dataframes = []

# Process 5 locations
for i, response in enumerate(responses):
    
	# Process hourly data. The order of variables needs to be the same as requested.
	hourly = response.Hourly()
	hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
	hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
	hourly_weather_code = hourly.Variables(2).ValuesAsNumpy()
	hourly_wind_speed_10m = hourly.Variables(3).ValuesAsNumpy()
	hourly_precipitation = hourly.Variables(4).ValuesAsNumpy()
	hourly_apparent_temperature = hourly.Variables(5).ValuesAsNumpy()
	
	hourly_data = {
		"date": pd.date_range(
			start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
			end =  pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
			freq = pd.Timedelta(seconds = hourly.Interval()),
			inclusive = "left"
		).tz_convert(response.Timezone().decode())
	}
	
	hourly_data["temperature_2m"] = hourly_temperature_2m
	hourly_data["relative_humidity_2m"] = hourly_relative_humidity_2m
	hourly_data["weather_code"] = hourly_weather_code
	hourly_data["wind_speed_10m"] = hourly_wind_speed_10m
	hourly_data["precipitation"] = hourly_precipitation
	hourly_data["apparent_temperature"] = hourly_apparent_temperature
	
	# Création du dataframe d'une ville à partir des données horaires
	df = pd.DataFrame(data = hourly_data)
	
    # Ajout de la colonne "villes" avec le nom de la ville correspondante
	df["ville"] = villes[i]
	
	# Ajout du dataframe selon son index dans la liste all_dataframes
	all_dataframes.append(df)

# Concatenation de tous les dataframes pour créer un dataframe final
meteo_df = pd.concat(all_dataframes, ignore_index = True)

# Transformation

# Extraction de l'heure dans la colonne date
meteo_df["heure"] = meteo_df["date"].dt.hour

# Extraction du jour dans la colonne date
meteo_df["jour"] = meteo_df["date"].dt.date

# Codes météo selon le standard mondial WMO
codes_meteo = {
    0: "Ciel dégagé", 1: "Plutôt dégagé", 2: "Partiellement nuageux", 3: "Couvert",
    45: "Brouillard", 48: "Brouillard givrant",
    51: "Bruine légère", 53: "Bruine modérée", 55: "Bruine forte",
    56: "Bruine verglaçante légère", 57: "Bruine verglaçante forte",
    61: "Pluie faible", 63: "Pluie modérée", 65: "Pluie forte",
    66: "Pluie verglaçante légère", 67: "Pluie verglaçante forte",
    71: "Neige faible", 73: "Neige modérée", 75: "Neige forte", 77: "Grains de neige",
    80: "Averses faibles", 81: "Averses modérées", 82: "Averses violentes",
    85: "Averses de neige faibles", 86: "Averses de neige fortes",
    95: "Orage", 96: "Orage avec grêle légère", 99: "Orage avec grêle forte",
}

meteo_df["weather_code"] = meteo_df["weather_code"].astype(int)
meteo_df["conditions"] = meteo_df["weather_code"].map(codes_meteo)

# Noms des colonnes en français
meteo_df = meteo_df.rename(columns={
   "temperature_2m": "temperature",
    "apparent_temperature": "temperature_ressentie",
    "relative_humidity_2m": "humidite",
    "wind_speed_10m": "vitesse_vent",
    "precipitation": "precipitations",
    "weather_code": "code_meteo",
})

# Arrondi à 1 décimale
colonnes_num = ["temperature", "temperature_ressentie", "humidite", "vitesse_vent", "precipitations"]
meteo_df[colonnes_num] = meteo_df[colonnes_num].round(1)

# Chargement des données

meteo_sql = meteo_df.copy()
meteo_sql["date"] = meteo_sql["date"].dt.strftime("%Y-%m-%d %H:%M:%S")
meteo_sql["jour"] = meteo_sql["jour"].astype("str")