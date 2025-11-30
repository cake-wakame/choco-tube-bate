# チョコTUBE - YouTube視聴サイト

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
