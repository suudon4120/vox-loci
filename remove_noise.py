import os

# =========================================================
# 【設定エリア】
# ここを変更するだけで、入出力ファイルや除外ルールを切り替えられます。
# =========================================================

# 入力ファイル名
INPUT_PATH = 'KYOTO2_100_processed_tagged.txt'

# 出力ファイル名
root, ext = os.path.splitext(INPUT_PATH)
OUTPUT_PATH = f"{root}_cleaned{ext}"

# 除外したい行末パターンのリスト
# ※ ここに条件を追加すれば、ロジックを変更せずに除外対象を増やせます
EXCLUDE_PATTERNS = [
    ", -1",    # パターン1: カンマ＋スペース＋-1
    ",-1",     # パターン2: カンマ＋-1
    # ", 0",   # 例: 将来的に0を除外したい場合
]

# =========================================================
# 【処理ロジックエリア】
# =========================================================

def filter_lines_by_patterns(input_file, output_file, patterns):
    """
    指定されたファイルから、パターンに一致する行を除外して保存する関数
    """
    total_lines = 0
    kept_lines = 0

    try:
        # 入力ファイルの存在確認
        if not os.path.exists(input_file):
            print(f"エラー: 入力ファイル '{input_file}' が見つかりません。パスを確認してください。")
            return

        with open(input_file, 'r', encoding='utf-8') as f_in, \
             open(output_file, 'w', encoding='utf-8') as f_out:
            
            print(f"処理を開始します: {input_file} -> {output_file}")
            
            for line in f_in:
                total_lines += 1
                stripped_line = line.strip()
                
                # 設定されたパターンのいずれかに一致するか判定
                if any(stripped_line.endswith(pattern) for pattern in patterns):
                    continue
                
                f_out.write(line)
                kept_lines += 1

        print("-" * 30)
        print("処理完了！")
        print(f"保存先: {output_file}")
        print(f"結果: 全 {total_lines} 行中、 {total_lines - kept_lines} 行を除外しました。")
        print(f"残り: {kept_lines} 行")
        print("-" * 30)

    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")

if __name__ == "__main__":
    # 設定値を使って関数を実行
    filter_lines_by_patterns(INPUT_PATH, OUTPUT_PATH, EXCLUDE_PATTERNS)