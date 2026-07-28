import pandas as pd
import os
import sys
from datetime import datetime

# appモジュール（database.py）を読み込めるようにパスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.database import SessionLocal, MeshSummary, IntegratedTweet

def migrate_data():
    db = SessionLocal()
    
    print("データ移行を開始します...")

    # ---------------------------------------------------------
    # 1. 地域の記憶（要約）データの移行
    # ---------------------------------------------------------
    summary_csv = "data/processed/mesh_summary_database.csv"
    if os.path.exists(summary_csv):
        # CSVを読み込む（欠損値などは空文字列にするなどの処理を自動で行う）
        df_summary = pd.read_csv(summary_csv).fillna('')
        for _, row in df_summary.iterrows():
            # 日付文字列をPythonのdatetimeオブジェクトに変換（エラー時は現在時刻）
            try:
                updated_at_val = pd.to_datetime(row['updated_at'])
            except:
                updated_at_val = datetime.utcnow()
            
            record = MeshSummary(
                mesh_code=str(row['mesh_code']),
                summary=str(row['summary']),
                updated_at=updated_at_val,
                tweet_count=int(row['tweet_count']) if row['tweet_count'] else 0
            )
            # mergeを使うことで、同じmesh_codeがあれば上書き、なければ新規追加します
            db.merge(record)
        print(f"✅ {summary_csv} のデータを移行しました。")
    else:
        print(f"⚠️ {summary_csv} が見つかりません。")

    # ---------------------------------------------------------
    # 2. 集約された生ツイートデータの移行
    # ---------------------------------------------------------
    integrated_csv = "data/processed/mesh_tweets_integrated.csv"
    if os.path.exists(integrated_csv):
        df_integrated = pd.read_csv(integrated_csv).fillna('')
        for _, row in df_integrated.iterrows():
            record = IntegratedTweet(
                mesh_code=str(row['mesh_code']),
                tweet_count=int(row['tweet_count']) if row['tweet_count'] else 0,
                aggregated_text=str(row['aggregated_text'])
            )
            db.merge(record)
        print(f"✅ {integrated_csv} のデータを移行しました。")
    else:
        print(f"⚠️ {integrated_csv} が見つかりません。")

    # データベースに変更を保存（コミット）して閉じる
    db.commit()
    db.close()
    print("🎉 すべてのデータ移行が完了しました！")

if __name__ == "__main__":
    migrate_data()