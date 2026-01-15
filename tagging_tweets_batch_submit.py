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
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("❌️ エラー: APIキーが見つかりません。")
client = OpenAI(api_key=API_KEY)

parser = argparse.ArgumentParser(description="ツイートを読み込んでタグ付けのリクエストを行うプログラム")
parser.add_argument("--input", type=str, help="処理対象のファイルパス")
parser.add_argument("--chunk_size", type=int, default=50, help="1回のリクエストで処理する件数 (デフォルト: 50)")
parser.add_argument("--model", type=str, default="gpt-5-nano", help="使用するモデル名 (デフォルト: gpt-5-nano)")
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

CHUNK_SIZE = args.chunk_size
MODEL_NAME = args.model
BATCH_REQUEST_FILE = "batch_input.jsonl"


# ==========================================
# 🧠 システムプロンプト (判断基準)
# ==========================================
SYSTEM_PROMPT = """
    あなたはツイート分類の専門家です。以下の基準に従って、渡されたツイートリストを分析し、指定のJSON形式で出力してください。

    【判断基準】
    1. is_location_related (場所関連情報):
       - True: 具体的な地名、イベント名を含むものに加え、「ここの店員の対応が良い」「坂道で疲れる」など、ツイートの内容がその地点と関連するもの。
       - False: 場所に関係のない思想、概念、感想、評価、その他完全に場所と切り離された情報のみを含むもの。

    2. subjectivity (主観/客観):
       - 主観: 感情（嬉しい、つらい、好き）、評価（うまい、最高）、個人的な意思を含むもの。
       - 客観: 事実の報告、状況説明、定型的なチェックイン、機械的な通知。
       - N/A: 場所関連情報がFalseの場合。

    3. sentiment_or_noise (ポジティブ/ネガティブ/ノイズ):
       - ノイズ: クーポンや求人、イベント告知などの機械的な広告。「I'm at ～」「～なう」「〜イマココ」などのみで文脈がないもの。移動報告や事実の伝達のみで感情が含まれないもの。
       - ポジティブ: 主観的な内容が肯定的、好意的なもの。
       - ネガティブ: 主観的な内容が否定的、不満、不快なもの。
       - N/A: 場所関連情報がFalseの場合。

    4. user_attribute (ユーザー属性):
       - 住民: 通勤、通学、近所の日常的な行動、生活感のある文脈。
       - 観光客: 旅行中、「到着」「久々」、観光地やイベントへの感動。
       - それ以外: 判断困難、またはノイズのみの場合。
       - N/A: 場所関連情報がFalseの場合。
    """

# 出力フォーマット (JSON Schema)
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
                            "id": {"type": "integer", "description": "入力されたIDをそのまま返す"},
                            "is_location_related": {"type": "boolean"},
                            "subjectivity": {"type": "string", "enum": ["主観", "客観", "N/A"]},
                            "sentiment_or_noise": {"type": "string", "enum": ["ポジティブ", "ネガティブ", "ノイズ", "N/A"]},
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

def main():
    print("🚀 データを読み込み中...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"エラー: ファイル '{INPUT_FILE}' が見つかりません。")
        sys.exit()
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # データをチャンク（塊）に分割
    requests = []
    current_chunk = []
    
    print(f"📦 全 {len(lines)} 行を {CHUNK_SIZE} 件ずつのバッチリクエストに変換します...")

    with open(BATCH_REQUEST_FILE, 'w', encoding='utf-8') as jsonl_f:
        for i, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            
            parts = line.split('\t')
            # 5列目(インデックス4)がある場合はそれを採用、なければ行全体
            text_content = parts[4] if len(parts) >= 5 else line
            
            # IDと抽出したテキストのペアを作成
            current_chunk.append(f"ID:{i} Text:{text_content}")
            
            # チャンクサイズに達したら1つのリクエストとして書き出し
            if len(current_chunk) >= CHUNK_SIZE or i == len(lines) - 1:
                if not current_chunk: continue
                
                # プロンプト作成（複数のツイートを改行で結合）
                user_content = "\n".join(current_chunk)
                
                # APIリクエスト構造の作成
                # custom_id は後で紐付けに使えます（ここでは開始行番号を使用）
                start_id = i - len(current_chunk) + 1
                request_obj = {
                    "custom_id": f"batch_start_{start_id}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": MODEL_NAME,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_content}
                        ],
                        "response_format": RESPONSE_SCHEMA
                    }
                }
                
                jsonl_f.write(json.dumps(request_obj, ensure_ascii=False) + "\n")
                current_chunk = []

    print("📤 ファイルをOpenAIにアップロード中...")
    batch_file = client.files.create(
        file=open(BATCH_REQUEST_FILE, "rb"),
        purpose="batch"
    )

    print(f"🚀 Batch処理を開始します (File ID: {batch_file.id})...")
    batch_job = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={"description": "tweet_analysis_v1_textonly"}
    )

    print(f"\n✅ 送信完了！")
    print(f"Batch ID: {batch_job.id}")
    print("--------------------------------------------------")
    print("このIDを控えておいてください。受信スクリプトで使います。")


if __name__ == "__main__":
    main()