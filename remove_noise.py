import pandas as pd
import os
import argparse
import sys

# =========================================================
# 【設定エリア】
# =========================================================

# 処理タイプを設定: 'csv' または 'txt' を入力
PROCESS_TYPE = 'csv'

# 入力ファイル名
parser = argparse.ArgumentParser(description="特定のタグを含む行を除去するプログラム")
parser.add_argument("--input", type=str, help="処理対象のファイルパス")
# args = parser.parse_args()
# 以下の行をコメントアウト（または削除）
# args = parser.parse_args()

# 代わりに、テスト実行時でもエラーにならないよう空のオブジェクトを作成
class DummyArgs:
    input = None
args = DummyArgs()
# if args.input:
#     INPUT_PATH = args.input
#     print(f"コマンドライン引数からファイル名を受け取りました: {INPUT_PATH}")
# else:
#     print("入力ファイルが指定されていません。")
#     INPUT_PATH = input(">>処理するファイル名を入力してください: ").strip()
# --- 修正前（ここをコメントアウトまたは削除） ---
# if args.input:
#     INPUT_PATH = args.input
# else:
#     INPUT_PATH = input(">>処理するファイル名を入力してください: ").strip()

# --- 修正後（ここを追加） ---
INPUT_PATH = "dummy.csv"  # テスト時は固定値にする
if not INPUT_PATH:
    print("ファイル名が入力されませんでした。終了します。")
    sys.exit()

# 出力ファイル名
root, ext = os.path.splitext(INPUT_PATH)
OUTPUT_PATH = f"{root}_cleaned.csv"

# 除外したい行末パターンのリスト
# ※ ここに条件を追加すれば、ロジックを変更せずに除外対象を増やせます
EXCLUDE_PATTERNS = [
    "ノイズ(クーポン情報)",
    "ノイズ(単体場所情報)",
    "ノイズ(広告・宣伝)",
    "ノイズ(客観的記述)",
    "noise",
    "ノイス",
    "ノイズ",
    "ノイズ/広告",
    "ニュース",
    "ニュートラル"
]

# ここに "住民", "観光客", "それ以外" などを記述すると、その属性の行が除去されます。
# 除外したくないものはコメントアウト（行頭に #）するか、リストから削除してください。
EXCLUDE_USER_ATTRIBUTES = [
    "それ以外",
    # "住民",
    "観光客",
]

# フィルタリングを行うカラム名
TARGET_COLUMN = 'sentiment_or_noise'
LOCATION_COLUMN = 'is_location_related'
USER_ATTRIBUTE_COLUMN = 'user_attribute'

# =========================================================
# 【処理ロジックエリア】
# =========================================================

def filter_data_by_column(input_path, output_path, process_type, target_col, exclude_values, location_col, user_attr_col, exclude_user_attrs):
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

        # 4. user_attribute による除外 (今回追加)
        if user_attr_col in df.columns:
            mask_to_exclude |= df[user_attr_col].isin(exclude_user_attrs)
            print(f"✅ ユーザー属性 ({exclude_user_attrs}) による除外対象を追加しました。")
        else:
            print(f"⚠️ 注意: '{user_attr_col}' カラムが存在しないため、属性フィルタはスキップされました。")

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

def main():
    """コマンドライン引数の処理と実行をここにまとめる"""
    parser = argparse.ArgumentParser(description="特定のタグを含む行を除去するプログラム")
    parser.add_argument("--input", type=str, help="処理対象のファイルパス")
    args = parser.parse_args()

    if args.input:
        input_path = args.input
        print(f"コマンドライン引数からファイル名を受け取りました: {input_path}")
    else:
        print("入力ファイルが指定されていません。")
        input_path = input(">>処理するファイル名を入力してください: ").strip()

    if not input_path:
        print("ファイル名が入力されませんでした。終了します。")
        sys.exit()

    # 出力ファイル名の生成
    root, ext = os.path.splitext(input_path)
    output_path = f"{root}_cleaned.csv"

    # 関数の実行
    filter_data_by_column(
        input_path=input_path, 
        output_path=output_path, 
        process_type=PROCESS_TYPE,
        target_col=TARGET_COLUMN, 
        exclude_values=EXCLUDE_PATTERNS,
        location_col=LOCATION_COLUMN,
        user_attr_col=USER_ATTRIBUTE_COLUMN,
        exclude_user_attrs=EXCLUDE_USER_ATTRIBUTES
    )

if __name__ == "__main__":
    main()