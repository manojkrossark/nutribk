from flask import Flask, request, jsonify
import psycopg2
import requests
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Google Generative AI integration
genai.configure(api_key='AIzaSyCn43FyMu0k4TpBrrXVo1KNRtPR1JuUoF4')
# Database connection setup
DATABASE_URL = os.getenv("DATABASE_URL")

# Initialize Flask app
app = Flask(__name__)


def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def get_weather_conditions(latitude, longitude):
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
        return Noneone

def get_meal_suggestions_from_genai(user_data, weather_data):
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

@app.route('/get-meal', methods=['POST'])
def get_meal():
    """API endpoint to get meal suggestion based on user mood, location, and weather."""
    user_data = request.get_json()
    mood = user_data.get("mood")
    location = user_data.get("location")
    health_goals = user_data.get("health_goals")
    dietary_restrictions = user_data.get("dietary_restrictions")
    latitude = user_data.get("latitude")
    longitude = user_data.get("longitude")

    # Get current weather for the location
    weather_data = get_weather_conditions(latitude, longitude)

    if weather_data:
        # Generate meal suggestion based on weather data and user info
        meal = get_meal_suggestions_from_genai(user_data, weather_data)
        
        # Store user data and meal suggestion in the database
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("INSERT INTO users (mood, location, last_meal_suggestion) VALUES (%s, %s, %s)", 
                       (mood, location, meal))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"meal": meal})
    else:
        return jsonify({"error": "Unable to fetch weather data"}), 500

if __name__ == "__main__":
    app.run(debug=True)
