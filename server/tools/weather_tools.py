from mcp.server.fastmcp import FastMCP, Context
import httpx
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Constants for API configuration
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

def register_weather_tools(mcp: FastMCP):
    """Register weather-related tools with the MCP server"""
    
    @mcp.tool()
    async def get_current_weather(location: str, ctx: Context) -> str:
        """Get current weather conditions for a location
        
        Args:
            location: City name or location
            
        Returns:
            Current weather information
        """
        if not WEATHER_API_KEY:
            return "Error: Weather API key not configured"
            
        try:
            # Make API request to OpenWeather
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "q": location,
                        "appid": WEATHER_API_KEY,
                        "units": "metric"  # Use metric units
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    return f"Error: API returned status code {response.status_code}"
                    
                # Parse results
                data = response.json()
                
                # Extract weather information
                weather = data.get("weather", [{}])[0]
                main = data.get("main", {})
                wind = data.get("wind", {})
                sys = data.get("sys", {})
                
                # Format results
                weather_description = weather.get("description", "Unknown").capitalize()
                temperature = main.get("temp", "Unknown")
                feels_like = main.get("feels_like", "Unknown")
                humidity = main.get("humidity", "Unknown")
                wind_speed = wind.get("speed", "Unknown")
                pressure = main.get("pressure", "Unknown")
                sunrise = sys.get("sunrise", 0)
                sunset = sys.get("sunset", 0)
                
                # Convert timestamps
                sunrise_time = datetime.fromtimestamp(sunrise).strftime("%H:%M")
                sunset_time = datetime.fromtimestamp(sunset).strftime("%H:%M")
                
                # Format response
                return (
                    f"Current weather for {location}:\n"
                    f"Condition: {weather_description}\n"
                    f"Temperature: {temperature}°C (Feels like: {feels_like}°C)\n"
                    f"Humidity: {humidity}%\n"
                    f"Wind Speed: {wind_speed} m/s\n"
                    f"Pressure: {pressure} hPa\n"
                    f"Sunrise: {sunrise_time}\n"
                    f"Sunset: {sunset_time}"
                )
                
        except Exception as e:
            return f"Error getting weather: {str(e)}"
    
    @mcp.tool()
    async def get_weather_forecast(location: str, days: int = 5, ctx: Context) -> str:
        """Get weather forecast for a location
        
        Args:
            location: City name or location
            days: Number of days to forecast (1-5)
            
        Returns:
            Weather forecast
        """
        if not WEATHER_API_KEY:
            return "Error: Weather API key not configured"
            
        # Validate days
        days = min(max(1, days), 5)
            
        try:
            # Make API request to OpenWeather
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openweathermap.org/data/2.5/forecast",
                    params={
                        "q": location,
                        "appid": WEATHER_API_KEY,
                        "units": "metric",
                        "cnt": days * 8  # 8 forecasts per day (every 3 hours)
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    return f"Error: API returned status code {response.status_code}"
                    
                # Parse results
                data = response.json()
                
                # Extract forecast information
                forecasts = data.get("list", [])
                city = data.get("city", {})
                city_name = city.get("name", location)
                
                if not forecasts:
                    return f"No forecast available for {location}"
                    
                # Group forecasts by day
                daily_forecasts = {}
                
                for forecast in forecasts:
                    # Extract date
                    timestamp = forecast.get("dt", 0)
                    date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                    time = datetime.fromtimestamp(timestamp).strftime("%H:%M")
                    
                    # Get weather information
                    weather = forecast.get("weather", [{}])[0]
                    main = forecast.get("main", {})
                    
                    # Extract details
                    weather_description = weather.get("description", "Unknown").capitalize()
                    temperature = main.get("temp", "Unknown")
                    
                    # Add to daily forecasts
                    if date not in daily_forecasts:
                        daily_forecasts[date] = []
                        
                    daily_forecasts[date].append({
                        "time": time,
                        "description": weather_description,
                        "temperature": temperature
                    })
                
                # Format results
                result = f"Weather forecast for {city_name}:\n\n"
                
                for date, forecasts in list(daily_forecasts.items())[:days]:
                    day_name = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
                    result += f"{day_name} ({date}):\n"
                    
                    for forecast in forecasts:
                        result += f"  {forecast['time']}: {forecast['temperature']}°C, {forecast['description']}\n"
                        
                    result += "\n"
                
                return result
                
        except Exception as e:
            return f"Error getting forecast: {str(e)}"
            
    @mcp.tool()
    async def get_weather_alerts(location: str, ctx: Context) -> str:
        """Get weather alerts for a location
        
        Args:
            location: City name or location
            
        Returns:
            Active weather alerts
        """
        if not WEATHER_API_KEY:
            return "Error: Weather API key not configured"
            
        try:
            # First, get coordinates for the location
            async with httpx.AsyncClient() as client:
                geo_response = await client.get(
                    "https://api.openweathermap.org/geo/1.0/direct",
                    params={
                        "q": location,
                        "limit": 1,
                        "appid": WEATHER_API_KEY
                    },
                    timeout=10.0
                )
                
                if geo_response.status_code != 200:
                    return f"Error: Geocoding API returned status code {geo_response.status_code}"
                    
                geo_data = geo_response.json()
                
                if not geo_data:
                    return f"Location not found: {location}"
                    
                # Extract coordinates
                lat = geo_data[0].get("lat")
                lon = geo_data[0].get("lon")
                
                if lat is None or lon is None:
                    return f"Could not get coordinates for location: {location}"
                    
                # Now get weather alerts
                alerts_response = await client.get(
                    "https://api.openweathermap.org/data/2.5/onecall",
                    params={
                        "lat": lat,
                        "lon": lon,
                        "exclude": "current,minutely,hourly,daily",
                        "appid": WEATHER_API_KEY
                    },
                    timeout=10.0
                )
                
                if alerts_response.status_code != 200:
                    return f"Error: Alerts API returned status code {alerts_response.status_code}"
                    
                alerts_data = alerts_response.json()
                
                # Extract alerts
                alerts = alerts_data.get("alerts", [])
                
                if not alerts:
                    return f"No active weather alerts for {location}"
                    
                # Format results
                result = f"Active weather alerts for {location}:\n\n"
                
                for i, alert in enumerate(alerts, 1):
                    event = alert.get("event", "Unknown alert")
                    sender = alert.get("sender_name", "Unknown source")
                    start = alert.get("start", 0)
                    end = alert.get("end", 0)
                    description = alert.get("description", "No description available")
                    
                    # Convert timestamps
                    start_time = datetime.fromtimestamp(start).strftime("%Y-%m-%d %H:%M")
                    end_time = datetime.fromtimestamp(end).strftime("%Y-%m-%d %H:%M")
                    
                    result += (
                        f"Alert {i}: {event}\n"
                        f"Source: {sender}\n"
                        f"Valid: {start_time} to {end_time}\n"
                        f"Description: {description}\n\n"
                    )
                
                return result
                
        except Exception as e:
            return f"Error getting weather alerts: {str(e)}"
