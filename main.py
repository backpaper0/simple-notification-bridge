import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from sse_starlette.sse import EventSourceResponse


class Settings(BaseSettings):
    notification_title: str = "DevContainer Notification"
    server_host: str = "0.0.0.0"
    server_port: int = 8000

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
