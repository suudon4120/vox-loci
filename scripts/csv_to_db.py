# csv_to_sqlite.py
import pandas as pd
import os
import sys
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.database import SessionLocal, MeshSummary, IntegratedTweet, engine

def migrate_data():
    db = SessionLocal()
    print(f"接続先DB: {engine.url.drivername}") # sqlite か postgresql か確認用
    print("データ移行を開始します...")

    # ---------------------------------------------------------
    # 1. 地域の記憶（要約）データの移行
    # ---------------------------------------------------------
    summary_csv = "data/processed/mesh_summary_database.csv"
    if os.path.exists(summary_csv):
        df_summary = pd.read_csv(summary_csv).fillna('')
        records = []
        for _, row in df_summary.iterrows():
            try:
                updated_at_val = pd.to_datetime(row['updated_at']).to_pydatetime()
            except:
                updated_at_val = datetime.utcnow()
            
            records.append({
                "mesh_code": str(row['mesh_code']),
                "summary": str(row['summary']),
                "updated_at": updated_at_val,
                "tweet_count": int(row['tweet_count']) if row['tweet_count'] != '' else 0
            })
        
        if records:
            # 1000件ずつまとめて一括送信（通信回数を劇的に減らす）
            chunk_size = 1000
            for i in range(0, len(records), chunk_size):
                chunk = records[i:i + chunk_size]
                stmt = insert(MeshSummary).values(chunk)
                # 既に同じmesh_codeがあれば上書きする設定
                stmt = stmt.on_conflict_do_update(
                    index_elements=['mesh_code'],
                    set_={
                        'summary': stmt.excluded.summary,
                        'updated_at': stmt.excluded.updated_at,
                        'tweet_count': stmt.excluded.tweet_count
                    }
                )
                db.execute(stmt)
                db.commit()
                print(f"  - 要約データ: {min(i + chunk_size, len(records))} / {len(records)} 件完了")
        print(f"✅ {summary_csv} のデータを移行しました。")
    else:
        print(f"⚠️ {summary_csv} が見つかりません。")

    # ---------------------------------------------------------
    # 2. 集約された生ツイートデータの移行
    # ---------------------------------------------------------
    integrated_csv = "data/processed/mesh_tweets_integrated.csv"
    if os.path.exists(integrated_csv):
        df_integrated = pd.read_csv(integrated_csv).fillna('')
        records = []
        for _, row in df_integrated.iterrows():
            records.append({
                "mesh_code": str(row['mesh_code']),
                "tweet_count": int(row['tweet_count']) if row['tweet_count'] != '' else 0,
                "aggregated_text": str(row['aggregated_text'])
            })
            
        if records:
            # こちらはテキストが長いため500件ずつ一括送信
            chunk_size = 500
            for i in range(0, len(records), chunk_size):
                chunk = records[i:i + chunk_size]
                stmt = insert(IntegratedTweet).values(chunk)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['mesh_code'],
                    set_={
                        'tweet_count': stmt.excluded.tweet_count,
                        'aggregated_text': stmt.excluded.aggregated_text
                    }
                )
                db.execute(stmt)
                db.commit()
                print(f"  - 統合ツイート: {min(i + chunk_size, len(records))} / {len(records)} 件完了")
        print(f"✅ {integrated_csv} のデータを移行しました。")
    else:
        print(f"⚠️ {integrated_csv} が見つかりません。")

    db.close()
    print("🎉 すべてのデータ移行が完了しました！")

if __name__ == "__main__":
    migrate_data()