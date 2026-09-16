from decimal import Decimal
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    database_url: str | None = None
    database_hostname: str = 'localhost'
    database_port: int = 5432
    database_password: str = ''
    database_name: str = 'library_management'
    database_username: str = 'postgres'
    secret_key: str = Field(min_length=32)
    algorithm: Literal['HS256', 'HS384', 'HS512'] = 'HS256'
    access_token_expire_minutes: int = Field(default=60, gt=0)
    loan_days: int = Field(default=14, gt=0)
    max_active_borrowings: int = Field(default=5, gt=0)
    daily_fine: Decimal = Field(default=Decimal('10.00'), ge=0, decimal_places=2)

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    @property
    def sqlalchemy_url(self):
        return self.database_url or URL.create(
            'postgresql+psycopg2', username=self.database_username,
            password=self.database_password, host=self.database_hostname,
            port=self.database_port, database=self.database_name,
        )


settings = Settings()
