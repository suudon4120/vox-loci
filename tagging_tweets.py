import pandas as pd
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Literal
import time
import os
from dotenv import load_dotenv

# ==========================================
# ⚙️ 設定セクション
# ==========================================

# .envファイルから環境変数を読み込む
# セキュリティ確保のため、APIキーはコードに直接書かず .env ファイルで管理します
load_dotenv()

# テストモードの設定
# Trueにすると、TEST_LIMITで指定した件数だけ処理して停止します。
# 本番実行時は False に変更してください。
TEST_MODE = True
TEST_LIMIT = 500

# 入出力ファイルの設定
INPUT_FILE = "KYOTO2.txt"
# 出力ファイル名
root, ext = os.path.splitext(INPUT_FILE)
# テストモード時はファイル名を分けて、本番用データの上書きを防ぎます
OUTPUT_FILE = f"{root}_{TEST_LIMIT}_tagged_test.csv" if TEST_MODE else f"{root}_tagged.csv"

# APIリクエストの設定
# クライアントサイド・バッチ: 1回のリクエストに含めるツイート数
# これにより通信回数とシステムプロンプトのトークン消費を節約します
BATCH_SIZE = 20

# 使用するOpenAIのモデル名
MODEL_NAME = "gpt-5-mini"

# 環境変数からAPIキーを取得
API_KEY = os.getenv("OPENAI_API_KEY")
# APIキーが読み込めていない場合は安全のためエラー終了させる
if not API_KEY:
    raise ValueError("❌ エラー: APIキーが見つかりません。")

# OpenAIクライアントの初期化
client = OpenAI(api_key=API_KEY)

# ==========================================
# 📐 データ構造定義 (Pydantic)
# ==========================================

# AIに出力させたいJSONデータの構造（スキーマ）を定義します。
# OpenAIの Structured Outputs 機能により、この形式が厳密に守られます。

class TweetAnalysis(BaseModel):
    id: int  # 元データの行番号（IDとして使用）
    is_location_related: bool  # 場所に関連する情報が含まれるか
    subjectivity: Literal["主観", "客観", "N/A"]  # 主観/客観の分類
    sentiment_or_noise: str  # ポジティブ/ネガティブ、またはノイズの種類
    user_attribute: Literal["住民", "観光客", "それ以外", "N/A"]  # 投稿者の属性推定

class BatchAnalysisResult(BaseModel):
    results: List[TweetAnalysis]  # 複数件の分析結果をリストとして保持

# ==========================================
# 🧠 AI分析処理関数
# ==========================================
def analyze_tweets_batch(batch_data):
    # AIには「ID」と「本文」だけを渡して分析させる
    tweets_text = "\n".join([f"ID:{item['id']} Text:{item['text']}" for item in batch_data])
    
    system_prompt = """
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
       - ノイズ(クーポン情報): 「クーポン」「割引」などの機械的な広告。
       - ノイズ(単体場所情報): 「I'm at ～」「～なう」のみで文脈がないもの。
       - ノイズ(広告・宣伝): 求人やイベント告知など。
       - ノイズ(客観的記述): 移動報告や事実の伝達のみで感情が含まれないもの。
       - ポジティブ: 主観的な内容が肯定的、好意的なもの。
       - ネガティブ: 主観的な内容が否定的、不満、不快なもの。
       - N/A: 場所関連情報がFalseの場合。

    4. user_attribute (ユーザー属性):
       - 住民: 通勤、通学、近所の日常的な行動、生活感のある文脈。
       - 観光客: 旅行中、「到着」「久々」、観光地やイベントへの感動。
       - それ以外: 判断困難、またはノイズのみの場合。
       - N/A: 場所関連情報がFalseの場合。
    """

    completion = client.beta.chat.completions.parse(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},  # ここに詳細な指示変数を渡す
            {"role": "user", "content": tweets_text},
        ],
        response_format=BatchAnalysisResult,
    )
    return completion.choices[0].message.parsed

# ==========================================
# 🚀 メイン実行処理
# ==========================================
def main():
    print(f"🚀 開始: {'テストモード' if TEST_MODE else '本番モード'}")
    print(f"📂 出力先: {OUTPUT_FILE}")
    print(f"🤖 使用モデル: {MODEL_NAME}")

    # 1. 途中再開機能
    processed_ids = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            # 高速化のため、'id'列だけを読み込んでメモリ消費を抑える
            df_existing = pd.read_csv(OUTPUT_FILE, usecols=['id'])
            processed_ids = set(df_existing['id'])
            print(f"🔄 既存データ {len(processed_ids)} 件をスキップします。")
        except ValueError:
            pass

    # 2. 入力データの読み込みと解析
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"❌ エラー: 入力ファイル '{INPUT_FILE}' が見つかりません。")
        return

    # 元データをパースしてリスト化しておく
    original_data_list = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line: continue
        
        # タブ区切りで分割 (フォーマットに合わせて調整してください)
        parts = line.split('\t')
        
        # データ形式が想定通りかチェック (5列以上あるか)
        if len(parts) >= 5:
            item = {
                "id": i,
                "timestamp": parts[0],
                "language": parts[1],
                "latitude": parts[2],
                "longitude": parts[3],
                "text": parts[4]  # 5列目が本文と仮定
            }
        else:
            # フォーマットが違う場合は行全体を本文とするなどの救済措置
            item = {
                "id": i,
                "timestamp": "", "language": "", "latitude": "", "longitude": "",
                "text": line
            }
        original_data_list.append(item)

    batch_input = []    # AIに送る用 (IDとTextのみ)
    batch_original = [] # 後で結合する用 (全データ)
    
    # 3. ループ処理
    for i, item in enumerate(original_data_list):
        # [テストモード判定]
        # 設定した件数を超えたらループを抜けて終了
        if TEST_MODE and i >= TEST_LIMIT:
            break
        # [スキップ判定]
        # すでに処理済みの行（出力ファイルにあるID）はスキップ
        if item['id'] in processed_ids:
            continue
        
        # バッチリストにデータを追加
        batch_input.append({"id": item['id'], "text": item['text']})
        batch_original.append(item)

        if len(batch_input) >= BATCH_SIZE:
            try:
                print(f"⏳ Processing batch ending at line {item['id']}...")
                
                # AI分析実行
                result = analyze_tweets_batch(batch_input)
                
                # --- データの結合処理 ---
                # 1. 元データのDataFrame作成
                df_orig = pd.DataFrame(batch_original)
                
                # 2. AI結果のDataFrame作成
                df_ai = pd.DataFrame([r.model_dump() for r in result.results])
                
                # 3. IDをキーにして結合 (inner join)
                df_merged = pd.merge(df_orig, df_ai, on='id')
                
                # CSVに追記保存
                write_header = not os.path.exists(OUTPUT_FILE)
                # カラムの順番を整える（見やすくする）
                cols = ['id', 'timestamp', 'language', 'latitude', 'longitude', 'text', 
                        'is_location_related', 'subjectivity', 'sentiment_or_noise', 'user_attribute']
                # 存在しないカラムがある場合のエラー回避
                cols = [c for c in cols if c in df_merged.columns]
                
                df_merged[cols].to_csv(OUTPUT_FILE, mode='a', header=write_header, index=False)
                
                batch_input = [] 
                batch_original = []
                time.sleep(0.5)

            except Exception as e:
                print(f"❌ Error at line {item['id']}: {e}")
                time.sleep(5)
    
    # 残りのバッチ処理
    if batch_input:
        try:
            print(f"⏳ Processing final batch...")
            result = analyze_tweets_batch(batch_input)
            
            df_orig = pd.DataFrame(batch_original)
            df_ai = pd.DataFrame([r.model_dump() for r in result.results])
            df_merged = pd.merge(df_orig, df_ai, on='id')
            
            write_header = not os.path.exists(OUTPUT_FILE)
            cols = ['id', 'timestamp', 'language', 'latitude', 'longitude', 'text', 
                    'is_location_related', 'subjectivity', 'sentiment_or_noise', 'user_attribute']
            cols = [c for c in cols if c in df_merged.columns]
            
            df_merged[cols].to_csv(OUTPUT_FILE, mode='a', header=write_header, index=False)
            print("✅ Final batch done.")
        except Exception as e:
            print(f"❌ Error at final batch: {e}")

    print("\n✨ 処理が完了しました。")

if __name__ == "__main__":
    main()