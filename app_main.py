import pandas as pd
import os
import jismesh.utils as ju
import search_mesh  # 既存の検索モジュール
import voicevox_utils  # 音声合成モジュール

# データファイルのパス設定
DATA_PATH = "mesh_summary_database.csv"

def load_summary_data():
    """
    CSVの要約データベースを読み込み、辞書型 {mesh_code: summary} にして返す
    想定カラム: mesh_code, summary, updated_at, tweet_count
    """
    summary_dict = {}
    
    if not os.path.exists(DATA_PATH):
        print(f"[Warning] データベースが見つかりません: {DATA_PATH}")
        return summary_dict

    try:
        df = pd.read_csv(DATA_PATH, dtype={'mesh_code': str})
        
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

def search_nearby_with_data(lat, lon, summary_data):
    """
    指定座標のメッシュにデータがなければ、周囲8方向(3x3)を探索する関数
    
    Returns:
        tuple: (mesh_code, found_type)
        found_type -> "direct" (中心で発見), "neighbor" (隣で発見), "none" (なし)
    """
    # 1. まず中心をチェック
    center_code = str(ju.to_meshcode(lat, lon, level=5)).strip()
    if center_code in summary_data:
        return center_code, "direct"
    
    # 2. 周囲8方向を探索
    # 5次メッシュ(250m)の刻み幅
    # 緯度: 7.5秒 = 7.5/3600 度
    # 経度: 11.25秒 = 11.25/3600 度
    lat_step = 7.5 / 3600
    lon_step = 11.25 / 3600
    
    # 探索順序（ランダム性を持たせても面白いが、今回は左上から走査）
    # (-1, -1) ... (1, 1)
    offsets = [
        (-1, 0), (1, 0), (0, -1), (0, 1), # 上下左右を優先
        (-1, -1), (-1, 1), (1, -1), (1, 1) # 斜めは後回し
    ]
    
    for dy, dx in offsets:
        neighbor_lat = lat + (dy * lat_step)
        neighbor_lon = lon + (dx * lon_step)
        neighbor_code = str(ju.to_meshcode(neighbor_lat, neighbor_lon, level=5)).strip()
        
        if neighbor_code in summary_data:
            return neighbor_code, "neighbor"
            
    # 3. それでもなければ中心のコードを返す（生成用）
    return center_code, "none"

def main():
    print("========================================")
    print("   位置情報 要約読み上げアプリ (Proto)")
    print("========================================")
    
    # 1. 起動時にデータをメモリにロード
    summary_data = load_summary_data()
    
    while True:
        print("\n" + "="*30)
        query = input("場所名 または メッシュコード を入力 (qで終了): ")
        
        if query.lower() == 'q':
            print("終了します。")
            break
            
        mesh_code = ""
        address = ""

        if query.isdigit():
            # 数字のみ入力された場合 -> 直接メッシュコードとして扱う
            print(f"🔢 コード直接入力モード")
            mesh_code = query
            address = "(コード直接指定のため住所不明)"
            
        else:
            # 文字列の場合 -> 場所検索を行う
            print(f"🔍 地名検索モード: {query}")
            result = search_mesh.get_mesh_data(query)
            
            if not result:
                print("場所が見つかりませんでした。")
                continue
            
            mesh_code = str(result['mesh_code']).strip()
            address = result['address']
            target_lat = result['lat']
            target_lon = result['lon']

            mesh_code, found_type = search_nearby_with_data(target_lat, target_lon, summary_data)
        
        # ------------------------------------------
        # 共通処理: 結果表示と読み上げ
        # ------------------------------------------
        print(f"📍 特定: {address}")
        
        if found_type == "neighbor":
            print(f"⚠️ 指定地点にはデータがありませんでしたが...")
            print(f"✅ すぐ近くのメッシュ ({mesh_code}) にデータが見つかりました！")
            
        print(f"🔢 ターゲットメッシュ: {mesh_code}")
        
        if mesh_code in summary_data:
            summary_text = summary_data[mesh_code]
            
            # 周辺データだった場合、前置きを入れると親切
            prefix = ""
            if found_type == "neighbor":
                prefix = "その場所のことは詳しくないんじゃが、すぐ近くのことなら知っておるぞ。"
                print(f"🗣️ 【お地蔵さん】\n「{prefix}」")
                print(f"「{summary_text}」")
                voicevox_utils.speak_text(prefix + summary_text, speaker_id=11)
            else:
                print(f"\n🗣️ 【お地蔵さん】\n「{summary_text}」")
                voicevox_utils.speak_text(summary_text, speaker_id=11)
            
        else:
            print("\n❌ 周辺を含めても、まだ要約データはありません。")
            # voicevox_utils.speak_text("この辺りには何もないようじゃ...", speaker_id=11)

if __name__ == "__main__":
    main()