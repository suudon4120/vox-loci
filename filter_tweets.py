import os
import time
import logging

# ==========================================
# 設定エリア
# ==========================================

# 入力ファイル名と出力ファイル名
INPUT_FILE = 'KYOTO2.txt'
OUTPUT_FILE = 'kyoto_filtered_actual.txt'
# INPUT_FILE = 'all.txt'
# OUTPUT_FILE = 'all-filtered.txt'

file_root, file_ext = os.path.splitext(OUTPUT_FILE)
LOG_FILE = f"{file_root}_log.txt"

# テストモード設定 (Trueなら最初の N行 だけ処理して終了)
# 動作確認のために最初は True で試すことをおすすめします
IS_TEST_MODE = False
TEST_LIMIT_LINES = 50000  # テスト時に読み込む行数

# キーワードリスト定義
# 抽出したい単語をここに追加・削除してください

# 1. 環境・対象（何について？）
KEYWORDS_ENV = [
    "景色", "眺め", "風景", "夜景", "ライトアップ", "見晴らし", "展望",
    "雰囲気", "空気", "居心地", "治安", "人混み", "行列", "混雑",
    "境内", "本堂", "改札", "出口", "入り口", "テラス", "BGM",
    "足元", "階段", "坂道", "路地"
]

# 2. 評価・感情（どう感じた？）
KEYWORDS_SENTIMENT = [
    "綺麗", "キレイ", "きれい", "美しい", "最高", "絶景", "落ち着く", 
    "癒やされる", "静か", "便利", "立派", "風情", "涼しい", "暖かい", "荘厳",
    "汚い", "うるさい", "騒がしい", "臭い", "不便", "怖い", "暗い", 
    "狭い", "混んでる", "激混み", "殺風景", "ボロい"
]

# 3. 特定地名（京都の主要スポット）
KEYWORDS_PLACE = [
    "京都駅", "鴨川", "清水寺", "金閣寺", "銀閣寺", "嵐山", "四条", "河原町", 
    "祇園", "伏見稲荷", "二条城", "八坂神社", "先斗町", "貴船", "鞍馬",
    "天橋立", "宇治", "東山", "南禅寺", "平安神宮"
]

# 全キーワードを結合（今回はシンプルなORマッチングのため）
ALL_KEYWORDS = KEYWORDS_ENV + KEYWORDS_SENTIMENT + KEYWORDS_PLACE

# ==========================================
# ロギング設定（画面とファイルの両方に出す）
# ==========================================
def setup_logger():
    # ロガーを作成
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 既存のハンドラがあれば削除（重複出力防止）
    if logger.hasHandlers():
        logger.handlers.clear()

    # ログのフォーマット（時間もあると便利）
    formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')

    # 1. ファイル出力設定
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 2. 画面（コンソール）出力設定
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    return logger

# グローバルなロガーを準備
logger = setup_logger()

# ==========================================
# 処理ロジック
# ==========================================

def filter_large_file():
    logger.info(f"処理を開始します: {INPUT_FILE} -> {OUTPUT_FILE}")
    logger.info(f"ログ保存先: {LOG_FILE}")
    logger.info(f"キーワード数: {len(ALL_KEYWORDS)}個")
    if IS_TEST_MODE:
        logger.info(f"★テストモード: 最初の {TEST_LIMIT_LINES} 行のみ処理します")

    start_time = time.time()
    line_count = 0
    hit_count = 0

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8', errors='ignore') as f_in, \
             open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:

            for line in f_in:
                line_count += 1
                
                # 行末の改行削除
                line_content = line.strip()
                
                # キーワード判定 (ORマッチング: どれか一つでも含まれればTrue)
                # 高速化のため、ヒットしたらすぐループを抜ける (anyを使用)
                # (地名 OR 環境) AND (評価) の場合のみ抽出
                has_target = any(k in line_content for k in KEYWORDS_PLACE + KEYWORDS_ENV)
                has_sentiment = any(k in line_content for k in KEYWORDS_SENTIMENT)

                if has_target and has_sentiment:
                    f_out.write(line)
                    hit_count += 1

                # 進捗表示 (10万行ごと)
                if line_count % 100000 == 0:
                    elapsed = time.time() - start_time
                    logger.info(f"処理中... {line_count:,} 行目 (ヒット: {hit_count:,} 件, {elapsed:.1f}秒経過)")

                # テストモードの上限チェック
                if IS_TEST_MODE and line_count >= TEST_LIMIT_LINES:
                    logger.info("テスト上限に達したため終了します。")
                    break

    except FileNotFoundError:
        logger.info(f"エラー: ファイル '{INPUT_FILE}' が見つかりません。")
        return

    total_time = time.time() - start_time
    logger.info("-" * 30)
    logger.info("処理完了")
    logger.info(f"総行数: {line_count:,}")
    logger.info(f"抽出件数: {hit_count:,}")
    logger.info(f"所要時間: {total_time:.1f}秒")
    logger.info(f"出力ファイル: {OUTPUT_FILE}")

if __name__ == "__main__":
    filter_large_file()