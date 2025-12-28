import pandas as pd

# データの読み込み
df = pd.read_csv("KYOTO2_batch_merged_tagged_cleaned_mesh.csv")

# メッシュコードごとにグループ化して件数を取得
mesh_counts = df.groupby("mesh_code").size().reset_index(name="tweet_count")

# --- 統計量の算出 ---
# 全ツイート数
total_tweets = len(df)
# 全メッシュ数
total_meshes = len(mesh_counts)
# 各種統計量
max_val = mesh_counts["tweet_count"].max()
min_val = mesh_counts["tweet_count"].min()
mean_val = mesh_counts["tweet_count"].mean()
std_val = mesh_counts["tweet_count"].std()
median_val = mesh_counts["tweet_count"].median()

# 上位5メッシュの取得
top_5_meshes = mesh_counts.sort_values(by="tweet_count", ascending=False).head(5)

# --- 結果の出力 ---
print(f"全ツイート数: {total_tweets}")
print(f"全メッシュ数: {total_meshes}")
print(f"最大値: {max_val}")
print(f"最小値: {min_val}")
print(f"平均値: {mean_val}")
print(f"標準偏差: {std_val}")
print(f"中央値: {median_val}")
print("\n上位5メッシュ:")
print(top_5_meshes)

# --- テキスト統合ファイルの作成 ---
# mesh_text_summary = df.groupby('mesh_code')['text'].apply(lambda x: ' /// '.join(x)).reset_index(name='aggregated_text')
# result_df = pd.merge(mesh_counts, mesh_text_summary, on='mesh_code')
# result_df.to_csv('mesh_text_summary.csv', index=False)
