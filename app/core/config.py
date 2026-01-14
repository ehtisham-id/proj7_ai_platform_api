from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    env: str = "development"
    app_name: str = "AI Platform API"
    app_description: str
    app_version: str
    
    #PostgreSQL settings
    postgres_host: str
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_port: int
    
    #MongoDB settings
    mongo_uri: str
    
    class Config:
        env_file = ".env"
        extra = "ignore" 

settings = Settings()