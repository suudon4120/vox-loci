import json
import os
import math
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==========================================
# ⚙️ 新しい設定 (ここで節約設定にする！)
# ==========================================
INPUT_DATA_FILE = "KYOTO2.txt"
NEW_BATCH_FILE = "batch_input_restart.jsonl"

# ★ ここで設定を変更してOKです ★
NEW_CHUNK_SIZE = 50           # 10 → 50 に増やして節約！
NEW_MODEL_NAME = "gpt-5-nano" # 安いモデルに変更！

# ★ プロンプトも短縮版に変更してOK ★
NEW_SYSTEM_PROMPT = """
ツイートリストを分析し指定のJSONで出力せよ。
【判断基準】
1. is_location_related:
   - True: 地名・イベント名、または「店員の対応」「坂道」等その場所に依存する内容。
   - False: 場所と無関係な概念や感想のみ。
2. subjectivity:
   - 主観: 感情・評価・意思。
   - 客観: 事実・報告・定型・機械的通知。
3. sentiment_or_noise:
   - ノイズ: 「クーポン/割引」(クーポン情報)、「〜なう/I'm at」のみ(単体場所情報)、求人/告知(広告・宣伝)、感情なき移動報告(客観的記述)。
   - ポジティブ: 主観的な肯定。
   - ネガティブ: 主観的な否定。
4. user_attribute:
   - 住民: 通勤通学・日常・生活感。
   - 観光客: 旅行・到着・非日常。
   - それ以外: 判断困難またはbotなど。
※is_location_relatedがFalseの場合、他項目は全て"N/A"。
"""

# スキーマは変えないこと（結合できなくなるため）
RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "tweet_analysis_result",
        "schema": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "is_location_related": {"type": "boolean"},
                            "subjectivity": {"type": "string", "enum": ["主観", "客観", "N/A"]},
                            "sentiment_or_noise": {"type": "string", "enum": ["ポジティブ", "ネガティブ", "ノイズ(クーポン情報)", "ノイズ(単体場所情報)", "ノイズ(広告・宣伝)", "ノイズ(客観的記述)", "N/A"]},
                            "user_attribute": {"type": "string", "enum": ["住民", "観光客", "それ以外", "N/A"]}
                        },
                        "required": ["id", "is_location_related", "subjectivity", "sentiment_or_noise", "user_attribute"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["results"],
            "additionalProperties": False
        },
        "strict": True
    }
}

COMPLETED_INDICES_FILE = "completed_indices.txt"

def main():
    print("🚀 差分リスタート処理を開始します...")

    # 1. 成功済みIDを読み込む
    completed_indices = set()
    if os.path.exists(COMPLETED_INDICES_FILE):
        with open(COMPLETED_INDICES_FILE, 'r') as f:
            for line in f:
                completed_indices.add(int(line.strip()))
    print(f"✅ 成功済み件数: {len(completed_indices)} 件 -> これらはスキップします。")

    # 2. 元データを読み込み
    with open(INPUT_DATA_FILE, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
    
    total_lines = len(all_lines)
    
    # 3. 未処理データのリストを作成
    # (行番号, テキスト) のタプルで保持
    pending_items = []
    for i in range(total_lines):
        if i not in completed_indices:
            pending_items.append((i, all_lines[i]))
            
    print(f"📋 今回の処理対象: {len(pending_items)} 行")

    # 4. JSONL作成 (NEW_CHUNK_SIZE ごとにまとめる)
    with open(NEW_BATCH_FILE, 'w', encoding='utf-8') as f_out:
        
        # pending_items を chunk_size ずつ取り出す
        for i in range(0, len(pending_items), NEW_CHUNK_SIZE):
            chunk = pending_items[i : i + NEW_CHUNK_SIZE]
            
            # バッチIDは、そのチャンクの「先頭データの元の行番号」を使うと管理しやすい
            first_real_id = chunk[0][0]
            
            chunk_text_list = []
            for real_id, line in chunk:
                # --- テキスト抽出 ---
                parts = line.strip().split('\t')
                text_content = parts[4] if len(parts) >= 5 else line.strip()
                # ------------------
                chunk_text_list.append(f"ID:{real_id} Text:{text_content}")

            user_content = "\n".join(chunk_text_list)
            
            request_obj = {
                "custom_id": f"batch_diff_{first_real_id}", # ID重複を避けるため prefix を変更
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": NEW_MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": NEW_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content}
                    ],
                    "response_format": RESPONSE_SCHEMA
                }
            }
            f_out.write(json.dumps(request_obj, ensure_ascii=False) + "\n")
    print(f"✅ 最適化バッチファイル作成完了: {NEW_BATCH_FILE}")

    # 5. 送信
    est_requests = math.ceil(len(pending_items) / NEW_CHUNK_SIZE)
    print(f"📦 予想リクエスト回数: {est_requests} 回")
    
    confirm = input(">> OpenAIに送信しますか？ (y/n): ")
    if confirm.lower() == 'y':
        print("📤 アップロード中...")
        batch_file = client.files.create(
            file=open(NEW_BATCH_FILE, "rb"),
            purpose="batch"
        )
        
        print("🚀 Batch処理を開始します...")
        batch_job = client.batches.create(
            input_file_id=batch_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={"description": "tweet_analysis_restart_textonly"}
        )
        print(f"✅ 再送完了！ New Batch ID: {batch_job.id}")
    else:
        print("中止しました。")

if __name__ == "__main__":
    main()