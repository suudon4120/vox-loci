import pandas as pd
import jismesh.utils as ju  # 標準地域メッシュ用ライブラリ
import os
import argparse
import sys

# =========================================================
# 【設定エリア】
# =========================================================
parser = argparse.ArgumentParser(
    description="ツイートを読み込んで地域メッシュごとにメッシュコードを付与するプログラム"
)
parser.add_argument("--input", type=str, help="処理対象のファイルパス")
parser.add_argument(
    "--process_type",
    type=str,
    default="csv",
    help="処理タイプ: 'csv' または 'txt' (デフォルト: csv)",
)
parser.add_argument(
    "--mesh_level",
    type=int,
    default=5,
    help="メッシュの細かさ (デフォルト: 5次メッシュ(約250m四方))",
)
args = parser.parse_args()

if args.input:
    INPUT_PATH = args.input
    print(f"コマンドライン引数からファイル名を受け取りました: {INPUT_PATH}")
else:
    print("入力ファイルが指定されていません。")
    INPUT_PATH = input(">>処理するファイル名を入力してください: ").strip()
if not INPUT_PATH:
    print("ファイル名が入力されませんでした。終了します。")
    sys.exit()
root, ext = os.path.splitext(INPUT_PATH)
PROCESS_TYPE = args.process_type
# メッシュの細かさ (レベル)
# 3: 3次メッシュ (約1km四方)
# 4: 4次メッシュ (約500m四方)
# 5: 5次メッシュ (約250m四方)
# 6: 6次メッシュ (約125m四方)
MESH_LEVEL = args.mesh_level

# =========================================================
# 【メイン処理ロジック】
# =========================================================


def load_and_standard_mesh(input_path, process_type, mesh_level):
    """
    データを読み込み、日本標準地域メッシュコードを付与する関数
    """
    df = pd.DataFrame()

    print(f"▶️ 読み込みモード: {process_type.upper()}")

    # --- 1. データの読み込み ---
    if process_type == "txt":
        data = []
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("[source") or not line:
                        continue
                    parts = line.split("\t")
                    record = {}
                    if len(parts) >= 5:
                        record["timestamp"] = parts[0]
                        record["lat"] = float(parts[2])
                        record["lon"] = float(parts[3])
                        record["text"] = parts[4]
                        data.append(record)
                    else:
                        parts = line.split()
                        if len(parts) >= 9:
                            record["timestamp"] = " ".join(parts[0:6])
                            record["lat"] = float(parts[7])
                            record["lon"] = float(parts[8])
                            record["text"] = " ".join(parts[9:])
                            data.append(record)
            df = pd.DataFrame(data)
            df.rename(columns={"lat": "latitude", "lon": "longitude"}, inplace=True)
        except Exception as e:
            print(f"TXT読み込みエラー: {e}")
            return pd.DataFrame()

    elif process_type == "csv":
        try:
            df = pd.read_csv(input_path, sep=None, engine="python")
            df.rename(columns={"latitude": "lat", "longitude": "lon"}, inplace=True)
            # 緯度経度を数値変換してクリーニング
            df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
            df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
            df.dropna(subset=["lat", "lon"], inplace=True)
        except Exception as e:
            print(f"CSV読み込みエラー: {e}")
            return pd.DataFrame()

    if df.empty:
        print("警告: データが空です。")
        return pd.DataFrame()

    # --- 2. 標準地域メッシュコードの付与 ---
    print(f"▶️ メッシュ変換: レベル {mesh_level} (JIS X 0410)")

    # jismeshを使って緯度経度からメッシュコードを一括変換
    # to_meshcodeはSeries(列)を受け取ってSeriesを返せるので高速です
    df["mesh_code"] = ju.to_meshcode(df["lat"], df["lon"], mesh_level)

    # --- 3. 可視化・分析用に「メッシュの中心座標」も計算しておく ---
    # メッシュコードだけだと地図にプロットしにくいため、そのメッシュの中心点(lat/lon)を求めます
    lat_center, lon_center = ju.to_meshpoint(
        df["mesh_code"], lat_multiplier=0.5, lon_multiplier=0.5
    )
    df["mesh_center_lat"] = lat_center
    df["mesh_center_lon"] = lon_center

    # --- 4. カラム整理 ---
    # 必要な列を見やすい順序に
    cols = [
        "timestamp",
        "mesh_code",
        "lat",
        "lon",
        "mesh_center_lat",
        "mesh_center_lon",
        "text",
    ]
    # 元データに他の列があればそれも後ろに追加
    remaining_cols = [c for c in df.columns if c not in cols]

    return df[cols + remaining_cols]


# 実行
df_final = load_and_standard_mesh(INPUT_PATH, PROCESS_TYPE, MESH_LEVEL)

if not df_final.empty:
    print("\n--- 処理結果の先頭5行 ---")
    print(df_final[["mesh_code", "lat", "lon", "text"]].head().to_string(index=False))

    OUTPUT_FILE = f"{root}_mesh.csv"
    df_final.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n✅ 完了: '{OUTPUT_FILE}' に保存しました。")
