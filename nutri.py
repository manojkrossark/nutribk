import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import psycopg2
import requests
import os
from dotenv import load_dotenv
import re
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

# OpenWeatherMap API setup
WEATHER_API_KEY = "6419738e339e4507aa8122732240910"
WEATHER_API_URL = "http://api.weatherapi.com/v1/current.json"
PEXELS_API_KEY = "j0PIrrp6gOhv1UBHbZTTBSrDOekAdibiRI4ti6vrgLgYxZNTu2KZY60e"

# Database connection setup
DATABASE_URL = "postgresql://postgres.qzudlrfcsaagrxvugzot:m6vuWFRSoHj2EHZe@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

class UserData(BaseModel):
    mood: str
    location: str
    health_goals: str
    dietary_restrictions: str
    latitude: float
    longitude: float
    language:str
    budget: str
    notes: str = ""   


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

# def get_meal_suggestions_from_genai(user_data: dict, weather_data: dict):
#     """Get meal suggestions from Google Generative AI using Gemini 1.5 Flash, formatted for frontend and localized by language."""
#     try:
#         # Language mapping
#         language = user_data.get("language", "english").lower()
#         language_map = {
#             "tamil": "Tamil",
#             "telugu": "Telugu",
#             "malayalam": "Malayalam",
#             "kanadam": "Kannada",
#             "english": "English"
#         }
#         target_language = language_map.get(language, "English")

#         # Prompt construction
#         prompt = (
#             f"I am feeling {user_data['mood']}, and I live in {user_data['location']}. "
#             f"The current weather in {user_data['location']} is {weather_data['condition']} with a temperature of "
#             f"{weather_data['temperature']}°C, wind speed of {weather_data['wind_speed']} kph, and humidity of "
#             f"{weather_data['humidity']}%. "
#             f"My health goals are {user_data['health_goals']} and I follow a {user_data['dietary_restrictions']} diet. "
#             f"My budget for meals is {user_data['budget']}. "
#         )

#         if user_data.get("notes"):
#             prompt += f"Additional notes from me: {user_data['notes']}. "

#         prompt += (
#             "Please provide a personalized 5-day meal plan tailored to my location, supporting my health goals and dietary restrictions. "
#             "The meals should consider the current weather, be nutritious, and reflect local tastes. Each day should include 3 meals "
#             "(Breakfast, Lunch, and Dinner), using locally sourced ingredients where possible. Each meal should list the food items "
#             "in a bullet point format and include a short note. Ensure meals are easy to prepare and budget-friendly. "
#             "Format the response strictly as a JSON object using this structure: "
#             "{"
#             "  'mealPlan': {"
#             "    'location': 'string',"
#             "    'weather': 'string',"
#             "    'healthGoals': 'string',"
#             "    'diet': 'string',"
#             "    'budget': 'string',"
#             "    'description': 'string',"
#             "    'days': ["
#             "      {"
#             "        'day': 'string',"
#             "        'meals': ["
#             "          {"
#             "            'meal': 'string',"
#             "            'items': ['string'],"
#             "            'notes': 'string'"
#             "          }"
#             "        ]"
#             "      }"
#             "    ]"
#             "  }"
#             "}. Return only the JSON without markdown formatting or extra explanation."
#         )

#         if target_language != "English":
#             prompt += f" Translate only the values to {target_language}, keeping field keys in English."

#         # Generate content
#         model = genai.GenerativeModel("gemini-1.5-flash")
#         response = model.generate_content(prompt)

#         if not response or not response.text:
#             return {"error": "Empty response from Gemini."}

#         cleaned_text = response.text.strip()
#         cleaned_text = cleaned_text.replace("```json", "").replace("```", "").strip()

#         # SAFE JSON Extraction
#         # Find the first "{" and last "}" to safely extract JSON
#         start_idx = cleaned_text.find('{')
#         end_idx = cleaned_text.rfind('}') + 1

#         if start_idx == -1 or end_idx == -1:
#             return {"error": "No JSON object found in Gemini response", "raw": cleaned_text}

#         json_text = cleaned_text[start_idx:end_idx]

#         try:
#             parsed_json = json.loads(json_text)
#             return parsed_json
#         except json.JSONDecodeError as e:
#             return {
#                 "error": f"JSON decode failed: {str(e)}",
#                 "raw": json_text
#             }

#     except Exception as e:
#         return {"error": f"Unhandled exception: {str(e)}"}
    
def get_pexels_image_url(query: str, api_key: str) -> str:
    headers = {
        "Authorization": api_key
    }
    params = {
        "query": f"{query} food meal dish",
        "per_page": 5  # Get more results to choose a better one
    }
    response = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        photos = data.get("photos", [])
        if photos:
            # Prefer landscape orientation or images with wider aspect ratio
            best_photo = sorted(
                photos,
                key=lambda p: p.get("width", 0) / max(p.get("height", 1), 1),
                reverse=True
            )[0]
            return best_photo["src"]["large"]
    return ""  # fallback


def get_meal_suggestions_from_genai(user_data: dict, weather_data: dict):
    """Get meal suggestions from Google Generative AI using Gemini 1.5 Flash, with accurate food images from Pexels."""
    try:
        # Language mapping
        language = user_data.get("language", "english").lower()
        language_map = {
            "tamil": "Tamil",
            "telugu": "Telugu",
            "malayalam": "Malayalam",
            "kanadam": "Kannada",
            "english": "English"
        }
        target_language = language_map.get(language, "English")

        # Construct prompt
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
            "Please provide a personalized 5-day meal plan tailored to my location, supporting my health goals and dietary restrictions. "
            "The meals should consider the current weather, be nutritious, and reflect local tastes. Each day should include 3 meals "
            "(Breakfast, Lunch, and Dinner), using locally sourced ingredients where possible. Each meal should list multiple food items. "
            "Each item should include a 'name'. Do not include any imageUrl or external links. "
            "Include a short 'notes' field per meal. Ensure meals are easy to prepare and budget-friendly. "
            "Format the response strictly as a JSON object using this structure: "
            "{"
            "  'mealPlan': {"
            "    'location': 'string',"
            "    'weather': 'string',"
            "    'healthGoals': 'string',"
            "    'diet': 'string',"
            "    'budget': 'string',"
            "    'description': 'string',"
            "    'days': ["
            "      {"
            "        'day': 'string',"
            "        'meals': ["
            "          {"
            "            'meal': 'string',"
            "            'items': [ { 'name': 'string' } ],"
            "            'notes': 'string'"
            "          }"
            "        ]"
            "      }"
            "    ]"
            "  }"
            "}. Return only the JSON without markdown formatting or extra explanation."
        )

        if target_language != "English":
            prompt += f" Translate only the values to {target_language}, keeping the field keys in English."

        # Generate content
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        if not response or not response.text:
            return {"error": "Empty response from Gemini."}

        cleaned_text = response.text.strip()
        cleaned_text = cleaned_text.replace("```json", "").replace("```", "").strip()

        # Extract JSON from response
        start_idx = cleaned_text.find('{')
        end_idx = cleaned_text.rfind('}') + 1

        if start_idx == -1 or end_idx == -1:
            return {"error": "No JSON object found in Gemini response", "raw": cleaned_text}

        json_text = cleaned_text[start_idx:end_idx]

        try:
            parsed_json = json.loads(json_text)

            # Inject image URLs using Pexels
            for day in parsed_json.get("mealPlan", {}).get("days", []):
                for meal in day.get("meals", []):
                    for item in meal.get("items", []):
                        item_name = item.get("name", "")
                        image_url = get_pexels_image_url(item_name, PEXELS_API_KEY)
                        item["imageUrl"] = image_url

            return parsed_json

        except json.JSONDecodeError as e:
            return {"error": f"JSON decode failed: {str(e)}", "raw": json_text}

    except Exception as e:
        return {"error": f"Unhandled exception: {str(e)}"}

@app.post("/get-meal")
async def get_meal(user_data: UserData):
    """API endpoint to get meal suggestion based on user mood, location, weather, and budget."""
    latitude = user_data.latitude
    longitude = user_data.longitude

    # Get current weather for the location
    weather_data = get_weather_conditions(latitude, longitude)

    if weather_data:
        # Generate meal suggestion based on weather data and user info, including budget
        meal = get_meal_suggestions_from_genai(user_data.model_dump(), weather_data)
        
        # Store user data and meal suggestion in the database (if needed)
        # conn = get_db_connection()
        # cursor = conn.cursor()

        # cursor.execute(
        #     "INSERT INTO users (mood, location, last_meal_suggestion) VALUES (%s, %s, %s)",
        #     (user_data.mood, user_data.location, meal),
        # )
        # conn.commit()

        # cursor.close()
        # conn.close()

        return {
            "meal": meal,
            "weather": {
                "temperature": weather_data["temperature"],
                "condition": weather_data["condition"],
                "wind_speed": weather_data["wind_speed"],
                "humidity": weather_data["humidity"],
                "precipitation": weather_data["precipitation"]
            }
        }
    else:
        raise HTTPException(status_code=500, detail="Unable to fetch weather data")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
