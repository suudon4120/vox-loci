# 1. ベースとなるOSとPythonのバージョンを指定（軽量なslim版を使用）
FROM python:3.12-slim

# pydubでWAVをM4Aに変換するために必要な ffmpeg をOSにインストール
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# 2. uvコマンドを公式イメージからコピーしてインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 3. コンテナ内の作業ディレクトリを /app に設定
WORKDIR /app

# 4. パッケージ管理ファイルだけを先にコピーしてライブラリをインストール
COPY pyproject.toml ./
RUN uv sync --no-install-project

# 5. プロジェクトのソースコード全体をコピー
COPY . .

# 6. アプリケーションが使うポート番号を明示
EXPOSE 8000

# 7. コンテナを起動した時に実行するコマンド
CMD ["uv", "run", "python", "app/app_line.py"]