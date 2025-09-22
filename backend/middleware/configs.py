import os
from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Database
    mysql_user: str = os.getenv("MYSQL_USER")
    mysql_password: str = os.getenv("MYSQL_PASSWORD")
    mysql_host: str = os.getenv("MYSQL_HOST")
    mysql_port: str = os.getenv("MYSQL_PORT")
    mysql_database: str = os.getenv("MYSQL_DATABASE")

    # Security
    secret_key: str = os.getenv("SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # LLM Models
    ollama_models: list = ["llama2", "mistral", "gemma3"]
    default_ollama_model: str = "gemma3"
    
    # File Upload
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    #allowed_file_types: list = [".csv", ".xlsx", ".xls", ".ofx"]
    allowed_file_types: list = [".csv"]
    
    class Config:
        env_file = ".env"

settings = Settings()