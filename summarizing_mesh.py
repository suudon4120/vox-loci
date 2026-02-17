import pandas as pd
import argparse
import sys
import os

# ==========================================
# ⚙️ 設定
# ==========================================
parser = argparse.ArgumentParser(description="メッシュごとにツイートを集計し、既存の集計ファイルに統合するプログラム")
parser.add_argument("--input", type=str, help="処理対象のファイルパス")
parser.add_argument("--output", type=str, default="mesh_tweets_integrated.csv", help="出力/統合先のファイルパス (デフォルト: mesh_tweets_integrated.csv)")
args = parser.parse_args()

# 入力ファイルの取得
if args.input:
    INPUT_FILE = args.input
else:
    INPUT_FILE = input(">>処理する新規ファイル名を入力してください: ").strip()

if not os.path.exists(INPUT_FILE):
    print(f"❌ 入力ファイル '{INPUT_FILE}' が見つかりません。")
    sys.exit()

OUTPUT_FILE = args.output

def main():
    print(f"📖 新規データを読み込んでいます: {INPUT_FILE}")
    try:
        df_new_raw = pd.read_csv(INPUT_FILE)
    except Exception as e:
        print(f"❌ 読み込みエラー: {e}")
        return

    # 必要なカラムの確認
    if 'mesh_code' not in df_new_raw.columns:
        print("❌ エラー: 入力ファイルに 'mesh_code' カラムが見つかりません。")
        return
    
    # 欠損値処理
    df_new_raw = df_new_raw.dropna(subset=['mesh_code'])
    if 'text' in df_new_raw.columns:
        df_new_raw['text'] = df_new_raw['text'].fillna("").astype(str)
    else:
        df_new_raw['text'] = ""

    # --- 1. 新規データの集計 ---
    print("📊 新規データの集計中...")
    
    # カウント集計
    new_counts = df_new_raw.groupby('mesh_code').size().reset_index(name='tweet_count')
    
    # テキスト結合集計
    new_texts = df_new_raw.groupby('mesh_code')['text'].apply(lambda x: ' /// '.join(x)).reset_index(name='aggregated_text')
    
    # 結合して新規の集計データフレームを作成
    df_new_summary = pd.merge(new_counts, new_texts, on='mesh_code')

    # --- 2. 既存ファイルとの統合（マージ） ---
    if os.path.exists(OUTPUT_FILE):
        print(f"🔄 既存の集計ファイル '{OUTPUT_FILE}' を読み込んで統合します...")
        try:
            df_existing = pd.read_csv(OUTPUT_FILE)
            
            # カラムチェック
            required_cols = {'mesh_code', 'tweet_count', 'aggregated_text'}
            if not required_cols.issubset(df_existing.columns):
                print(f"⚠️ 既存ファイルの形式が異なります。新規作成として上書きします。")
                df_final = df_new_summary
            else:
                # 外部結合 (outer join) して全てのメッシュを網羅
                merged = pd.merge(df_existing, df_new_summary, on='mesh_code', how='outer', suffixes=('_old', '_new'))
                
                # --- カウントの加算 ---
                merged['tweet_count'] = merged['tweet_count_old'].fillna(0) + merged['tweet_count_new'].fillna(0)
                
                # --- テキストの結合 ---
                def merge_text(row):
                    text_old = str(row['aggregated_text_old']) if pd.notna(row['aggregated_text_old']) and str(row['aggregated_text_old']).strip() != "" else ""
                    text_new = str(row['aggregated_text_new']) if pd.notna(row['aggregated_text_new']) and str(row['aggregated_text_new']).strip() != "" else ""
                    
                    if text_old and text_new:
                        return text_old + " /// " + text_new
                    elif text_old:
                        return text_old
                    else:
                        return text_new

                merged['aggregated_text'] = merged.apply(merge_text, axis=1)
                
                # 必要なカラムだけ抽出
                df_final = merged[['mesh_code', 'tweet_count', 'aggregated_text']]
                
        except Exception as e:
            print(f"⚠️ 既存ファイルの読み込みに失敗しました ({e})。新規作成します。")
            df_final = df_new_summary
    else:
        print(f"🆕 集計ファイル '{OUTPUT_FILE}' を新規作成します。")
        df_final = df_new_summary

    # --- 3. ソートと型変換 ---
    # ツイート数が多い順にソート
    df_final = df_final.sort_values(by='tweet_count', ascending=False)
    # 型を整数に戻す
    df_final['tweet_count'] = df_final['tweet_count'].astype(int)

    # --- 4. 統計量の算出と表示 ---
    print("\n📊 統合後の全体統計量:")
    stats = df_final['tweet_count'].describe()
    
    print("-" * 30)
    print(f"全ツイート数: {df_final['tweet_count'].sum()}")
    print(f"全メッシュ数: {len(df_final)}")
    print(f"最大値: {stats['max']}")
    print(f"最小値: {stats['min']}")
    print(f"平均値: {stats['mean']:.2f}")
    print(f"標準偏差: {stats['std']:.2f}")
    print(f"中央値: {stats['50%']}")
    print("-" * 30)

    print("\n🏆 統合後の上位5メッシュ:")
    top_5 = df_final.head(5).copy()
    # ターミナルでの表示が崩れないよう、出力用のテキストは50文字で丸める配慮を追加
    top_5['aggregated_text'] = top_5['aggregated_text'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
    print(top_5.to_string(index=False))
    print("-" * 30)

    # --- 5. 保存 ---
    df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"✅ 統合完了！ '{OUTPUT_FILE}' に保存しました。")

if __name__ == "__main__":
    main()