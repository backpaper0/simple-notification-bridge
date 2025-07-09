import os
from pathlib import Path
import time

import requests
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
    )
    discord_webhook_url: str
    event_log: str


settings = Settings()  # type: ignore


def main() -> None:
    event_log = Path(settings.event_log)
    if not event_log.exists():
        event_log.touch()
    with event_log.open(mode="r", encoding="utf-8") as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            resp = requests.post(settings.discord_webhook_url, json={"content": line})
            print(resp)


if __name__ == "__main__":
    main()
