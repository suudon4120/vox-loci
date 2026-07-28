import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# データベースファイルの保存先（dataディレクトリ内に vox_loci.db として作成）
DATABASE_URL = "sqlite:///./data/vox_loci.db"

# データベースエンジンの作成
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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