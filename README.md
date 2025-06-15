# Simple Notification Bridge

## 概要

ローカルホスト内で通知を行うための簡易的な仕組みを提供する Web アプリケーションです。
主なユースケースは devcontainer 内で実行したタスクが完了したときに通知することです。

## アーキテクチャ

システム構成。

```mermaid
flowchart LR
    subgraph DockerNetwork[Docker（ネットワークスタックを共有）]
        WebApp[Webアプリ]
        DevContainer[VSCode DevContainer]
    end

    subgraph Host[ホスト]
        Browser[Webブラウザ<br>（SSEクライアント）]
    end

    DevContainer -->|POST /notify| WebApp
    Browser -->|GET /notifications<br>（SSE接続）| WebApp
    WebApp -->|SSEでイベント送信| Browser
```

通知の処理シーケンス。

```mermaid
sequenceDiagram
    participant DevContainer as VSCode DevContainer
    participant WebApp as Webアプリ
    participant Browser as Webブラウザ

    DevContainer->>WebApp: POST /notify
    WebApp->>WebApp: 通知イベント生成
    WebApp-->>Browser: Server-Sent Events で通知イベントを送信
    Browser->>Browser: Web Notifications APIで通知を表示
```

## Web アプリ

### 技術スタック

- Python
- FastAPI
- pydantic-settings

### エンドポイント

- `GET /index.html`
  - 画面を開くと Web Notifications API の権限設定を行い、`GET /notifications`を使用して Server-Sent Events の接続を確立する
  - Server-Sent Events を通じて通知イベントを受け取ると Web Notifications API を用いて通知を行う
- `POST /notify`
  - 接続済みの Server-Sent Events セッションに対して通知イベントを送信する
- `GET /notifications`
  - Server-Sent Events の接続を確立する

### 設定

- 設定は`.env`ファイルで行う
- 設定する値は次の通り
  - 通知のタイトル

## コンテナイメージのビルド

次のコマンドでコンテナイメージをビルドします。

```bash
docker build -t simple-notification-bridge .
```

## devcontainer で Claude Code を動かす場合の使い方

`.devcontainer/devcontainer.json`へポート公開の設定を追加します。

```json
{
  "runArgs": [
    "--publish=8000:8000"
  ]
}
```

devcontainerのコンテナーIDを調べて、ネットワークスタックを共有させてWebアプリを起動します。

```bash
docker run -d --network container:<コンテナーID> simple-notification-bridge
```

http://localhost:8000 をWebブラウザで開きます。

作業が完了すると通知を行うよう`CLAUDE.md`へ通知ルールを記載します。

以上で Claude Code が作業を完了すると通知されます。
