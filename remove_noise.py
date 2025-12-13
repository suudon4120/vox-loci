import pandas as pd
import os

# =========================================================
# 【設定エリア】
# =========================================================

# 処理タイプを設定: 'csv' または 'txt' を入力
PROCESS_TYPE = 'csv'

# 入力ファイル名
INPUT_PATH = 'KYOTO2_10220_tagged.csv'

# 出力ファイル名
root, ext = os.path.splitext(INPUT_PATH)
OUTPUT_PATH = f"{root}_cleaned.csv"

# 除外したい行末パターンのリスト
# ※ ここに条件を追加すれば、ロジックを変更せずに除外対象を増やせます
EXCLUDE_PATTERNS = [
    "ノイズ(クーポン情報)",
    "ノイズ(単体場所情報)",
    "ノイズ(広告・宣伝)",
    "ノイズ(客観的記述)"
]

# フィルタリングを行うカラム名
TARGET_COLUMN = 'sentiment_or_noise'
LOCATION_COLUMN = 'is_location_related'

# =========================================================
# 【処理ロジックエリア】
# =========================================================

def filter_data_by_column(input_path, output_path, process_type, target_col, exclude_values, location_col):
    """
    Pandasを使用してデータを読み込み、指定されたカラムの値に基づいて行を除外する関数
    """
    
    # 処理タイプに応じてデリミタ（区切り文字）を決定
    if process_type == 'csv':
        delimiter = ','
        print("▶️ CSV処理モード (カンマ区切り) で実行します。")
    elif process_type == 'txt':
        delimiter = '\t'
        print("▶️ TXT処理モード (タブ区切り) で実行します。")
    else:
        print("エラー: PROCESS_TYPE は 'csv' または 'txt' のいずれかを設定してください。")
        return

    try:
        # データの読み込み
        df = pd.read_csv(input_path, sep=delimiter)
        
        # ターゲットカラムが存在するか確認
        if target_col not in df.columns or location_col not in df.columns:
            print(f"エラー: 必要なカラム ('{target_col}' または '{location_col}') がファイル内に見つかりません。")
            return

        total_lines = len(df)
        
        # 除外マスクの初期化 (すべてFalse: 残す)
        mask_to_exclude = pd.Series(False, index=df.index)
        
        # is_location_related が False の行に True を立てる
        mask_to_exclude |= (df[location_col] == False)
        print("✅ 場所非関連の行 (is_location_related=False) を除外対象に追加しました。")

        # target_col の値が exclude_strings のリストに含まれる行に True を立てる
        mask_to_exclude |= df[target_col].isin(exclude_values)
        print("✅ ノイズタグによる除外対象を追加しました。")

        # target_col が NaN の行に True を立てる
        mask_to_exclude |= df[target_col].isna()
        print("✅ NaN (欠損値) を除外対象に追加しました。")

        # フィルタリング処理
        # その結果を ~ で反転させ、False（残したい行）だけを選択
        df_cleaned = df[~mask_to_exclude]
        
        kept_lines = len(df_cleaned)

        # ファイルへの保存
        df_cleaned.to_csv(output_path, index=False)

        print("-" * 30)
        print("処理完了！")
        print(f"保存先: {output_path}")
        print(f"結果: 全 {total_lines} 行中、 {total_lines - kept_lines} 行を除外しました。")
        print(f"残り: {kept_lines} 行")
        print("-" * 30)

    except FileNotFoundError:
        print(f"エラー: 入力ファイル '{input_path}' が見つかりません。パスを確認してください。")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")

if __name__ == "__main__":
    # 設定値を使って関数を実行
    filter_data_by_column(
        input_path=INPUT_PATH, 
        output_path=OUTPUT_PATH, 
        process_type=PROCESS_TYPE,
        target_col=TARGET_COLUMN, 
        exclude_values=EXCLUDE_PATTERNS,
        location_col=LOCATION_COLUMN
    )