import pandas as pd
import jismesh.utils as ju # 標準地域メッシュ用ライブラリ
import os
import argparse
import sys

# =========================================================
# 【設定エリア】
# =========================================================
parser = argparse.ArgumentParser(description="ツイートを読み込んで地域メッシュごとにメッシュコードを付与するプログラム")
parser.add_argument("--input", type=str, help="処理対象のファイルパス")
parser.add_argument("--mesh_level", type=int, default=5, help="メッシュの細かさ (デフォルト: 5次メッシュ(約250m四方))")
args = parser.parse_args()

# 入力ファイル
if args.input:
    INPUT_PATH = args.input
    print(f"コマンドライン引数からファイルパスを受け取りました: {INPUT_PATH}")
else:
    print("入力ファイルが指定されていません。")
    INPUT_PATH = input(">>処理するファイルパスを入力してください: ").strip()
if not INPUT_PATH:
    print("ファイルパスが入力されませんでした。終了します。")
    sys.exit()
INPUT_PATH = os.path.abspath(INPUT_PATH)
input_filename = os.path.basename(INPUT_PATH)
root, ext = os.path.splitext(input_filename)
# 出力ファイル
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "interim", f"{root}_mesh.csv")

MESH_LEVEL = args.mesh_level
# メッシュの細かさ (レベル)
# 3: 3次メッシュ (約1km四方)
# 4: 4次メッシュ (約500m四方)
# 5: 5次メッシュ (約250m四方)
# 6: 6次メッシュ (約125m四方)

# =========================================================
# 【メイン処理ロジック】
# =========================================================

def load_and_standard_mesh(input_path, mesh_level):
    """
    データを読み込み、日本標準地域メッシュコードを付与する関数
    """
    df = pd.DataFrame()
    print("▶️ データの読み込み中...")

    # --- データの読み込み ---
    try:
        df = pd.read_csv(input_path)
        
        # latitude/longitude があれば lat/lon に統一
        df.rename(columns={'latitude': 'lat', 'longitude': 'lon'}, inplace=True)
        
        if 'lat' not in df.columns or 'lon' not in df.columns:
            print("エラー: CSVに 'lat', 'lon' (または 'latitude', 'longitude') カラムがありません。")
            return pd.DataFrame()

        # 緯度経度を数値変換してクリーニング
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df.dropna(subset=['lat', 'lon'], inplace=True)
        
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
        return pd.DataFrame()

    if df.empty:
        print("警告: データが空です。")
        return pd.DataFrame()

    # --- 標準地域メッシュコードの付与 ---
    print(f"▶️ メッシュ変換: レベル {mesh_level} (JIS X 0410)")
    df['mesh_code'] = ju.to_meshcode(df['lat'], df['lon'], mesh_level)

    # --- メッシュ中心座標の計算 ---
    lat_center, lon_center = ju.to_meshpoint(df['mesh_code'], lat_multiplier=0.5, lon_multiplier=0.5)
    df['mesh_center_lat'] = lat_center
    df['mesh_center_lon'] = lon_center

    # --- カラム整理 ---
    cols = ['timestamp', 'mesh_code', 'lat', 'lon', 'mesh_center_lat', 'mesh_center_lon', 'text']
    cols = [c for c in cols if c in df.columns] # 存在するカラムだけ抽出
    remaining_cols = [c for c in df.columns if c not in cols]
    
    return df[cols + remaining_cols]

# 実行
df_final = load_and_standard_mesh(INPUT_PATH, MESH_LEVEL)

if not df_final.empty:
    print("\n--- 処理結果の先頭5行 ---")
    preview_cols = [c for c in ['mesh_code', 'lat', 'lon', 'text'] if c in df_final.columns]
    print(df_final[preview_cols].head().to_string(index=False))

    df_final.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')
    print(f"\n✅ 完了: '{OUTPUT_PATH}' に保存しました。")