from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import psycopg2
import requests
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Generative AI integration
genai.configure(api_key='AIzaSyCn43FyMu0k4TpBrrXVo1KNRtPR1JuUoF4')

# Weather API
WEATHER_API_KEY = "6419738e339e4507aa8122732240910"
WEATHER_API_URL = "http://api.weatherapi.com/v1/current.json"

# PostgreSQL connection
DATABASE_URL = "postgresql://postgres.qzudlrfcsaagrxvugzot:m6vuWFRSoHj2EHZe@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

class UserData(BaseModel):
    mood: str
    location: str
    health_goals: str
    dietary_restrictions: str
    latitude: float
    longitude: float
    budget: str
    notes: str = ""
    language: Optional[str] = "english"

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def get_weather_conditions(latitude: float, longitude: float):
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
    try:
        language = user_data.get("language", "english").lower()
        language_map = {
            "tamil": "Tamil",
            "telugu": "Telugu",
            "malayalam": "Malayalam",
            "kannada": "Kannada",
            "english": "English"
        }
        target_language = language_map.get(language, "English")

        prompt = (
            f"I am feeling {user_data['mood']}, and I live in {user_data['location']}. "
            f"The current weather in {user_data['location']} is {weather_data['condition']} with a temperature of "
            f"{weather_data['temperature']}°C, wind speed of {weather_data['wind_speed']} kph, and humidity of "
            f"{weather_data['humidity']}%. "
            f"My health goals are {user_data['health_goals']} and I follow a {user_data['dietary_restrictions']} diet. "
            f"My budget for meals is {user_data['budget']}. "
        )

        if user_data.get("notes"):
            prompt += f"Additional notes from me: {user_data['notes']}. "

        prompt += (
            f"Please provide a personalized 5-day meal plan tailored to my location in {user_data['location']}, supporting "
            f"my health goals and dietary restrictions. The meals should consider the current weather, be nutritious, and "
            f"reflect local tastes. Each day should include 3 meals (Breakfast, Lunch, and Dinner), using locally sourced ingredients where possible. "
            f"Each meal should list the food items in a bullet point format and include a short note about the meal. "
            f"Ensure the meals are easy to prepare, satisfying, and aligned with my goals of {user_data['health_goals']} and my budget of {user_data['budget']}. "
            f"Format the response strictly as a JSON object using this structure: "
            f"{{"
            f"  'mealPlan': {{"
            f"    'location': 'string',"
            f"    'weather': 'string',"
            f"    'healthGoals': 'string',"
            f"    'diet': 'string',"
            f"    'budget': 'string',"
            f"    'description': 'string',"
            f"    'days': ["
            f"      {{"
            f"        'day': 'string',"
            f"        'meals': ["
            f"          {{"
            f"            'meal': 'string',"
            f"            'items': ['string', 'string'],"
            f"            'notes': 'string'"
            f"          }}"
            f"        ]"
            f"      }}"
            f"    ]"
            f"  }}"
            f"}}. "
            f"Return only the JSON without markdown formatting or extra explanation."
        )

        if target_language != "English":
            prompt += f" Translate the entire response (values only) to {target_language}. Keep field keys in English."

        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        response = model.generate_content(prompt)

        if response and response.text:
            cleaned_text = response.text.strip()
            # Attempt to extract JSON by identifying first/last braces
            start = cleaned_text.find('{')
            end = cleaned_text.rfind('}') + 1
            json_part = cleaned_text[start:end]
            parsed_json = json.loads(json_part)
            return parsed_json
        else:
            raise ValueError("Empty response from Gemini")

    except Exception as e:
        print(f"Meal suggestion error: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching meal suggestion: {str(e)}")

@app.post("/get-meal")
async def get_meal(user_data: UserData):
    weather_data = get_weather_conditions(user_data.latitude, user_data.longitude)

    if weather_data:
        meal_json = get_meal_suggestions_from_genai(user_data.model_dump(), weather_data)
        return {
            "meal": meal_json,
            "weather": weather_data
        }
    else:
        raise HTTPException(status_code=500, detail="Unable to fetch weather data")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
