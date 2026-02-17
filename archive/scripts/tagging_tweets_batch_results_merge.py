import pandas as pd
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# ==========================================
# ⚙️ 設定エリア
# ==========================================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ★重要★ ここに「最初のバッチID」と「再送したバッチID」の両方をリストに入れます
BATCH_IDS = [
    "batch_693fc4b6ec08819099b31c516ded4ff8",  # 1回目 (途中まで成功)
    "batch_69401ddb27988190b7a5d597b7be25e2",  # 2回目 (リカバリ分)
]

INPUT_FILE = "KYOTO2.txt"
FINAL_OUTPUT_CSV = "KYOTO2_batch_tagged.csv"

# ==========================================
# 処理ロジック
# ==========================================
def main():
    print(f"🚀 {len(BATCH_IDS)} 個のバッチ結果を統合します...")
    
    all_ai_results = []

    # --- 1. 全てのバッチIDをループして結果を回収 ---
    for batch_id in BATCH_IDS:
        print(f"\n🔍 Batch ID: {batch_id} の取得中...")
        
        try:
            batch_job = client.batches.retrieve(batch_id)
            print(f"   Status: {batch_job.status}")

            # 完了していないものがあれば警告（でも処理は続ける）
            if batch_job.status != "completed":
                print(f"   ⚠️ 注意: このバッチは完了していません (Status: {batch_job.status})。スキップします。")
                continue
            
            if not batch_job.output_file_id:
                print("   ⚠️ 出力ファイルがありません（全件失敗の可能性があります）。")
                continue

            # 結果ファイルのダウンロード
            print("   📥 ダウンロード中...")
            content_response = client.files.content(batch_job.output_file_id)
            file_content = content_content = content_response.text
            
            # データの解析
            count = 0
            for line in file_content.strip().split('\n'):
                if not line: continue
                data = json.loads(line)
                
                # APIエラーでない場合のみ処理
                if data['response']['status_code'] == 200:
                    try:
                        # AIの回答JSONを取り出す
                        body_str = data['response']['body']['choices'][0]['message']['content']
                        body_json = json.loads(body_str)
                        
                        # リストを展開して結果リストに追加
                        for item in body_json.get('results', []):
                            all_ai_results.append(item)
                            count += 1
                    except Exception as e:
                        print(f"   ⚠️ Parse Error: {e}")
            
            print(f"   ✅ {count} 件のデータを回収しました。")

        except Exception as e:
            print(f"   ❌ エラーが発生しました: {e}")

    # --- 2. データの整理と重複除去 ---
    print("\n📊 データの整理中...")
    df_ai = pd.DataFrame(all_ai_results)
    
    if df_ai.empty:
        print("❌ AIの分析結果が1件も取得できませんでした。終了します。")
        return

    # IDの型を整数に統一
    df_ai['id'] = df_ai['id'].astype(int)

    # 重複の削除 (もし再送分と被っていても、後勝ちで上書きするように設定)
    # keep='last' にすることで、リストの後ろ（新しいバッチ）の結果を優先します
    df_ai = df_ai.drop_duplicates(subset='id', keep='last')
    
    print(f"✅ AI分析データの合計: {len(df_ai)} 件 (ユニーク)")

    # --- 3. 元データとの結合 ---
    print("📖 元データを読み込んでいます...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    original_data = []
    for i, line in enumerate(lines):
        line = line.strip()
        parts = line.split('\t')
        
        # タブ区切り箇所のパース
        if len(parts) >= 5:
            item = {"id": i, "timestamp": parts[0], "language": parts[1], "latitude": parts[2], "longitude": parts[3], "text": parts[4]}
        else:
            item = {"id": i, "text": line}
        original_data.append(item)
        
    df_original = pd.DataFrame(original_data)
    df_original['id'] = df_original['id'].astype(int)

    print("🔗 結合中...")
    # 元データにAI結果をマージ (左外部結合)
    df_final = pd.merge(df_original, df_ai, on='id', how='left')

    # --- 4. 保存 ---
    cols = ['id', 'timestamp', 'language', 'latitude', 'longitude', 'text', 
            'is_location_related', 'subjectivity', 'sentiment_or_noise', 'user_attribute']
    cols = [c for c in cols if c in df_final.columns]
    
    df_final[cols].to_csv(FINAL_OUTPUT_CSV, index=False)
    
    # --- 5. 最終結果レポート ---
    print("\n" + "="*40)
    print(f"🎉 全処理完了！")
    print(f"📂 出力ファイル: {FINAL_OUTPUT_CSV}")
    print(f"📊 データ総数: {len(df_final)}")
    
    # 未処理（NaN）の数を数える
    nan_count = df_final['is_location_related'].isna().sum()
    if nan_count > 0:
        print(f"⚠️ 注意: まだ分析できていない行が {nan_count} 件あります。")
        print("   (原因: Batch APIのエラー、またはAIの生成漏れ)")
    else:
        print("✨ すべての行に分析データが入りました！")
    print("="*40)

if __name__ == "__main__":
    main()