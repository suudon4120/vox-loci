import os
import datetime
import jismesh.utils as ju
import search_mesh  # 検索モジュール
import voicevox_utils  # 音声合成モジュール
import llm_utils       # 生成モジュール

# データベース設定をインポート
from database import SessionLocal, MeshSummary, IntegratedTweet

def save_new_summary(db, mesh_code, summary, tweet_count):
    """生成した要約をデータベースに保存する"""
    try:
        # 新しいレコードを作成
        record = MeshSummary(
            mesh_code=str(mesh_code),
            summary=summary,
            tweet_count=tweet_count,
            updated_at=datetime.datetime.utcnow()
        )
        # mergeを使って、すでに存在する場合は上書き、なければ新規追加
        db.merge(record)
        db.commit()
        print(f"💾 要約をデータベースに保存しました ({mesh_code})")
    except Exception as e:
        db.rollback() # エラーが起きたら変更を元に戻す
        print(f"[Error] 保存失敗: {e}")

def search_nearby_with_db(db, lat, lon):
    """
    データベースを検索して指定座標のメッシュ、または周囲8方向(3x3)を探索する関数
    
    Returns:
        tuple: (mesh_code, found_type)
        found_type -> "direct" (中心で発見), "neighbor" (隣で発見), "none" (なし)
    """
    # 中心をチェック
    center_code = str(ju.to_meshcode(lat, lon, level=5)).strip()
    
    # データベースにクエリを投げて検索 (SELECT * FROM mesh_summaries WHERE mesh_code = ...)
    if db.query(MeshSummary).filter(MeshSummary.mesh_code == center_code).first():
        return center_code, "direct"
    
    # 周囲8方向を探索
    lat_step = 7.5 / 3600
    lon_step = 11.25 / 3600
    offsets = [
        (-1, 0), (1, 0), (0, -1), (0, 1),
        (-1, -1), (-1, 1), (1, -1), (1, 1)
    ]
    
    for dy, dx in offsets:
        neighbor_lat = lat + (dy * lat_step)
        neighbor_lon = lon + (dx * lon_step)
        neighbor_code = str(ju.to_meshcode(neighbor_lat, neighbor_lon, level=5)).strip()
        
        # 隣接メッシュをデータベース検索
        if db.query(MeshSummary).filter(MeshSummary.mesh_code == neighbor_code).first():
            return neighbor_code, "neighbor"
            
    # それでもなければ中心のコードを返す（生成用）
    return center_code, "none"

def main():
    print("========================================")
    print("   位置情報 要約読み上げアプリ (DB対応版)")
    print("========================================")
    
    # データベースセッションを開始
    db = SessionLocal()
    
    try:
        while True:
            print("\n" + "="*30)
            query = input("場所名 または メッシュコード を入力 (qで終了): ")
            
            if query.lower() == 'q':
                print("終了します。")
                break
                
            mesh_code = ""
            address = ""
            found_type = "none"

            if query.isdigit():
                # 数字のみ入力された場合 -> 直接メッシュコードとして扱う
                print(f"🔢 コード直接入力モード")
                mesh_code = query
                address = "(コード直接指定のため住所不明)"
                # DB検索
                if db.query(MeshSummary).filter(MeshSummary.mesh_code == mesh_code).first():
                    found_type = "direct"
                
            else:
                # 文字列の場合 -> 場所検索を行う
                print(f"🔍 地名検索モード: {query}")
                result = search_mesh.get_mesh_data(query)
                
                if not result:
                    print("場所が見つかりませんでした。")
                    continue
                
                address = result['address']
                target_lat = result['lat']
                target_lon = result['lon']

                # データベースを使って周辺探索
                mesh_code, found_type = search_nearby_with_db(db, target_lat, target_lon)
            
            summary_text = ""

            if found_type in ["direct", "neighbor"]:
                # 要約データをDBから取得
                summary_record = db.query(MeshSummary).filter(MeshSummary.mesh_code == mesh_code).first()
                summary_text = summary_record.summary
            
            else:
                # 要約がない場合、生データ(IntegratedTweet)がDBにあるか確認
                raw_record = db.query(IntegratedTweet).filter(IntegratedTweet.mesh_code == mesh_code).first()
                
                if raw_record:
                    confirm = input("データベースに要約が見つかりません。生成しますか？ (y/n): ")

                    if confirm == 'y':
                        print("要約を生成します...")

                        # LLM呼び出し
                        generated_text = llm_utils.generate_summary(raw_record.aggregated_text, mesh_code)

                        # データベースへ保存
                        save_new_summary(db, mesh_code, generated_text, raw_record.tweet_count)

                        summary_text = generated_text
                        found_type = "generated"
                    else:
                        print("生成をキャンセルしました。")
                        found_type = "cancelled"
                else:
                    found_type = "not_found"

            # ------------------------------------------
            # 共通処理: 結果表示と読み上げ
            # ------------------------------------------
            print(f"📍 特定: {address}")
            
            if found_type == "not_found":
                print("この場所にはツイートデータがありませんでした。")
            elif found_type == "cancelled":
                print("要約を生成しませんでした。")
            else:
                if found_type == "neighbor":
                    print(f"⚠️ 指定地点にはデータがありませんでしたが...")
                    print(f"✅ すぐ近くのメッシュ ({mesh_code}) にデータが見つかりました！")
                elif found_type == "generated":
                    print("新しく要約を生成しました！")

            if summary_text:
                print(f"\n🗣️ 【お地蔵さん】\n「{summary_text}」")
                voicevox_utils.speak_text(summary_text, speaker_id=42)

    finally:
        # アプリ終了時に確実にデータベース接続を閉じる
        db.close()

if __name__ == "__main__":
    main()