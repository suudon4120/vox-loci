import pandas as pd
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# ==========================================
# ⚙️ 設定
# ==========================================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BATCH_ID = input("Batch IDを入力: ") 

INPUT_FILE = "KYOTO2.txt"
root, ext = os.path.splitext(INPUT_FILE)
FINAL_OUTPUT_CSV = f"{root}_batch_tagged.csv"

def main():
    print(f"🔍 Batch ID: {BATCH_ID} のステータスを確認中...")
    
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
    
    # --- 1. 結果データの解析 ---
    print("📂 AIの分析結果を展開中...")
    ai_results = []
    
    # 結果のJSONLを1行ずつ処理
    for line in file_response.text.strip().split('\n'):
        if not line: continue
        data = json.loads(line)
        
        # エラーレスポンスでないか確認
        if data['response']['status_code'] != 200:
            print(f"⚠️ Error in batch item: {data['custom_id']}")
            continue
            
        # JSONの中身を取り出す
        content_str = data['response']['body']['choices'][0]['message']['content']
        content_json = json.loads(content_str)
        
        # リスト形式の結果を展開してフラットにする
        # output: {"results": [{"id": 0, "is_location..."}, {"id": 1, ...}]}
        for item in content_json.get('results', []):
            ai_results.append(item)
            
    # AI結果をDataFrame化 (IDとタグのみ)
    df_ai = pd.DataFrame(ai_results)
    print(f"✅ AI分析結果: {len(df_ai)} 件取得")

    # --- 2. 元データの読み込み ---
    print("📖 元データを読み込んでいます...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    original_data = []
    for i, line in enumerate(lines):
        line = line.strip()
        parts = line.split('\t') # タブ区切りと想定
        
        if len(parts) >= 5:
            item = {"id": i, "timestamp": parts[0], "language": parts[1], "latitude": parts[2], "longitude": parts[3], "text": parts[4]}
        else:
            item = {"id": i, "text": line} # フォーマット崩れ対応
        original_data.append(item)
        
    df_original = pd.DataFrame(original_data)

    # --- 3. 結合 (Merge) ---
    print("🔗 元データと分析結果を結合中...")
    
    # IDをキーにして結合 (left join: AIの結果がない行があっても元データは残す)
    df_final = pd.merge(df_original, df_ai, on='id', how='left')
    
    # --- 4. 保存 ---
    # カラム順序を整理
    cols = ['id', 'timestamp', 'language', 'latitude', 'longitude', 'text', 
            'is_location_related', 'subjectivity', 'sentiment_or_noise', 'user_attribute']
    # 存在しないカラムは除外
    cols = [c for c in cols if c in df_final.columns]
    
    df_final[cols].to_csv(FINAL_OUTPUT_CSV, index=False)
    print(f"\n✨ 完了しました！ '{FINAL_OUTPUT_CSV}' を確認してください。")

if __name__ == "__main__":
    main()