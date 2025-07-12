import os
import time
from pathlib import Path

import redis
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
    )
    redis_host: str = "localhost"
    redis_port: int = 6379
    channel: str = "notification"
    event_log: str = "/.claude/events.log"


settings = Settings()  # type: ignore


def main() -> None:
    r = redis.Redis(host=settings.redis_host, port=settings.redis_port)
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
            r.publish(settings.channel, line)


if __name__ == "__main__":
    main()
