import jismesh.utils as ju
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

def get_mesh_data(query):
    """
    地名クエリからメッシュコード情報を取得する関数
    (アプリからの利用を想定)
    
    Args:
        query (str): 検索したい地名
    Returns:
        dict: 成功時 {'mesh_code': str, 'address': str, 'lat': float, 'lon': float}
        None: 失敗時
    """
    # 入力が空の場合はNoneを返す
    if not query or not query.strip():
        return None

    # Geopyの設定
    geolocator = Nominatim(user_agent="mesh_converter_v1")
    
    try:
        # 住所から座標を取得
        location = geolocator.geocode(query, timeout=10)
        
        if location:
            lat = location.latitude
            lon = location.longitude
            
            # 5次メッシュコード(250m)を算出
            mesh_code = ju.to_meshcode(lat, lon, level=5)
            
            # 辞書形式で結果を返す
            return {
                "mesh_code": mesh_code,
                "address": location.address,
                "lat": lat,
                "lon": lon
            }
        else:
            # 見つからなかった場合
            return None
            
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"[Error] 通信エラーが発生しました: {e}")
        return None
    except Exception as e:
        print(f"[Error] 予期せぬエラー: {e}")
        return None

def main():
    """
    単体実行時のメイン処理（CLIツールとして動作）
    """
    print("========================================")
    print("   地名からメッシュコード変換ツール")
    print("========================================")
    
    query = input("検索したい地名を入力：")
    
    if not query.strip():
        print("入力が空です。処理を終了します。")
        return

    print(f"「{query}」を検索中...")
    
    # ★ここが変わった箇所: ロジック関数を呼び出すだけにする
    result = get_mesh_data(query)
    
    if result:
        print("\n------------ 結果 ------------")
        print(f"【入力】 {query}")
        print(f"【特定】 {result['address']}")
        print(f"【座標】 緯度: {result['lat']:.6f}, 経度: {result['lon']:.6f}")
        print(f"------------------------------")
        print(f"★ 5次メッシュコード: {result['mesh_code']}")
        print(f"------------------------------")
    else:
        print("\n[!] 場所が見つかりませんでした。")
        print("ヒント: 正式名称を使うか、県名を含めるとヒットしやすくなります。")

if __name__ == "__main__":
    main()