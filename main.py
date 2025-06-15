import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
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
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Notification Bridge</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background-color: white;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                margin-bottom: 20px;
            }
            .status {
                padding: 10px;
                border-radius: 4px;
                margin-bottom: 20px;
                font-weight: 500;
            }
            .status.connected {
                background-color: #d4edda;
                color: #155724;
            }
            .status.disconnected {
                background-color: #f8d7da;
                color: #721c24;
            }
            .status.permission-denied {
                background-color: #fff3cd;
                color: #856404;
            }
            button {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #0056b3;
            }
            button:disabled {
                background-color: #ccc;
                cursor: not-allowed;
            }
            .log {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 10px;
                margin-top: 20px;
                max-height: 300px;
                overflow-y: auto;
            }
            .log-entry {
                margin-bottom: 5px;
                font-family: monospace;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Notification Bridge</h1>
            <div id="status" class="status disconnected">
                SSE接続: 切断中
            </div>
            <button id="requestPermission" onclick="requestNotificationPermission()">
                通知の許可をリクエスト
            </button>
            <div class="log" id="log">
                <div class="log-entry">ログ:</div>
            </div>
        </div>
        
        <script>
            let eventSource;
            let notificationPermission = Notification.permission;
            
            function addLog(message) {
                const log = document.getElementById('log');
                const entry = document.createElement('div');
                entry.className = 'log-entry';
                const timestamp = new Date().toLocaleTimeString();
                entry.textContent = `[${timestamp}] ${message}`;
                log.appendChild(entry);
                log.scrollTop = log.scrollHeight;
            }
            
            function updateStatus(connected) {
                const status = document.getElementById('status');
                if (connected) {
                    status.className = 'status connected';
                    status.textContent = 'SSE接続: 接続中';
                } else {
                    status.className = 'status disconnected';
                    status.textContent = 'SSE接続: 切断中';
                }
            }
            
            function updatePermissionStatus() {
                const button = document.getElementById('requestPermission');
                notificationPermission = Notification.permission;
                
                if (notificationPermission === 'granted') {
                    button.textContent = '通知許可済み';
                    button.disabled = true;
                    addLog('通知が許可されました');
                } else if (notificationPermission === 'denied') {
                    button.textContent = '通知が拒否されました';
                    button.disabled = true;
                    addLog('通知が拒否されました');
                } else {
                    button.textContent = '通知の許可をリクエスト';
                    button.disabled = false;
                }
            }
            
            async function requestNotificationPermission() {
                try {
                    const permission = await Notification.requestPermission();
                    updatePermissionStatus();
                } catch (error) {
                    addLog('通知許可のリクエストに失敗しました: ' + error.message);
                }
            }
            
            function showNotification(message) {
                if (notificationPermission === 'granted') {
                    const notification = new Notification(message);
                    
                    notification.onclick = function() {
                        window.focus();
                        notification.close();
                    };
                    
                    addLog('通知を表示しました: ' + message);
                } else {
                    addLog('通知権限がないため表示できません: ' + message);
                }
            }
            
            function connectSSE() {
                eventSource = new EventSource('/notifications');
                
                eventSource.onopen = function() {
                    updateStatus(true);
                    addLog('SSE接続が確立されました');
                };
                
                eventSource.onmessage = function(event) {
                    showNotification(event.data);
                };
                
                eventSource.onerror = function(error) {
                    updateStatus(false);
                    addLog('SSE接続エラーが発生しました');
                    eventSource.close();
                    
                    setTimeout(() => {
                        addLog('再接続を試みています...');
                        connectSSE();
                    }, 5000);
                };
            }
            
            window.addEventListener('DOMContentLoaded', function() {
                updatePermissionStatus();
                connectSSE();
            });
            
            window.addEventListener('beforeunload', function() {
                if (eventSource) {
                    eventSource.close();
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


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
