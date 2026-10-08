from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AEREO Bulk Certificate Generator"
    database_url: str = "sqlite:///./certificate_generator.db"
    certificate_output_dir: str = "generated_certificates"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
