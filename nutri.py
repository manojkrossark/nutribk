from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg2
import requests
import os
from dotenv import load_dotenv
import google.generativeai as genai
import uvicorn

# Load environment variables
load_dotenv()

# Google Generative AI integration
genai.configure(api_key='AIzaSyCn43FyMu0k4TpBrrXVo1KNRtPR1JuUoF4')

# OpenWeatherMap API setup
WEATHER_API_KEY = "6419738e339e4507aa8122732240910"
WEATHER_API_URL = "http://api.weatherapi.com/v1/current.json"

# Database connection setup
DATABASE_URL = "postgresql://postgres.qzudlrfcsaagrxvugzot:m6vuWFRSoHj2EHZe@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

# Initialize FastAPI app
app = FastAPI()


class UserData(BaseModel):
    mood: str
    location: str
    health_goals: str
    dietary_restrictions: str
    latitude: float
    longitude: float


def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def get_weather_conditions(latitude: float, longitude: float):
    """Fetch real-time weather data for the location."""
    try:
        url = f"{WEATHER_API_URL}?key={WEATHER_API_KEY}&q={latitude},{longitude}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return {
            "temperature": data["current"]["temp_c"],
            "condition": data["current"]["condition"]["text"],
            "wind_speed": data["current"]["wind_kph"],
            "humidity": data["current"]["humidity"],
            "precipitation": data["current"].get("precip_mm", 0)
        }
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None


def get_meal_suggestions_from_genai(user_data: dict, weather_data: dict):
    """Get meal suggestions from Google Generative AI using generateContent."""
    try:
        prompt = f"I am feeling {user_data['mood']}, and I live in {user_data['location']}. The current weather is {weather_data['condition']} with a temperature of {weather_data['temperature']}°C, wind speed of {weather_data['wind_speed']} kph, and humidity of {weather_data['humidity']}%. My health goals are {user_data['health_goals']} and I have the following dietary restrictions: {user_data['dietary_restrictions']}."

        response = genai.generateContent(
            model="models/text-bison-001",  # Specify model
            prompt=prompt,
            temperature=0.7
        )

        return response['candidates'][0]['content'] if 'candidates' in response else "Sorry, I couldn't suggest a meal at the moment."
    
    except Exception as e:
        return f"Error fetching meal suggestion: {str(e)}"


@app.post("/get-meal")
async def get_meal(user_data: UserData):
    """API endpoint to get meal suggestion based on user mood, location, and weather."""
    latitude = user_data.latitude
    longitude = user_data.longitude

    # Get current weather for the location
    weather_data = get_weather_conditions(latitude, longitude)

    if weather_data:
        # Generate meal suggestion based on weather data and user info
        meal = get_meal_suggestions_from_genai(user_data.dict(), weather_data)
        
        # Store user data and meal suggestion in the database
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (mood, location, last_meal_suggestion) VALUES (%s, %s, %s)",
            (user_data.mood, user_data.location, meal),
        )
        conn.commit()

        cursor.close()
        conn.close()

        return {"meal": meal}
    else:
        raise HTTPException(status_code=500, detail="Unable to fetch weather data")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
