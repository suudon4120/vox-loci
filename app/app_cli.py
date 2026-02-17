import pandas as pd
import os
import csv
import datetime
import jismesh.utils as ju
import search_mesh  # 検索モジュール
import voicevox_utils  # 音声合成モジュール
import llm_utils       # 生成モジュール

# データファイルのパス設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUMMARY_DB_PATH = os.path.join(BASE_DIR, "data", "processed", "mesh_summary_database.csv")
RAW_DATA_PATH   = os.path.join(BASE_DIR, "data", "processed", "mesh_tweets_integrated.csv")

def load_summary_data():
    # 要約済みデータ(キャッシュ)を読み込む
    summary_dict = {}
    if not os.path.exists(SUMMARY_DB_PATH):
        print(f"[Warning] データベースが見つかりません: {SUMMARY_DB_PATH}")
        return summary_dict
    
    try:
        df = pd.read_csv(SUMMARY_DB_PATH, dtype={'mesh_code': str})
        # 必要なカラムがあるかチェック
        if 'mesh_code' not in df.columns or 'summary' not in df.columns:
            print("[Error] CSVのフォーマットが不正です (mesh_code, summary列が必要です)")
            return summary_dict
        
        df['mesh_code'] = df['mesh_code'].astype(str).str.strip()
        df = df.dropna(subset=['mesh_code', 'summary'])
        summary_dict = dict(zip(df['mesh_code'], df['summary']))
        print(f"要約データベースをロードしました: {len(summary_dict)}件")

    except Exception as e:
        print(f"[Error] CSV読み込みエラー: {e}")

    return summary_dict

def load_raw_data():
    # ツイートデータを読み込む
    raw_dict = {}
    if not os.path.exists(RAW_DATA_PATH):
        print(f"[Error] 元データファイルが見つかりません: {RAW_DATA_PATH}")
        return raw_dict

    try:
        # csv読み込み
        df = pd.read_csv(RAW_DATA_PATH, dtype={'mesh_code': str})
        
        # 文字列化と空白除去
        df['mesh_code'] = df['mesh_code'].astype(str).str.strip()
        
        # 必要な情報を辞書に格納 (key: mesh_code, value: {text, count})
        for _, row in df.iterrows():
            raw_dict[row['mesh_code']] = {
                "text": str(row['aggregated_text']),
                "count": row['tweet_count']
            }
        print(f"📦 元データ(ツイート)をロード: {len(raw_dict)}件")
        
    except Exception as e:
        print(f"[Error] 元データ読み込みエラー: {e}")
    return raw_dict

def save_new_summary(mesh_code, summary, tweet_count):
    """生成した要約をCSVに追記保存する"""
    try:
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # csvモジュールを使って安全に追記（カンマや改行が含まれていてもエスケープしてくれる）
        with open(SUMMARY_DB_PATH, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([mesh_code, summary, now_str, tweet_count])
            
        print(f"💾 要約をデータベースに保存しました ({mesh_code})")
    except Exception as e:
        print(f"[Error] 保存失敗: {e}")

def search_nearby_with_data(lat, lon, summary_data):
    """
    指定座標のメッシュにデータがなければ、周囲8方向(3x3)を探索する関数
    
    Returns:
        tuple: (mesh_code, found_type)
        found_type -> "direct" (中心で発見), "neighbor" (隣で発見), "none" (なし)
    """
    # 中心をチェック
    center_code = str(ju.to_meshcode(lat, lon, level=5)).strip()
    if center_code in summary_data:
        return center_code, "direct"
    
    # 周囲8方向を探索
    # 5次メッシュ(250m)の刻み幅
    # 緯度: 7.5秒 = 7.5/3600 度
    # 経度: 11.25秒 = 11.25/3600 度
    lat_step = 7.5 / 3600
    lon_step = 11.25 / 3600
    
    # 探索順序
    offsets = [
        (-1, 0), (1, 0), (0, -1), (0, 1),
        (-1, -1), (-1, 1), (1, -1), (1, 1)
    ]
    
    for dy, dx in offsets:
        neighbor_lat = lat + (dy * lat_step)
        neighbor_lon = lon + (dx * lon_step)
        neighbor_code = str(ju.to_meshcode(neighbor_lat, neighbor_lon, level=5)).strip()
        
        if neighbor_code in summary_data:
            return neighbor_code, "neighbor"
            
    # それでもなければ中心のコードを返す（生成用）
    return center_code, "none"

def main():
    print("========================================")
    print("   位置情報 要約読み上げアプリ (Proto)")
    print("========================================")
    
    summary_data = load_summary_data()
    raw_data = load_raw_data()
    
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
            if mesh_code in summary_data:
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

            mesh_code, found_type = search_nearby_with_data(target_lat, target_lon, summary_data)
        
        summary_text = ""

        if found_type in ["direct", "neighbor"]:
            summary_text = summary_data[mesh_code]
        
        elif mesh_code in raw_data:
            confirm = input("データベースに要約が見つかりません。生成しますか？ (y/n): ")

            if confirm == 'y':
                print("要約を生成します...")

                # LLM呼び出し
                tweet_info = raw_data[mesh_code]
                generated_text = llm_utils.generate_summary(tweet_info['text'], mesh_code)

                # メモリ更新 & ファイル保存
                summary_data[mesh_code] = generated_text
                save_new_summary(mesh_code, generated_text, tweet_info['count'])

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

        print(f"\n🗣️ 【お地蔵さん】\n「{summary_text}」")
        voicevox_utils.speak_text(summary_text, speaker_id=42)

if __name__ == "__main__":
    main()