# チョコTUBE - YouTube視聴サイト (日本語版)

## プロジェクト概要

チョコTUBEは、Flask/Jinja2ベースのYouTube視聴Webアプリケーションです。複数のAPIソースを統合し、動画検索、視聴、チャンネル情報表示機能を提供します。

## 技術スタック

- **バックエンド**: Flask (Python)
- **テンプレートエンジン**: Jinja2
- **API**: Invidious API, YouTube Data API v3, EDU Video API
- **フロントエンド**: HTML, CSS, JavaScript
- **動画再生**: HLS.js, YouTube埋め込み

## 主な機能

### 1. 動画検索・表示
- サムネイル、タイトル、チャンネル名、再生回数、投稿日時を表示
- 検索候補のオートコンプリート
- ページネーション対応

### 2. 複数の再生モード
- ストリーム再生 (`/watch`)
- 高画質再生 (`/w`)
- 埋め込み再生 - nocookie (`/ume`)
- Education再生 (`/edu`)

### 3. チャンネル情報
- チャンネルバナー、アイコン表示
- チャンネル登録者数
- 最新の動画一覧
- チャンネル説明

### 4. ライト/ダークモード
- ワンクリックでテーマ切り替え
- Cookie保存でセッション間で設定を維持

### 5. プレイヤー機能
- 画質選択セレクター
- ループ再生
- 自動次動画再生
- キーボードショートカット (Space/K で再生/一時停止)

## ファイル構造

```
├── app.py              # メインFlaskアプリケーション
├── templates/
│   ├── base.html       # ベーステンプレート（テーマ切り替え含む）
│   ├── index.html      # ホームページ（トレンド動画）
│   ├── search.html     # 検索結果ページ
│   ├── watch.html      # 動画再生ページ
│   └── channel.html    # チャンネルページ
├── static/
│   ├── style.css       # スタイルシート（ライト/ダーク対応）
│   └── script.js       # フロントエンドスクリプト
├── requirements.txt    # Python依存関係
└── replit.md           # このファイル
```

## 環境変数

| 変数名 | 説明 | 必須 |
| --- | --- | --- |
| `YOUTUBE_API_KEY` | Google YouTube Data API v3キー | 任意（なくてもInvidious APIで動作） |

## 開発メモ

### 2025-11-29
- choco-tube-bateリポジトリをベースに作成
  - 埋め込み機能 (nocookie, education)
  - 高画質再生機能 (adaptiveFormats対応)
  - チャンネル情報取得 (バナー、登録者数等)
  - 検索結果にサムネイル・タイトル・チャンネル情報を表示
- ライト/ダークモード切り替え機能を実装
- 再生モード選択機能を追加

### API情報

- Invidious API: 複数インスタンスからフォールバック
- 高画質ストリーム: webmコンテナ、1080p/720p優先
- 音声ストリーム: m4a AUDIO_QUALITY_MEDIUM

# チョコTube - YouTube Alternative Frontend

## Overview

チョコTube is a privacy-focused YouTube frontend application built with Flask. It provides an alternative interface for watching YouTube videos with multiple playback modes, search functionality, and channel browsing. The application features a modern dark/light theme UI with Japanese localization and emphasizes privacy by proxying requests through various services.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Technology Stack**: Vanilla JavaScript, HTML5, CSS3 with custom properties for theming

**Design Pattern**: Server-side rendering with progressive enhancement
- Templates use Jinja2 for server-side HTML generation
- Client-side JavaScript handles theme toggling, search suggestions, and dynamic interactions
- CSS custom properties enable seamless light/dark theme switching
- Responsive design approach without framework dependencies

**Rationale**: Server-side rendering provides faster initial page loads and better SEO while maintaining simplicity. The vanilla JS approach avoids framework overhead for this relatively simple UI.

### Backend Architecture

**Framework**: Flask (Python web microframework)

**Request Handling Strategy**: Connection pooling with retry logic
- Custom session with HTTPAdapter configured for connection reuse (20 connections)
- Automatic retry on server errors (500-504 status codes)
- Backoff strategy to handle temporary failures gracefully

**Caching Strategy**: In-memory caching with timestamp-based invalidation
- Educational video parameters cached to reduce API calls
- Trending videos cached to minimize external requests
- Thumbnail proxy cache to reduce bandwidth
- LRU cache decorator used for frequently accessed data

**Rationale**: In-memory caching is simple and effective for single-instance deployment. The retry strategy ensures resilience against temporary service disruptions.

### Video Playback Modes

**Multi-source fallback architecture**: Four distinct playback modes
1. **Stream mode** (default): Direct streaming via proxy API
2. **High quality mode**: WebM format for better quality
3. **Embed mode**: YouTube nocookie embed iframe
4. **Education mode**: Custom educational video API integration

**Fallback chain**: Application attempts multiple sources in order until successful
- Primary stream URL → M3U8 playlist → Embed fallback
- HLS.js library handles adaptive streaming for M3U8 playlists

**Rationale**: Multiple playback modes ensure video availability even when specific sources fail. The fallback mechanism maximizes reliability.

### Data Sources & Integration

**Primary APIs**:
- **Invidious instances**: Privacy-respecting YouTube API alternatives (9 instances with rotation)
- **Educational video API**: Custom backend for educational content
- **Stream proxy APIs**: YTDL-based services for direct video streaming
- **YouTube Data API**: Optional direct YouTube API integration

**Instance rotation**: Random selection from multiple Invidious servers
- Distributes load across instances
- Provides redundancy if specific instances are down
- User-Agent rotation to avoid rate limiting

**Rationale**: Multiple Invidious instances provide redundancy and avoid single points of failure. Privacy is maintained by not directly contacting YouTube servers.

### Routing Structure

**Core routes**:
- `/` - Home page with trending videos
- `/search` - Search results with video/channel filtering
- `/watch`, `/w`, `/ume`, `/edu` - Different video player modes
- `/channel/<id>` - Channel information and videos
- `/thumbnail` - Proxy endpoint for video thumbnails
- `/api/*` - JSON endpoints for AJAX requests (suggestions, search)

**Design pattern**: RESTful routing with mode-based player selection
- Query parameter `vc` determines playback mode
- Consistent URL structure across different modes

## External Dependencies

### Third-party Services

1. **Invidious Network**
   - Purpose: Privacy-respecting YouTube API proxy
   - Instances: 9 public instances with automatic rotation
   - Endpoints: Video metadata, search, trending, channel data
   - Fallback: Multiple instances ensure high availability

2. **YTDL Stream Service** (ytdl-0et1.onrender.com)
   - Purpose: Direct video stream extraction
   - Endpoints: `/stream/` for direct playback, `/m3u8/` for HLS playlists
   - Format: Returns streamable URLs and M3U8 manifests

3. **Educational Video API** (siawaseok.duckdns.org)
   - Purpose: Custom educational content integration
   - Configuration: External JSON config from GitHub repository
   - Format: Custom video metadata and streaming URLs

4. **YouTube Data API v3**
   - Purpose: Optional direct API access (requires API key)
   - Usage: Search and video metadata when enabled
   - Environment variable: `YOUTUBE_API_KEY`

### Frontend Libraries

1. **HLS.js** (v1.4.12)
   - Purpose: HTTP Live Streaming (HLS) support in browsers
   - Usage: M3U8 playlist playback for adaptive streaming
   - CDN delivery for reliability

2. **Google Fonts**
   - Font: Noto Sans JP (Japanese language support)
   - Weights: 400, 500, 700
   - Purpose: Consistent typography across platforms

### Python Packages

- **Flask** (>=2.0.0): Web framework
- **requests** (>=2.28.0): HTTP client with retry support
- **urllib3**: Low-level HTTP client (via requests)
- **python-dotenv** (>=1.0.0): Environment variable management
- **gunicorn** (>=21.0.0): Production WSGI server

### Deployment Platform

- **Replit**: Primary hosting platform
- **Environment variables**: API keys and configuration
- **Port**: 5000 (Flask development) / 8080 (production)
