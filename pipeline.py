import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
params = {
	"latitude": [48.8534, 47.6422, 43.297, 45.7491, 48.5839],
	"longitude": [2.3488, 6.8539, 5.3811, 4.8479, 7.7455],
	"hourly": ["temperature_2m", "relative_humidity_2m", "weather_code", "wind_speed_10m", "precipitation", "apparent_temperature"],
	"models": "meteofrance_seamless",
	"timezone": "auto",
	"start_date": "2026-08-04",
	"end_date": "2026-09-05",
}
responses = openmeteo.weather_api(url, params = params)

# Process 5 locations
for response in responses:
	print(f"\nCoordinates: {response.Latitude()}°N {response.Longitude()}°E")
	print(f"Elevation: {response.Elevation()} m asl")
	print(f"Timezone: {response.Timezone()}{response.TimezoneAbbreviation()}")
	print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")
	
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
	
	hourly_dataframe = pd.DataFrame(data = hourly_data)
	print("\nHourly data\n", hourly_dataframe)
	