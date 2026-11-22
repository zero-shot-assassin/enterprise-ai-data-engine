from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    s3_endpoint: str = "rustfs:9000"
    s3_access_key: str = "rustfsadmin"
    s3_secret_key: str
    s3_bucket_raw: str = "raw-documents"
    redis_url: str = "redis://redis:6379/0"
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333

settings = Settings() # type: ignore