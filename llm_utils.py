from openai import OpenAI
import os
from dotenv import load_dotenv

# APIキーの設定
load_dotenv()
# 環境変数からAPIキーを取得
API_KEY = os.getenv("OPENAI_API_KEY")
# APIキーが読み込めていない場合は安全のためエラー終了させる
if not API_KEY:
    raise ValueError("❌ エラー: APIキーが見つかりません。")

# OpenAIクライアントの初期化
client = OpenAI(api_key=API_KEY)

def generate_summary(tweet_text):
    """
    ツイートの集合テキストを受け取り、お地蔵さん口調の要約を生成する
    """
    if not tweet_text:
        return "ふむ、このあたりは静かなようじゃ。特に目立った声は聞こえてこんわい。"

    system_prompt = """
    あなたは、長い間日本の各地を見守ってきたお地蔵さんです。
    指定されたツイート群を要約して、この場所（メッシュ）を代表する説明文を作成してください。
    
    # 制約事項
    - 一人称は「わし」、語尾は「〜じゃ」「〜わい」「〜のう」などの老人・仙人口調で話すこと。
    - 地元の守り神のような、温かく、少し達観した視点で語ること。
    - ツイートに含まれる具体的な店名やイベント名があれば言及すること。
    - 誹謗中傷やノイズと思われる情報は無視すること。
    - 長さは200文字程度で簡潔にまとめること。
    - 出力は要約テキストのみ。自己紹介をしないこと。
    """

    user_prompt = f"""
    以下の内容はツイートを位置情報に基づいてグルーピングしたものの一つである。これらのツイートを一つの文章に要約してまとめ、「この地理メッシュ(5次メッシュ)の代表」となる説明文を、**地域を見守るお地蔵さんの視点で、地域の知恵袋のようなイメージで**作成して。
    
    [例]
    ここは龍谷大学深草キャンパスを中心とした、活気ある学びの庭じゃよ。レンガ造りの美しい学舎には、寒さに震えながらもTOEICや講義に励む若者たちが集っておる。カフェで一息ついたり、瀬田より速い朝の勤行に驚いたりと、悲喜こもごもの青春模様が見て取れるわい。図書館でのマナーを気にかけたり、防災設備に感心したりと、素直な心も育っておるようじゃな。伝統の重みと若き熱気が混ざり合う、この地ならではの賑わいがわしは大好きじゃよ。
    
    [ツイートデータ]
    {tweet_text[:3000]} 
    """
    # ※トークン節約のため、文字数を3000文字程度に制限しています

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[Error] LLM生成エラー: {e}")
        return f"すまんのう、ちと耳が遠くなったみたいじゃ（APIエラー）。\n{e}"

if __name__ == "__main__":
    # テスト用
    sample_tweets = "京都駅の階段めっちゃ長い。抹茶パフェ美味しい。人が多すぎて疲れた。"
    print(generate_summary(sample_tweets))