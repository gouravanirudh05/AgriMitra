from langchain_community.utilities import OpenWeatherMapAPIWrapper

weather = OpenWeatherMapAPIWrapper()

weather_data = weather.run("London,GB")
print(weather_data)