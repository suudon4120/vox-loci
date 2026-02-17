import pandas as pd
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import argparse
import sys

# ==========================================
# ⚙️ 設定
# ==========================================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BATCH_ID = input("Batch IDを入力: ") 

parser = argparse.ArgumentParser(description="Batch APIによる処理の結果を元データと結合するプログラム")
parser.add_argument("--input", type=str, help="処理対象のファイルパス")
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
# 出力ファイル
input_filename = os.path.basename(INPUT_PATH)
root, ext = os.path.splitext(input_filename)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "interim", f"{root}_batch_tagged.csv")

def main():
    print(f"🔍 Batch ID: {BATCH_ID} のステータスを確認中...")
    
    try:
        batch_job = client.batches.retrieve(BATCH_ID)
        print(f"Status: {batch_job.status}")

        if batch_job.status == "failed":
            print("❌ 処理が失敗しました。エラーを確認してください。")
            print(batch_job.errors)
            return
            
        if batch_job.status != "completed":
            print("⏳ まだ処理中です。時間を置いて再実行してください。")
            return

        print("🎉 処理完了！結果ファイルをダウンロードします...")
        result_file_id = batch_job.output_file_id
        file_response = client.files.content(result_file_id)
    except Exception as e:
        print(f"❌️エラーが発生しました: {e}")    
        return
    
    # --- 結果データの解析 ---
    print("📂 AIの分析結果を展開中...")
    ai_results = []
    
    # 結果のJSONLを1行ずつ処理
    for line in file_response.text.strip().split('\n'):
        if not line: continue
        try:
            data = json.loads(line)
            
            # エラーレスポンスでないか確認
            if data.get('response', {}).get('status_code') != 200:
                print(f"⚠️ Error in batch item: {data.get('custom_id')}")
                continue
                
            # JSONの中身を取り出す
            content_str = data['response']['body']['choices'][0]['message']['content']
            content_json = json.loads(content_str)
            
            # リスト形式の結果を展開してフラットにする
            # output: {"results": [{"id": 0, "is_location..."}, {"id": 1, ...}]}
            for item in content_json.get('results', []):
                ai_results.append(item)
        except json.JSONDecodeError:
            print("⚠️JSONデコードエラースキップ")
            continue
            
    # AI結果をDataFrame化 (IDとタグのみ)
    df_ai = pd.DataFrame(ai_results)
    # idカラムを整数型に変換（マージ用）
    if 'id' in df_ai.columns:
        df_ai['id'] = df_ai['id'].astype(int)
    print(f"✅ AI分析結果: {len(df_ai)} 件取得")

    # --- 元データの読み込み ---
    print("📖 元データを読み込んでいます...")
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    original_data = []
    # 列数判定用
    sample_line = lines[0].strip().split('\t')
    col_count = len(sample_line)
    
    print(f"ℹ️ 入力データの列数: {col_count}列")
    
    for i, line in enumerate(lines):
        line = line.strip()
        parts = line.split('\t')
        
        # 共通のID（行番号）
        item = {"id": i}
        
        # 列数による分岐処理
        if len(parts) >= 7:  # all100.txt 形式 (ID, Time, User, Lang, Text, Lat, Lon)
            item.update({
                "tweet_id": parts[0],
                "timestamp": parts[1],
                "user_name": parts[2],
                "language": parts[3],
                "text": parts[4],
                "latitude": parts[5],
                "longitude": parts[6]
            })
        elif len(parts) >= 5: # KYOTO2_100.txt 形式 (Time, Lang, Lat, Lon, Text)
            item.update({
                "timestamp": parts[0],
                "language": parts[1],
                "latitude": parts[2],
                "longitude": parts[3],
                "text": parts[4]
            })
        else:
            # フォーマット不明または空行に近い場合
            item["text"] = line

        original_data.append(item)
        
    df_original = pd.DataFrame(original_data)

    # --- 結合 (Merge) ---
    print("🔗 元データと分析結果を結合中...")
    
    if 'id' not in df_ai.columns:
        print("❌ AIの結果に 'id' カラムが見つかりません。プロンプト出力を確認してください。")
        return

    # IDをキーにして結合 (left join: AIの結果がない行があっても元データは残す)
    df_final = pd.merge(df_original, df_ai, on='id', how='left')
    
    # --- 保存 ---
   # 保存したいカラムの優先順位定義
    desired_order = [
        'id', 'tweet_id', 'timestamp', 'user_name', 'language', 
        'latitude', 'longitude', 'text',
        'is_location_related', 'subjectivity', 'sentiment_or_noise', 'user_attribute'
    ]
    
    # 実際にデータフレームに存在するカラムのみを抽出
    final_cols = [c for c in desired_order if c in df_final.columns]
    
    # 残りのカラム（もしあれば）を後ろに追加
    remaining_cols = [c for c in df_final.columns if c not in final_cols]
    final_cols.extend(remaining_cols)
    
    df_final[final_cols].to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')
    print(f"\n✨ 完了しました！ '{OUTPUT_PATH}' を確認してください。")

if __name__ == "__main__":
    main()