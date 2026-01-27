import requests
import simpleaudio as sa
import io
import time

# VOICEVOX EngineのURL (デフォルト)
BASE_URL = "http://localhost:50021"

def speak_text(text, speaker_id=42):
    """
    テキストをVOICEVOXで音声化して再生する関数
    
    Args:
        text (str): 喋らせたいテキスト
        speaker_id (int): 話者ID (11:玄野武宏, 3:ずんだもん, 2:四国めたん, etc.)
    """
    # 1. 音声合成用のクエリを作成 (Audio Query)
    try:
        query_payload = {"text": text, "speaker": speaker_id}
        r_query = requests.post(f"{BASE_URL}/audio_query", params=query_payload)
        
        if r_query.status_code != 200:
            print(f"[Error] AudioQuery失敗: {r_query.text}")
            return
        
        query_data = r_query.json()

    except requests.exceptions.ConnectionError:
        print(f"\n[Error] VOICEVOXが見つかりません。アプリが起動しているか確認してください。")
        print(f"接続先: {BASE_URL}")
        return

    # 2. 音声データを合成 (Synthesis)
    # スピードやピッチを変えたい場合は query_data の中身をここで書き換える
    # query_data['speedScale'] = 0.9 # 少しゆっくりにする例
    
    synth_payload = {"speaker": speaker_id}
    r_synth = requests.post(
        f"{BASE_URL}/synthesis",
        params=synth_payload,
        json=query_data
    )

    if r_synth.status_code != 200:
        print(f"[Error] Synthesis失敗: {r_synth.text}")
        return

    # 3. 再生 (simpleaudioを使用)
    # バイナリデータ(wav)をメモリ上で読み込んで再生
    wave_obj = sa.WaveObject.from_wave_file(io.BytesIO(r_synth.content))
    play_obj = wave_obj.play()
    
    # 再生終了を待つ（待たないと次の処理に進んでしまう）
    play_obj.wait_done()

if __name__ == "__main__":
    # テスト用
    print("音声再生テスト中...")
    speak_text("これはテスト音声じゃ。聞こえているかの？")