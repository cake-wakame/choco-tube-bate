# チョコTUBE - YouTube視聴サイト

YouTube動画を視聴できるWebアプリケーション

## プロジェクト概要

チョコTUBEは、複数のAPIソースを統合したYouTube視聴サイトです。Google公式YouTube APIによる検索機能と、複数のオープンソースプロジェクトからの動画視聴方法を組み合わせています。

## アーキテクチャ

### バックエンド
- **Flask** - Pythonウェブフレームワーク
- **Gunicorn** - 本番環境用WSGIサーバー

### API統合
- **YouTube Data API v3** - 公式検索機能（要APIキー）
- **Invidious API** - フォールバック検索・トレンド取得
- **EDU Video API** - 動画情報取得
- **YTDL Stream API** - ストリーミングURL取得
- **M3U8 API** - HLSストリーミング対応

### フロントエンド
- **Jinja2テンプレート** - HTMLレンダリング
- **HLS.js** - HLSビデオ再生対応
- **カスタムCSS** - チョコレートテーマのダークモードUI

## ファイル構造

```
├── app.py              # メインFlaskアプリケーション
├── templates/
│   ├── base.html       # ベーステンプレート
│   ├── index.html      # ホームページ（トレンド）
│   ├── search.html     # 検索結果ページ
│   └── watch.html      # 動画再生ページ
├── static/
│   ├── style.css       # スタイルシート
│   └── script.js       # フロントエンドスクリプト
├── requirements.txt    # Python依存関係
├── Procfile            # Heroku/Render用
└── render.yaml         # Render設定
```

## 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `YOUTUBE_API_KEY` | Google YouTube Data API v3キー | 任意（なしでもInvidious APIで検索可能） |

## 機能

- 急上昇動画の表示
- 動画検索（YouTube API/Invidious API）
- 動画再生（複数ソース対応）
- 関連動画表示
- コメント表示

## Renderへのデプロイ

1. GitHubにプッシュ
2. Renderで新しいWeb Serviceを作成
3. ビルドコマンド: `pip install -r requirements.txt`
4. スタートコマンド: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 app:app`
5. 環境変数に`YOUTUBE_API_KEY`を設定（任意）

## ローカル開発

```bash
pip install -r requirements.txt
python app.py
```

## 更新履歴

- 2025-11-29: 初期バージョン作成
  - Flask/Jinja2ベースのアプリケーション
  - 複数APIソースの統合
  - チョコレートテーマUI
  - Render対応
