import json
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from app.config.settings import settings
from app.db.database import get_db_connection

router = APIRouter(prefix="/meal", tags=["meal"])

class UserData(BaseModel):
    mood: str
    location: str
    health_goals: str
    dietary_restrictions: str
    latitude: float
    longitude: float
    language: str
    budget: str
    notes: str = ""

def get_weather_conditions(latitude: float, longitude: float):
    try:
        url = f"{settings.WEATHER_API_URL}?key={settings.WEATHER_API_KEY}&q={latitude},{longitude}"
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

def get_pexels_image_url(query: str) -> str:
    headers = {
        "Authorization": settings.PEXELS_API_KEY
    }
    params = {
        "query": f"{query} food meal dish",
        "per_page": 5
    }
    response = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        photos = data.get("photos", [])
        if photos:
            best_photo = sorted(
                photos,
                key=lambda p: p.get("width", 0) / max(p.get("height", 1), 1),
                reverse=True
            )[0]
            return best_photo["src"]["large"]
    return ""

def get_meal_suggestions_from_genai(user_data: dict, weather_data: dict):
    try:
        language = user_data.get("language", "english").lower()
        language_map = {
            "tamil": "Tamil",
            "telugu": "Telugu",
            "malayalam": "Malayalam",
            "kanadam": "Kannada",
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
            "Please provide a personalized 7-day meal plan tailored to my location, supporting my health goals and dietary restrictions. "
            "The meals should consider the current weather, be nutritious, and reflect local tastes. Each day should include 3 meals "
            "(Breakfast, Lunch, and Dinner), using locally sourced ingredients where possible. Each meal should list multiple food items. "
            "Each item should include a 'name'. Do not include any imageUrl or external links. "
            "Include a short 'notes' field per meal. Ensure meals are easy to prepare and budget-friendly. "
            "Format the response strictly as a JSON object using this structure: {...}"
        )

        if target_language != "English":
            prompt += f" Translate only the values to {target_language}, keeping the field keys in English."

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        if not response or not response.text:
            return {"error": "Empty response from Gemini."}

        cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()

        start_idx = cleaned_text.find('{')
        end_idx = cleaned_text.rfind('}') + 1

        if start_idx == -1 or end_idx == -1:
            return {"error": "No JSON object found in Gemini response", "raw": cleaned_text}

        json_text = cleaned_text[start_idx:end_idx]

        parsed_json = json.loads(json_text)

        for day in parsed_json.get("mealPlan", {}).get("days", []):
            for meal in day.get("meals", []):
                for item in meal.get("items", []):
                    item_name = item.get("name", "")
                    image_url = get_pexels_image_url(item_name)
                    item["imageUrl"] = image_url

        return parsed_json

    except Exception as e:
        return {"error": f"Unhandled exception: {str(e)}"}

@router.post("/get-meal")
async def get_meal(user_data: UserData):
    weather_data = get_weather_conditions(user_data.latitude, user_data.longitude)

    if weather_data:
        meal = get_meal_suggestions_from_genai(user_data.model_dump(), weather_data)
        return {
            "meal": meal,
            "weather": weather_data
        }
    else:
        raise HTTPException(status_code=500, detail="Unable to fetch weather data")
