from flask import Flask, request, abort, send_from_directory
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, AudioSendMessage, LocationMessage
import os
import uuid
import re
import requests
import jismesh.utils as ju
from pydub import AudioSegment
from dotenv import load_dotenv

# 既存モジュールをインポート
import search_mesh
import voicevox_utils
import llm_utils
# app_cli.py から必要な関数やパスをインポート
from app_cli import (
    load_summary_data, 
    load_raw_data, 
    save_new_summary, 
    search_nearby_with_data,
    SUMMARY_DB_PATH,
    RAW_DATA_PATH
)

app = Flask(__name__)

# --- 設定  ---
load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
NGROK_DOMAIN = os.getenv('NGROK_DOMAIN')
NGROK_URL = f"https://{NGROK_DOMAIN}"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 保存用ディレクトリ
STATIC_DIR = 'static'
os.makedirs(STATIC_DIR, exist_ok=True)

# データのロード（起動時に一度だけ実行）
print("データをロード中...")
summary_data = load_summary_data()
raw_data = load_raw_data()
print("ロード完了")

def parse_coordinates(text):
    """
    テキストが '緯度, 経度' の形式か判定し、数値のタプルを返す
    例: "35.689, 139.691" -> (35.689, 139.691)
    """
    # 全角数字を半角に、全角カンマを半角に、スペース除去
    text = text.replace('，', ',').translate(str.maketrans('０１２３４５６７８９', '0123456789')).strip()
    
    # 正規表現: 数字(小数含む) , 数字(小数含む)
    match = re.match(r'^(\d+(\.\d+)?)\s*,\s*(\d+(\.\d+)?)$', text)
    if match:
        lat = float(match.group(1))
        lon = float(match.group(3))
        return lat, lon
    return None

def get_voicevox_audio(text, speaker_id=42):
    """VOICEVOXでWAV生成 -> M4A変換 -> URL返却"""
    try:
        # VOICEVOX API
        base_url = "http://localhost:50021"
        q = requests.post(f"{base_url}/audio_query", params={"text": text, "speaker": speaker_id})
        if q.status_code != 200: return None, 0
        
        s = requests.post(f"{base_url}/synthesis", params={"speaker": speaker_id}, json=q.json())
        if s.status_code != 200: return None, 0
        
        # ファイル保存
        filename = f"{uuid.uuid4()}"
        wav_path = os.path.join(STATIC_DIR, f"{filename}.wav")
        m4a_path = os.path.join(STATIC_DIR, f"{filename}.m4a")
        
        with open(wav_path, "wb") as f:
            f.write(s.content)
            
        # M4A変換 (LINE用)
        sound = AudioSegment.from_wav(wav_path)
        sound.export(m4a_path, format="mp4")
        
        duration = int(len(sound)) # ミリ秒
        
        # WAVは削除しても良いが、デバッグ用に残しても良い
        # os.remove(wav_path)
        
        return f"{filename}.m4a", duration
    except Exception as e:
        print(f"[Error] 音声生成失敗: {e}")
        return None, 0

def create_reply_messages(mesh_code, found_type, address_label):
    """
    判定結果に基づいて、テキストと音声メッセージを生成する共通関数
    """
    summary_text = ""
    reply_messages = []
    
    # 文章の決定
    if found_type in ["direct", "neighbor"]:
        summary_text = summary_data[mesh_code]
        if found_type == "neighbor":
            reply_messages.append(TextSendMessage(text=f"その場所（{address_label}）のデータはないが、すぐ近くの情報を教えるぞ。"))
    
    elif mesh_code in raw_data:
        # 未生成データがある場合 -> 自動生成
        reply_messages.append(TextSendMessage(text=f"ふむ、新しい場所（{address_label}）じゃな。詳しく見てみるぞ...（生成中）"))
        
        tweet_info = raw_data[mesh_code]
        generated_text = llm_utils.generate_summary(tweet_info['text'], mesh_code)

        # 保存
        summary_data[mesh_code] = generated_text
        save_new_summary(mesh_code, generated_text, tweet_info['count'])
        
        summary_text = generated_text
        found_type = "generated"
        
    else:
        found_type = "not_found"
        summary_text = "すまんが、このあたりには何もないようじゃ..."

    # メッセージ構築
    if found_type == "not_found":
        reply_messages.append(TextSendMessage(text=f"【お地蔵さん】\n{summary_text}"))
    else:
        reply_messages.append(TextSendMessage(text=f"【お地蔵さん】\n{summary_text}"))

    # 音声生成
    if found_type != "not_found":
        filename, duration = get_voicevox_audio(summary_text)
        if filename:
            audio_url = f"{NGROK_URL}/static/{filename}"
            reply_messages.append(AudioSendMessage(
                original_content_url=audio_url,
                preview_url=audio_url,
                duration=duration
            ))
            
    return reply_messages

def process_coords_request(lat, lon, address_text):
    """座標から検索するルート"""
    mesh_code, found_type = search_nearby_with_data(lat, lon, summary_data)
    return create_reply_messages(mesh_code, found_type, address_text)

def process_mesh_direct_request(mesh_code):
    """メッシュコード直接指定ルート"""
    # 既存データ確認
    if mesh_code in summary_data:
        return create_reply_messages(mesh_code, "direct", f"コード:{mesh_code}")
    
    # 元データ確認
    elif mesh_code in raw_data:
        # found_type="none" だが create_reply_messages 内で raw_data チェックに引っかかる仕組み
        return create_reply_messages(mesh_code, "none", f"コード:{mesh_code}")
    
    # データなし
    else:
        return create_reply_messages(mesh_code, "not_found", f"コード:{mesh_code}")


# --- LINE Bot ハンドラ ---

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@app.route('/static/<path:filename>')
def send_static(filename):
    return send_from_directory(STATIC_DIR, filename)

@handler.add(MessageEvent, message=(TextMessage, LocationMessage))
def handle_message(event):
    messages = []

    # 位置情報メッセージ
    if isinstance(event.message, LocationMessage):
        lat = event.message.latitude
        lon = event.message.longitude
        messages = process_coords_request(lat, lon, event.message.address)

    # テキストメッセージ
    elif isinstance(event.message, TextMessage):
        text = event.message.text.strip()
        
        # 座標直接入力チェック
        coords = parse_coordinates(text)
        if coords:
            lat, lon = coords
            messages = process_coords_request(lat, lon, f"{lat},{lon}")
        
        # メッシュコード直接入力
        elif text.isdigit():
            messages = process_mesh_direct_request(text)
        
        # 地名検索
        else:
            result = search_mesh.get_mesh_data(text)
            if result:
                messages = process_coords_request(result['lat'], result['lon'], result['address'])
            else:
                messages = [TextSendMessage(text="場所が見つからんかったわい。")]

    if messages:
        line_bot_api.reply_message(event.reply_token, messages)

if __name__ == "__main__":
    app.run(port=8000)