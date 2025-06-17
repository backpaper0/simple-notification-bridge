import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    Message,
    MessagingApi,
    PushMessageRequest,
)
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from sse_starlette.sse import EventSourceResponse


class Settings(BaseSettings):
    notification_title: str = "DevContainer Notification"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    line_channel_access_token: str | None = None
    line_push_to: str | None = None

    class Config:
        env_file = ".env"


class NotificationRequest(BaseModel):
    message: str


class NotificationManager:
    def __init__(self):
        self.clients: list[asyncio.Queue] = []

    async def add_client(self) -> AsyncGenerator[dict, None]:
        queue: asyncio.Queue = asyncio.Queue()
        self.clients.append(queue)
        try:
            while True:
                data = await queue.get()
                yield data
        finally:
            self.clients.remove(queue)

    async def notify_all(self, message: str):
        notification_data = {
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

        for client in self.clients:
            await client.put(notification_data)

        if settings.line_push_to is not None:
            configuration = Configuration(
                access_token=settings.line_channel_access_token
            )
            with ApiClient(configuration) as api_client:
                messaging_api = MessagingApi(api_client)
                messaging_api.push_message(
                    PushMessageRequest(
                        to=settings.line_push_to,
                        messages=[Message.from_dict({"type": "text", "text": message})],
                        notificationDisabled=None,
                        customAggregationUnits=None,
                    )
                )


notification_manager = NotificationManager()
settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
@app.get("/index.html")
async def get_index():
    return FileResponse("index.html")


@app.get("/notifications")
async def get_notifications(request: Request):
    async def event_generator():
        async for notification in notification_manager.add_client():
            yield {
                "event": "message",
                "data": notification["message"],
            }

    return EventSourceResponse(event_generator())


@app.post("/notify")
async def post_notify(
    notification: NotificationRequest = NotificationRequest(
        message=settings.notification_title
    ),
):
    await notification_manager.notify_all(notification.message)
    return {"status": "ok", "message": "Notification sent"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.server_host, port=settings.server_port)
