# Simple Notification Bridge

## 概要

ファイルを監視して新しい書き込みを検知したらRedisへpublishするだけのシンプルなアプリケーションです。
主なユースケースは devcontainer 内で実行したClaude Codeの処理が完了したときに通知やコミットなどの後続処理を行うことです。

## アーキテクチャ

システム構成。

```mermaid
flowchart TB
    subgraph "devcontainer"
        CC[Claude Code]
        SH[Stop Hook]
        LOG[ログファイル]
    end
    
    subgraph "Docker Container 1"
        PY1[Python App<br/>ファイル監視]
    end
    
    subgraph "Docker Container 2"
        REDIS[(Redis)]
    end
    
    PY2[Python App<br/>サブスクライバ]
    DISCORD[Discord]
    GIT[Gitリポジトリ]
    
    CC -->|処理完了| SH
    SH -->|ログ書き出し| LOG
    LOG -->|ファイル変更検知| PY1
    PY1 -->|publish| REDIS
    REDIS -->|subscribe| PY2
    PY2 -->|通知| DISCORD
    PY2 -->|commit| GIT
    
    style CC fill:#e1f5fe
    style SH fill:#f3e5f5
    style LOG fill:#fff3e0
    style PY1 fill:#e8f5e8
    style PY2 fill:#e8f5e8
    style REDIS fill:#ffebee
    style DISCORD fill:#e3f2fd
    style GIT fill:#f1f8e9
```

## 使い方

devcontainer で Claude Code を動かす場合を想定しています。

Claude Code の [Stop hook](https://docs.anthropic.com/en/docs/claude-code/hooks#stop) を使用して `~/.claude/events.log` にログを書き込みます。

Stop hook の設定例：

```bash
jq -r '"\(.)"' >> ~/.claude/events.log
```

Redisを起動します。

```bash
docker run -d --name redis -p 16379:6379 redis
```

Simple Notification Bridge は `claude-code-config` をマウントして `events.log` を監視します：

```bash
docker run -d --name snb --network container:redis -v claude-code-config:/.claude:ro ghcr.io/backpaper0/simple-notification-bridge:v3
```

Claude Code のタスクが完了すると Stop hook が実行され、Redisへメッセージがpublishされます。

メッセージをsubscribeして通知やコミットを行いたい場合は`post_process.py`を動かしてください。

```bash
uv run post_process.py
```
