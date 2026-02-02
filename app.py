import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# .env を読み込む
load_dotenv()

# APIキーを使ってクライアント作成
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("Writer AI MVP（主張→生成）")

text = st.text_area("文章を入力", height=200)

if st.button("主張を5つ生成", disabled=not text):
    system = """あなたは思想系SNSコンテンツの編集者兼ライターです。
抽象的な文章を、一般読者にも伝わるSNS投稿用エッセイに変換する専門家です。

重視する点：
- 主張の明確さ
- 比喩による直感的理解
- 論理的根拠の提示
- 読後に思考が残る構成
- SNSで読まれるテンポ

哲学・心理学・社会学などの専門用語を適切に織り交ぜてもよいが、
必ず文脈の中で自然に使うこと。
"""

    user = f"""
以下の文章を、SNS投稿向けの約2000文字の文章に書き換えてください。

条件：
・タイトルを必ず付ける
・内容を分かりやすくする比喩を入れる
・関連する専門用語を自然に使用する
・「なぜそう言えるのか」という根拠を最低2つ以上入れる
・絵文字を適度に入れる（多すぎない）
・思想エッセイ風で、読者に問いかける構成にする

出力は【1パターンのみ】とし、完成度を最大化してください。

文字数はパターンおよそ2000文字前後。

元の文章：
<<<
{text}
>>>
"""

    res = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.8,
    )

    st.subheader("生成結果（3パターン）")
    st.write(res.choices[0].message.content)