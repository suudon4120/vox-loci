import reverse_geocoder as rg
import time
import sys

# ---------------------------------------------------------
# 設定
INPUT_FILE = 'all.txt'
if len(sys.argv) < 2:
    print("抽出したい都道府県名をローマ字で入力")
    sys.exit(1)
TARGET_PREF = sys.argv[1]
OUTPUT_FILE = f'{TARGET_PREF}_tweets.txt' # 書き出し先
BATCH_SIZE = 100000             # 一度に処理する行数（メモリに応じて調整）
# ---------------------------------------------------------

def filter_huge_file():
    print(f"処理を開始します... 対象: {TARGET_PREF} (を含むエリア)")
    start_time = time.time()
    
    total_processed = 0
    hit_count = 0

    # バッファ用リスト
    batch_coords = [] # (lat, lon) のタプルを格納
    batch_lines = []  # 元の行データを格納

    with open(INPUT_FILE, 'r', encoding='utf-8', errors='ignore') as f_in, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:

        for line in f_in:
            line_stripped = line.strip()
            if not line_stripped: continue

            parts = line_stripped.split('\t')
            
            # データ形式チェック（緯度経度が末尾にあると仮定）
            # ファイルの末尾2つが [lat, lon] である必要があります
            if len(parts) < 2:
                continue

            try:
                lat = float(parts[-2])
                lon = float(parts[-1])
                
                # バッチに追加
                batch_coords.append((lat, lon))
                batch_lines.append(line_stripped)

            except ValueError:
                continue

            # バッチサイズに達したらまとめて判定
            if len(batch_coords) >= BATCH_SIZE:
                hit_count += process_batch(batch_coords, batch_lines, f_out)
                total_processed += len(batch_coords)
                
                # 進捗表示
                elapsed = time.time() - start_time
                print(f"経過: {int(elapsed)}秒 | 処理済: {total_processed}行 | ヒット: {hit_count}行")
                
                # バッファをクリア
                batch_coords = []
                batch_lines = []

        # 残りのデータを処理
        if batch_coords:
            hit_count += process_batch(batch_coords, batch_lines, f_out)
            total_processed += len(batch_coords)

    elapsed = time.time() - start_time
    print(f"完了！ 総処理時間: {int(elapsed)}秒")
    print(f"抽出件数: {hit_count} / {total_processed}")

def process_batch(coords, lines, file_handle):
    """
    reverse_geocoderを使って一括判定し、マッチする行を書き込む
    """
    local_hit = 0
    
    results = rg.search(coords)

    for i, res in enumerate(results):
        # res['admin1'] には都道府県名が入る (例: "Tokyo Prefecture")
        # res['name'] には市区町村名等が入る
        
        # 都道府県名(admin1)にターゲット文字列が含まれているか
        if TARGET_PREF.lower() in res['admin1'].lower():
            file_handle.write(lines[i] + '\n')
            local_hit += 1
            
    return local_hit

if __name__ == "__main__":
    filter_huge_file()