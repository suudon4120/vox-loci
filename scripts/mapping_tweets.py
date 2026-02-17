import pandas as pd
import folium
import os
import argparse
import sys
import jismesh.utils as ju

# 引数設定
parser = argparse.ArgumentParser(description="ツイートを地図上にプロットするプログラム")
parser.add_argument("--input", type=str, help="処理対象のファイルパス")
# シンプルモード（黒グリッド・オレンジ点・ポップアップなし）
parser.add_argument("--simple", action="store_true", help="軽量モード（グリッド表示・ポップアップなし）で出力します")
args = parser.parse_args()

# 入力ファイル
if args.input:
    INPUT_PATH = args.input
else:
    print("入力ファイルが指定されていません。")
    INPUT_PATH = input(">>処理対象のファイルパスを入力してください: ").strip()
if not INPUT_PATH:
    print("ファイルパスが入力されませんでした。終了します。")
    sys.exit()
INPUT_PATH = os.path.abspath(INPUT_PATH)
# 出力ファイル
input_filename = os.path.basename(INPUT_PATH)
root, ext = os.path.splitext(input_filename)
suffix = "_simple" if args.simple else "_detail"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "interim", f'{root}_map{suffix}.html')

def create_tweet_map(input_file, output_file, is_simple_mode):
    # 1. データの読み込み
    try:
        df = pd.read_csv(input_file)
        
        if 'lat' not in df.columns or 'lon' not in df.columns:
            print("エラー: 'lat' または 'lon' 列が見つかりません。")
            return
        
        # mesh_codeのチェック
        if 'mesh_code' not in df.columns:
            if is_simple_mode:
                print("注意: 'mesh_code' 列がないため、グリッド線は描画されません。")
            else:
                print("エラー: 詳細モードには 'mesh_code' 列が必要です。")
                return
            
    except FileNotFoundError:
        print(f"エラー: ファイル '{input_file}' が見つかりません。")
        return

    # 2. 地図の初期化
    center_lat = df['lat'].mean()
    center_lon = df['lon'].mean()
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=13, 
        # tiles='CartoDB positron', 
        # tiles='CartoDB dark_matter', grid_color = 'white', 
        tiles='https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png', attr='国土地理院',
        prefer_canvas=True
    )

    # 3. メッシュ区切り線（グリッド）の描画
    if is_simple_mode and 'mesh_code' in df.columns:
        print("シンプルモード: メッシュ枠線を描画中...")
        unique_mesh_codes = df['mesh_code'].astype(str).unique()
        
        for code in unique_mesh_codes:
            try:
                lat_sw, lon_sw = ju.to_meshpoint(code, 0, 0)
                lat_ne, lon_ne = ju.to_meshpoint(code, 1, 1)
                
                # === グリッド線の設定変更 ===
                folium.Rectangle(
                    bounds=[[lat_sw, lon_sw], [lat_ne, lon_ne]],
                    color="black",      # 色を黒に変更
                    weight=0.8,         # 線の太さ（適度な太さに調整）
                    fill=False,
                    opacity=1.0,        # 透明度をなくしてくっきり表示
                    interactive=False
                ).add_to(m)
            except Exception:
                continue

    # 4. 色の準備（詳細モード用）
    mesh_color_map = {}
    if not is_simple_mode:
        available_colors = [
            'red', 'blue', 'green', 'purple', 'orange', 'darkred',
            'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue',
            'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen',
            'gray', 'black', 'lightgray'
        ]
        unique_mesh_codes = df['mesh_code'].unique()
        for i, code in enumerate(unique_mesh_codes):
            mesh_color_map[code] = available_colors[i % len(available_colors)]

    # 5. プロット処理
    print(f"全 {len(df)} 件のデータをプロット中... モード: {'軽量(グリッド・点)' if is_simple_mode else '詳細(ピン)'}")

    for index, row in df.iterrows():
        lat = row['lat']
        lon = row['lon']
        
        if is_simple_mode:
            # === 軽量モード（点の描画設定変更） ===
            folium.CircleMarker(
                location=[lat, lon],
                radius=3,               # 点を少し大きくして目立たせる（2→3）
                color="darkorange",     # 枠線の色を濃いオレンジに
                weight=1,               # 枠線の太さ
                fill=True,
                fill_color="orange",    # 塗りつぶし色を鮮やかなオレンジに
                fill_opacity=0.9,       # 塗りつぶしの不透明度を高めに
                popup=None,
                tooltip=None
            ).add_to(m)
        
        else:
            # === 詳細モード ===
            text = str(row['text'])
            mesh_code = row['mesh_code']
            icon_color = mesh_color_map.get(mesh_code, 'blue')

            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(text, max_width=300),
                icon=folium.Icon(color=icon_color),
                tooltip=f"Mesh: {mesh_code}"
            ).add_to(m)

    # 6. 保存
    m.save(output_file)
    print(f"地図を保存しました: {output_file}")

if __name__ == "__main__":
    create_tweet_map(INPUT_PATH, OUTPUT_PATH, args.simple)