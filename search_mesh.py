import jismesh.utils as ju
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


def main():
    print("========================================")
    print("   地名からメッシュコード変換ツール")
    print("========================================")

    # 1. ユーザーからの入力を受け付け
    query = input("検索したい地名を入力：")

    # 入力が空の場合は終了
    if not query.strip():
        print("入力が空です。処理を終了します。")
        return

    # 2. Geopyの設定 (OpenStreetMapのNominatimを使用)
    # user_agentにはアプリ名や連絡先を入れるのがマナーです
    geolocator = Nominatim(user_agent="mesh_converter_v1")

    try:
        print(f"「{query}」を検索中...")

        # 3. 住所から座標を取得 (ジオコーディング)
        # timeoutを設定して通信エラーを防ぐ
        location = geolocator.geocode(query, timeout=10)

        if location:
            lat = location.latitude
            lon = location.longitude

            # 4. 座標から5次メッシュコード(250m)を算出
            # level=5 が5次メッシュです
            mesh_code = ju.to_meshcode(lat, lon, level=5)

            # 結果の表示
            print("\n------------ 結果 ------------")
            print(f"【入力】 {query}")
            print(f"【特定】 {location.address}")  # 実際にヒットした場所を確認
            print(f"【座標】 緯度: {lat:.6f}, 経度: {lon:.6f}")
            print("------------------------------")
            print(f"★ 5次メッシュコード: {mesh_code}")
            print("------------------------------")

        else:
            print("\n[!] 場所が見つかりませんでした。")
            print("ヒント: 正式名称を使うか、県名を含めるとヒットしやすくなります。")

    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"\n[Error] 通信エラーが発生しました: {e}")
    except Exception as e:
        print(f"\n[Error] 予期せぬエラー: {e}")


if __name__ == "__main__":
    main()
