import json
import os
from openai import OpenAI
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ★ここにBatch IDを入れてください
BATCH_ID = "batch_693cf334b2c08190a850afb4a1bc3f6a" 

def diagnose_batch_results():
    print(f"🔍 Batch ID: {BATCH_ID} の診断を開始します...")
    
    try:
        batch_job = client.batches.retrieve(BATCH_ID)
        print(f"Status: {batch_job.status}")
        
        if batch_job.status != "completed":
            print("⚠️ バッチ処理が完了していません。")
            return

        # 結果ファイルのダウンロード
        print("📥 結果ファイルをダウンロード中...")
        result_file_id = batch_job.output_file_id
        error_file_id = batch_job.error_file_id
        
        content_response = client.files.content(result_file_id)
        raw_content = content_response.text
        
        # 生ログを保存（念のため）
        with open("debug_batch_output.jsonl", "w", encoding="utf-8") as f:
            f.write(raw_content)
        print("📄 'debug_batch_output.jsonl' に生の出力を保存しました。")

        # 解析
        total_items_found = 0
        error_count = 0
        successful_ids = []

        for line in raw_content.strip().split('\n'):
            if not line: continue
            data = json.loads(line)
            
            # 1. APIレベルのエラーチェック
            if data['response']['status_code'] != 200:
                print(f"❌ API Error (Request ID: {data['custom_id']}): {data['response']['status_code']}")
                error_count += 1
                continue
            
            # 2. AI生成内容のチェック
            try:
                body = data['response']['body']['choices'][0]['message']['content']
                parsed = json.loads(body)
                
                # リスト内の結果数を確認
                results = parsed.get('results', [])
                total_items_found += len(results)
                for item in results:
                    successful_ids.append(item.get('id'))
                    
            except Exception as e:
                print(f"⚠️ JSON Parse Error in {data['custom_id']}: {e}")

        print("-" * 30)
        print("📊 診断結果")
        print(f"  - 正常なレスポンス内のツイート数: {total_items_found}")
        print(f"  - APIエラー数: {error_count}")
        
        if batch_job.request_counts:
            print(f"  - (参考) 送信したリクエスト総数: {batch_job.request_counts.total}")
        
        if successful_ids:
            print(f"  - 取得できたIDの例: {successful_ids[:10]}")
            print(f"  - IDの型: {type(successful_ids[0])}")
        else:
            print("⚠️ 有効なIDが一つも取得できませんでした。")

        # エラーファイルがある場合（リクエスト自体が不正だった場合）
        if error_file_id:
            print("\n🚨 エラーファイルが存在します（入力形式ミスの可能性）")
            err_content = client.files.content(error_file_id).text
            print(err_content[:500])

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    diagnose_batch_results()