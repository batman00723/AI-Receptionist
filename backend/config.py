from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    secret_key: SecretStr
    debug : bool

    db_name: str
    db_user: str
    db_password: SecretStr
    db_host: str
    db_port: int
    db_url: SecretStr


    langsmith_api_key: SecretStr
    langsmith_tracing: str = "true"
    langsmith_project: str 
    langsmith_endpoint: str 

    cerebras_api_key: SecretStr
    google_api_key: SecretStr

    reranker_voyage_ai_api_key: SecretStr

    resend_api_key: SecretStr
    cal_api_key: SecretStr
    groq_api_key: SecretStr

    brevo_api_key: SecretStr

    model_config= SettingsConfigDict(env_file= ".env",
                                     extra= 'ignore',
                                     case_sensitive=False)

settings= Settings()