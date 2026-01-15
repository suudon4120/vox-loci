import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 前回のBatch ID (途中まで成功したもの)
PREV_BATCH_ID = "batch_693fc4b6ec08819099b31c516ded4ff8" 

def get_completed_indices():
    print(f"🔍 Batch ID: {PREV_BATCH_ID} の成功済みIDを確認します...")
    
    batch_job = client.batches.retrieve(PREV_BATCH_ID)
    if not batch_job.output_file_id:
        print("⚠️ 出力ファイルがありません。全件失敗した可能性があります。")
        return set()

    print("📥 結果ファイルをダウンロード中...")
    content_response = client.files.content(batch_job.output_file_id)
    file_content = content_response.text
    
    completed_indices = set()
    
    # 結果ファイルを解析して、処理済みの「元の行番号」を特定
    for line in file_content.strip().split('\n'):
        if not line: continue
        data = json.loads(line)
        
        # custom_id = "batch_start_1230" 形式を想定
        if data['response']['status_code'] == 200:
            custom_id = data['custom_id']
            start_index = int(custom_id.split('_')[-1])
            
            # このバッチに含まれていた10件分のインデックスを全て追加
            # (前回のCHUNK_SIZEは10だったので)
            for i in range(10): 
                completed_indices.add(start_index + i)
                
    print(f"✅ 成功済みツイート数: {len(completed_indices)} 件")
    return completed_indices

if __name__ == "__main__":
    indices = get_completed_indices()
    # 確認のため保存
    with open("completed_indices.txt", "w") as f:
        for idx in sorted(indices):
            f.write(f"{idx}\n")
    print("completed_indices.txt に保存しました。")