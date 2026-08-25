# Vox-Loci

Vox-Lociは、位置情報付きソーシャルメディアデータから人々の経験を抽出し、「地域の記憶」として整理・提示するシステムです。
物理的な記録には残りにくい、その場所の人々の感情や文脈の集合を、現代の人間が追体験可能な物語形式に再構成することを目指しています。

本システムは、膨大で断片的なツイートを約250m四方の5次メッシュ単位で集約し、大規模言語モデル（LLM）を用いて意味的フィルタリングを行います。さらに、長きにわたり地域を見守る「お地蔵さん」のペルソナを付与したLLMが、話題や感情の要点を150文字程度のナラティブ（物語）として生成します。

生成された要約はVOICEVOX（ちび式じい）を利用して音声化され、LINE BotやCLIを通じてユーザーに提供されます。

![System Overview](docs/images/overview.png)

> **Note for Portfolio Reviewers**
> 本リポジトリは研究および開発のポートフォリオとして公開しています。
> プライバシー保護およびデータ利用規約の観点から、生のツイートデータはリポジトリに含めておりません。実装したデータ処理のロジックやプロンプト設計、システム構成のコードをご確認いただけます。

## デモ

以下のQRコードを読み取るか、ボタンからLINE公式アカウントを「友だち追加」することで、実際のシステムをお試しいただけます。チャット画面で「立命館大学」や「出町柳」などの地名を送信してみてください。(現在は`京都・兵庫・沖縄`の地名に対応しています)

<a href="https://lin.ee/VO7qlTV"><img src="https://scdn.line-apps.com/n/line_add_friends/btn/ja.png" alt="友だち追加" height="36" border="0"></a>

<img src="https://qr-official.line.me/gs/L_217owsky_GW.png?oat_content=qr" alt="LINE Bot QR Code" width="200">

> **⚠️ 初回応答時の遅延について**
> 本Botのバックエンドはサーバーレス環境（Cloud Run）で稼働しています。しばらくアクセスがなかった後の初回送信時は、サーバーの起動（コールドスタート）により、応答までに数秒〜十数秒程度の時間がかかる場合があります。

![Demo](docs/images/demo.png)

## 使用技術

| Category      | Technologies                                                                                                                                                             |
| :------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Language** | ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)                                                                    |
| **AI / NLP** | ![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)  |
| **Voice** | ![VOICEVOX](https://img.shields.io/badge/VOICEVOX-A4C639?style=for-the-badge)                                                                                            |
| **Platform** | ![LINE API](https://img.shields.io/badge/LINE_Messaging_API-00C300?style=for-the-badge&logo=line&logoColor=white)                                                        |
| **Database** | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white) ![Neon](https://img.shields.io/badge/Neon-00E599?style=for-the-badge&logo=neon&logoColor=black) |
| **Infrastructure** | ![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white) ![Google Cloud Run](https://img.shields.io/badge/Cloud_Run-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white) |
| **Data / GIS** | ![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white) ![Folium](https://img.shields.io/badge/Folium-2E70D5?style=for-the-badge) |
| **Environment**| ![uv](https://img.shields.io/badge/uv-DE3423?style=for-the-badge)  |
| **VCS** | ![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)                                                                    |

## システム構成とパイプライン

本システムの処理パイプラインは、主に以下の3段階で構成されています。

1. **空間集約 (Spatial Aggregation)**
   - ツイートの座標情報を基に、標準地域メッシュ（4次・5次）へ分類・集約します。
2. **意味的フィルタリング (Semantic Filtering)**
   - OpenAI API等を用い、各ツイートに対して「場所関連性」「主観/客観」「感情極性/ノイズ」「居住者属性」の多角的なラベル付けを行います。
3. **ナラティブ生成 (Narrative Generation)**
   - 抽出されたツイート群を統合し、Gemini等を利用して「お地蔵さん」の語り口による要約文を生成します。

![System Architecture](docs/images/system_architecture.png)

## ディレクトリ構成

    .
    ├── app/              # アプリケーション本体（LINE Bot / CLI / 音声合成連携）
    ├── scripts/          # データ処理パイプライン（抽出・タグ付け・ノイズ除去・メッシュ化）
    ├── archive/          # Batch APIの再実行・検証用ツール群、過去のスクリプト
    ├── data/             # データファイル（Git管理外: rawデータ、CSV、要約テキストなど）
    ├── pyproject.toml    # uvパッケージ管理設定
    ├── uv.lock           # 依存関係ロックファイル
    └── tagged_to_map.sh  # データ処理パイプラインの自動化シェルスクリプト

## 主要スクリプトの説明

### データ前処理 (`scripts/`)
パイプラインに沿って、以下の順序でデータを処理します。
* `extract_pref.py`: 全データから特定都道府県のツイートを抽出。
* `tagging_tweets_batch_submit.py` / `_results.py`: OpenAI Batch APIを用いた非同期タグ付けと結果の結合。
* `remove_noise.py`: タグ付け結果をもとに、ノイズとなるツイートを除去。
* `assign_mesh.py`: 座標情報を基にメッシュコードを付与。
* `aggregate_mesh.py`: メッシュごとにツイートを結合・集計。
* `mapping_tweets.py`: 処理済みデータを地図上にプロットし、HTMLとして可視化。
* `csv_to_sqlite.py`: 処理済みCSVからPostgreSQLへの初期データ移行スクリプト。

### アプリケーション (`app/`)
* `app_line.py`: LINE Botのメインサーバープログラム。
* `app_cli.py`: CLI上で動作確認を行うためのアプリケーション。
* `database.py`: SQLAlchemyを用いたPostgreSQLのスキーマ定義およびDB接続管理。
* `llm_utils.py`: LLM（OpenAI）による物語生成。
* `search_mesh.py`: 検索クエリから該当するメッシュコードを特定。
* `voicevox_utils.py`: 要約テキストをVOICEVOX APIに送信し、音声を生成。

## ローカル環境での起動手順 (参考)

本プロジェクトは `Docker Compose` を用いて、アプリケーション本体とVOICEVOX APIコンテナを統合管理しています。
※注: 実行にはリポジトリに含まれない初期データベースファイルまたはCSVデータが必要です。

1. **環境変数の設定**
   プロジェクトルートに `.env` ファイルを作成し、必要な接続情報を設定します。

   ```env
   OPENAI_API_KEY=your_openai_api_key
   GEMINI_API_KEY=your_gemini_api_key
   LINE_CHANNEL_ACCESS_TOKEN=your_line_access_token
   LINE_CHANNEL_SECRET=your_line_secret
   DATABASE_URL=postgresql://user:password@host/dbname
   ```
1. **コンテナのビルドと起動**
   Dockerがインストールされた環境で以下のコマンドを実行し、アプリとVOICEVOXの2つのコンテナを立ち上げます。

   ``` Bash
   docker compose up -d --build
   ```
   起動後、ローカル（http://localhost:8000）にてWebhookの受け付けが開始され、内部ネットワーク経由でVOICEVOXコンテナ（ポート50021）と通信を行います。