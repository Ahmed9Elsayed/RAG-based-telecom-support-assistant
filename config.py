from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    groq_api_key: str
    n8n_webhook_url: str = ""
    data_path: str = "./data"
    hf_token: str = "" # Added this for your Hugging Face downloads!
    
    # This tells pydantic to read these values from your .env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# We create a single instance of this class to import into other files
settings = Settings()