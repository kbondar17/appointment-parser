from pathlib import Path

from pydantic import BaseSettings, validator


class Configs(BaseSettings):
    LOGGING_LEVEL: str = 'ERROR'
    MAIN_LOG_FILE:str = 'logs/main.json'

    @validator('MAIN_LOG_FILE')
    def get_abs_path(cls, v, values):
        return Path(v).absolute()

configs = Configs()

 