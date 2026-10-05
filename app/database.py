import os
import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(base_dir, ".env"))
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    # PostgreSQL用のエンジン作成
    engine = create_engine(DATABASE_URL)
else:
    # 環境変数が未指定の場合はローカルのSQLiteにフォールバック
    sqlite_path = os.path.join(base_dir, "data", "vox_loci.db")
    engine = create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------------------------------------------------------
# 1. 地域の記憶（要約）を保存するテーブルの設計図
# 対象CSV: mesh_summary_database.csv
# ---------------------------------------------------------
class MeshSummary(Base):
    __tablename__ = "mesh_summaries"

    # mesh_code が重複しない一意な値になるため、主キー（Primary Key）として扱う
    mesh_code = Column(String, primary_key=True, index=True) 
    summary = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    tweet_count = Column(Integer, default=0)

# ---------------------------------------------------------
# 2. 集約された生ツイートデータを保存するテーブルの設計図
# 対象CSV: mesh_tweets_integrated.csv
# ---------------------------------------------------------
class IntegratedTweet(Base):
    __tablename__ = "mesh_tweets_integrated"

    mesh_code = Column(String, primary_key=True, index=True)
    tweet_count = Column(Integer, default=0)
    aggregated_text = Column(Text, nullable=False)

# ---------------------------------------------------------
# データベースの初期化関数（テーブルを実際に作成する）
# ---------------------------------------------------------
def init_db():
    Base.metadata.create_all(bind=engine)
    print("データベースの初期化が完了しました。")

if __name__ == "__main__":
    # このファイルを直接実行したときにテーブルを作成します
    init_db()