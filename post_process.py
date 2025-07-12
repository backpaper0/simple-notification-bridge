import subprocess

import redis
import requests
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
    )
    redis_host: str = "localhost"
    redis_port: int = 16379
    channel: str = "notification"
    discord_webhook_url: str
    git_workspace_path: str
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"


settings = Settings()  # type: ignore


def main() -> None:
    r = redis.Redis(host=settings.redis_host, port=settings.redis_port)
    pubsub = r.pubsub()
    pubsub.subscribe(settings.channel)

    for message in pubsub.listen():
        if message["type"] == "message":
            print(message)

            # コードの差分から変更点を要約する
            subprocess.run(["git", "-C", settings.git_workspace_path, "add", "-A"])
            git_diff_result = subprocess.run(
                ["git", "-C", settings.git_workspace_path, "diff", "--cached"],
                capture_output=True,
                text=True,
            )

            prompt = {
                "model": settings.ollama_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "与えられた git diff の内容を読んでコミットメッセージを書いてください。コミットメッセージのみを出力すること。",
                    },
                    {
                        "role": "user",
                        "content": git_diff_result.stdout,
                    },
                ],
                "stream": False,
            }
            resp = requests.post(settings.ollama_base_url + "/api/chat", json=prompt)
            commit_message = resp.json()["message"]["content"]

            # Discordへ通知
            requests.post(
                settings.discord_webhook_url,
                json={"content": commit_message},
            )

            # git commit
            subprocess.run(
                [
                    "git",
                    "-C",
                    settings.git_workspace_path,
                    "commit",
                    "-m",
                    commit_message,
                ]
            )


if __name__ == "__main__":
    main()
