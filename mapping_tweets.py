import pandas as pd
import folium

def create_tweet_map(input_file, output_file):
    # 1. データの読み込み
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"エラー: ファイル '{input_file}' が見つかりません。")
        return

    # 2. 地図の初期化（データの中心付近を表示）
    center_lat = df['lat'].mean()
    center_lon = df['lon'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    # 3. mesh_idごとに色を割り当てるための準備
    # foliumのマーカーで使える色のリスト
    available_colors = [
        'red', 'blue', 'green', 'purple', 'orange', 'darkred',
        'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue',
        'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen',
        'gray', 'black', 'lightgray'
    ]
    
    # mesh_idのユニークな値を取得し、色を割り当てる辞書を作成
    unique_mesh_ids = df['mesh_id'].unique()
    mesh_color_map = {}
    for i, mesh_id in enumerate(unique_mesh_ids):
        # 色のリストを循環して割り当て
        color = available_colors[i % len(available_colors)]
        mesh_color_map[mesh_id] = color

    # 4. 1行ずつデータを読み込んでピンを打つ
    for index, row in df.iterrows():
        lat = row['lat']
        lon = row['lon']
        text = row['text']
        mesh_id = row['mesh_id']
        
        # mesh_idに対応する色を取得
        icon_color = mesh_color_map[mesh_id]
        
        # マーカーを作成して地図に追加
        # popupの幅(max_width)を指定して、長い文章も見やすくします
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(text, max_width=300),
            icon=folium.Icon(color=icon_color),
            tooltip=f"Mesh ID: {mesh_id}" # マウスオーバーでIDを表示（おまけ）
        ).add_to(m)

    # 5. 地図をHTMLファイルとして保存
    m.save(output_file)
    print(f"地図を保存しました: {output_file}")

# 実行
if __name__ == "__main__":
    create_tweet_map('kyoto_tweets_with_mesh.csv', 'kyoto_tweets_map.html')