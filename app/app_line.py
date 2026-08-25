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
import llm_utils

# データベース関連と、app_cliから共通関数をインポート
from database import SessionLocal, MeshSummary, IntegratedTweet
from app_cli import save_new_summary, search_nearby_with_db

# 保存用ディレクトリ
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, 'data', 'audio')
os.makedirs(STATIC_DIR, exist_ok=True)

# --- 設定  ---
load_dotenv(os.path.join(BASE_DIR, '.env'))
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
NGROK_DOMAIN = os.getenv('NGROK_DOMAIN')
NGROK_URL = f"https://{NGROK_DOMAIN}"
VOICEVOX_URL = os.getenv('VOICEVOX_URL')

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

def parse_coordinates(text):
    """
    テキストが '緯度, 経度' の形式か判定し、数値のタプルを返す
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
        base_url = VOICEVOX_URL
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
        
        duration = int(len(sound))
        return f"{filename}.m4a", duration
    except Exception as e:
        print(f"[Error] 音声生成失敗: {e}")
        return None, 0

def create_reply_messages(db, mesh_code, found_type, address_label):
    """
    判定結果に基づいて、テキストと音声メッセージを生成する共通関数
    """
    summary_text = ""
    reply_messages = []
    
    if found_type in ["direct", "neighbor"]:
        # DBから要約を取得
        record = db.query(MeshSummary).filter(MeshSummary.mesh_code == mesh_code).first()
        summary_text = record.summary if record else "エラーが発生しました。"
        
        if found_type == "neighbor":
            reply_messages.append(TextSendMessage(text=f"その場所（{address_label}）のデータはないが、すぐ近くの情報を教えるぞ。"))
    
    elif found_type == "none":
        # 未生成データがある場合 -> 自動生成
        raw_record = db.query(IntegratedTweet).filter(IntegratedTweet.mesh_code == mesh_code).first()
        
        if raw_record:
            reply_messages.append(TextSendMessage(text=f"ふむ、新しい場所（{address_label}）じゃな。詳しく見てみるぞ...（生成中）"))
            
            # LLM生成と保存
            generated_text = llm_utils.generate_summary(raw_record.aggregated_text, mesh_code)
            save_new_summary(db, mesh_code, generated_text, raw_record.tweet_count)
            
            summary_text = generated_text
            found_type = "generated"
        else:
            found_type = "not_found"
            summary_text = "すまんが、このあたりには何もないようじゃ..."
    
    else:
        found_type = "not_found"
        summary_text = "すまんが、このあたりには何もないようじゃ..."

    # メッセージ構築
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

def process_coords_request(db, lat, lon, address_text):
    """座標から検索するルート"""
    mesh_code, found_type = search_nearby_with_db(db, lat, lon)
    return create_reply_messages(db, mesh_code, found_type, address_text)

def process_mesh_direct_request(db, mesh_code):
    """メッシュコード直接指定ルート"""
    if db.query(MeshSummary).filter(MeshSummary.mesh_code == mesh_code).first():
        return create_reply_messages(db, mesh_code, "direct", f"コード:{mesh_code}")
    elif db.query(IntegratedTweet).filter(IntegratedTweet.mesh_code == mesh_code).first():
        return create_reply_messages(db, mesh_code, "none", f"コード:{mesh_code}")
    else:
        return create_reply_messages(db, mesh_code, "not_found", f"コード:{mesh_code}")

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

@handler.add(MessageEvent, message=(TextMessage, LocationMessage))
def handle_message(event):
    messages = []
    
    # ユーザーからのメッセージが来るたびにデータベースの窓口（セッション）を開く
    db = SessionLocal()
    
    try:
        if isinstance(event.message, LocationMessage):
            lat = event.message.latitude
            lon = event.message.longitude
            messages = process_coords_request(db, lat, lon, event.message.address)

        elif isinstance(event.message, TextMessage):
            text = event.message.text.strip()
            
            coords = parse_coordinates(text)
            if coords:
                lat, lon = coords
                messages = process_coords_request(db, lat, lon, f"{lat},{lon}")
            
            elif text.isdigit():
                messages = process_mesh_direct_request(db, text)
            
            else:
                result = search_mesh.get_mesh_data(text)
                if result:
                    messages = process_coords_request(db, result['lat'], result['lon'], result['address'])
                else:
                    messages = [TextSendMessage(text="場所が見つからんかったわい。")]

        if messages:
            line_bot_api.reply_message(event.reply_token, messages)
            
    finally:
        # 処理が成功してもエラーが起きても、絶対にセッションを閉じる
        db.close()

if __name__ == "__main__":
    # host="0.0.0.0"により，Dockerコンテナ外からの通信を許可
    # Cloud Runから割り当てられる環境変数PORTを取得し，なければデフォルトで8000を使用
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)