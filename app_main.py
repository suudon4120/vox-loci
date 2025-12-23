import pandas as pd
import os
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
        
        # ------------------------------------------
        # 共通処理: 結果表示と読み上げ
        # ------------------------------------------
        print(f"📍 特定: {address}")
        print(f"🔢 メッシュコード: {mesh_code}")
        
        # 3. 既存の要約があるか確認
        if mesh_code in summary_data:
            summary_text = summary_data[mesh_code]
            
            print(f"\n🗣️ 【お地蔵さん】\n「{summary_text}」")
            
            # 4. 読み上げ
            voicevox_utils.speak_text(summary_text, speaker_id=11)
            
        else:
            print("\n❌ この場所の要約データはまだありません。")
            # voicevox_utils.speak_text("そこには何もないようじゃ...", speaker_id=11)

if __name__ == "__main__":
    main()