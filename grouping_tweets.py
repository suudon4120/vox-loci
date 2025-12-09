import pandas as pd

# 1. ファイル読み込みとパース（前回同様）
file_path = 'KYOTO2_100.txt'
data = []

with open(file_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line.startswith('[source') or not line:
            continue
        
        parts = line.split('\t')
        
        # データの格納用辞書
        record = {}
        
        if len(parts) >= 5: # タブ区切りの場合
            try:
                # 日付情報がある場合は取得（1列目）
                record['timestamp'] = parts[0]
                record['lat'] = float(parts[2])
                record['lon'] = float(parts[3])
                record['text'] = parts[4]
                data.append(record)
            except ValueError:
                continue
        else: # スペース区切りの場合
            parts = line.split()
            if len(parts) >= 9:
                try:
                    # スペース区切りの場合、タイムスタンプが分割されているため結合
                    record['timestamp'] = " ".join(parts[0:6])
                    record['lat'] = float(parts[7])
                    record['lon'] = float(parts[8])
                    record['text'] = " ".join(parts[9:])
                    data.append(record)
                except ValueError:
                    continue

df = pd.DataFrame(data)

# 2. メッシュ情報の計算と付与 (200mメッシュ)
lat_step = 0.0018
lon_step = 0.0022

# メッシュ座標の計算（小数点4桁で丸めることで誤差を排除）
df['mesh_lat'] = ((df['lat'] // lat_step) * lat_step).round(4)
df['mesh_lon'] = ((df['lon'] // lon_step) * lon_step).round(4)

# メッシュIDの生成（グルーピングキーとして使いやすい文字列）
df['mesh_id'] = df['mesh_lat'].astype(str) + '_' + df['mesh_lon'].astype(str)

# 3. カラムの並べ替え（使いやすい順序に）
output_columns = ['timestamp', 'mesh_id', 'lat', 'lon', 'mesh_lat', 'mesh_lon', 'text']
df_output = df[output_columns]

# 4. CSV形式で先頭を表示（確認用）
print(df_output.head(10).to_csv(index=False))

# (仮想的に)保存する場合のコード
df_output.to_csv('kyoto_tweets_with_mesh.csv', index=False, encoding='utf-8-sig')