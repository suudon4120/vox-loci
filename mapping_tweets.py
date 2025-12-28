import pandas as pd
import folium
import os
import argparse
import sys

parser = argparse.ArgumentParser(description="ツイートを地図上にプロットするプログラム")
parser.add_argument("--input", type=str, help="処理対象のファイルパス")
args = parser.parse_args()

if args.input:
    INPUT_FILE = args.input
    print(f"コマンドライン引数からファイル名を受け取りました: {INPUT_FILE}")
else:
    print("入力ファイルが指定されていません。")
    INPUT_FILE = input(">>処理するファイル名を入力してください: ").strip()
if not INPUT_FILE:
    print("ファイル名が入力されませんでした。終了します。")
    sys.exit()
root, ext = os.path.splitext(INPUT_FILE)
OUPUT_FILE = f"{root}_map.html"


def create_tweet_map(input_file, output_file):
    # 1. データの読み込み
    try:
        df = pd.read_csv(input_file)

        # mesh_code列が存在するか確認
        if "mesh_code" not in df.columns:
            print("エラー: データ内に 'mesh_code' 列が見つかりません。")
            return
    except FileNotFoundError:
        print(f"エラー: ファイル '{input_file}' が見つかりません。")
        return

    # 2. 地図の初期化（データの中心付近を表示）
    center_lat = df["lat"].mean()
    center_lon = df["lon"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    # 3. mesh_idごとに色を割り当てるための準備
    # foliumのマーカーで使える色のリスト
    available_colors = [
        "red",
        "blue",
        "green",
        "purple",
        "orange",
        "darkred",
        "lightred",
        "beige",
        "darkblue",
        "darkgreen",
        "cadetblue",
        "darkpurple",
        "white",
        "pink",
        "lightblue",
        "lightgreen",
        "gray",
        "black",
        "lightgray",
    ]

    # mesh_idのユニークな値を取得し、色を割り当てる辞書を作成
    unique_mesh_codes = df["mesh_code"].unique()
    mesh_color_map = {}
    for i, code in enumerate(unique_mesh_codes):
        # 色のリストを循環して割り当て
        color = available_colors[i % len(available_colors)]
        mesh_color_map[code] = color

    # 4. 1行ずつデータを読み込んでピンを打つ
    for index, row in df.iterrows():
        lat = row["lat"]
        lon = row["lon"]
        text = str(row["text"])
        mesh_code = row["mesh_code"]

        # mesh_idに対応する色を取得
        icon_color = mesh_color_map[mesh_code]

        # マーカーを作成して地図に追加
        # popupの幅(max_width)を指定して、長い文章も見やすくします
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(text, max_width=300),
            icon=folium.Icon(color=icon_color),
            tooltip=f"Mesh Code: {mesh_code}",  # マウスオーバーでIDを表示（おまけ）
        ).add_to(m)

    # 5. 地図をHTMLファイルとして保存
    m.save(output_file)
    print(f"地図を保存しました: {output_file}")


# 実行
if __name__ == "__main__":
    create_tweet_map(INPUT_FILE, OUPUT_FILE)
