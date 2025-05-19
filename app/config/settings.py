from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    WEATHER_API_KEY: str
    GEMINI_API_KEY: str
    PEXELS_API_KEY: str
    WEATHER_API_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"

settings = Settings()
