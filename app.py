import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# .env を読み込む（ローカル用。Streamlit CloudではSecretsに入れる）
load_dotenv()

# OpenAIクライアント
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("Writer AI（SNS投稿用に書き換え）")

# セッションに保存する箱（ボタン押しても保持するため）
if "output_text" not in st.session_state:
    st.session_state.output_text = ""
if "summary_120" not in st.session_state:
    st.session_state.summary_120 = ""

text = st.text_area("文章を入力", height=200)

# ========= 本文生成 =========
col1, col2 = st.columns(2)

with col1:
    if st.button("投稿文を生成 ✨", disabled=not text):
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

文字数はおよそ2000文字前後。

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

        st.session_state.output_text = res.choices[0].message.content.strip()
        # 本文を作り直したら、要約はリセット（古い要約の混在防止）
        st.session_state.summary_120 = ""

with col2:
    # ========= 120文字要約 =========
    if st.button("要約を作る（120文字）", disabled=not st.session_state.output_text):
        sum_system = "あなたは編集者。日本語でX向けに要約する。"
        sum_user = f"""
次の文章をX投稿用に【120文字以内】で要約して。

条件：
- 核が一発で伝わる
- 絵文字は1〜2個まで
- ハッシュタグは不要
- 120文字を1文字でも超えたら、必ず言い換えて120文字以内に収める

本文：
<<<
{st.session_state.output_text}
>>>

出力は要約文のみ（前置き不要）。
"""

        sum_res = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": sum_system},
                {"role": "user", "content": sum_user},
            ],
            temperature=0.6,
        )

        st.session_state.summary_120 = sum_res.choices[0].message.content.strip()

st.divider()

# ========= 表示エリア =========
st.subheader("生成結果（本文）")
if st.session_state.output_text:
    # 右上にコピー（📋）が付く
    st.code(st.session_state.output_text, language="markdown")
else:
    st.caption("まだ本文がありません。左の「投稿文を生成 ✨」を押してください。")

st.subheader("120文字要約（X向け）")
if st.session_state.summary_120:
    st.code(st.session_state.summary_120, language="text")
else:
    st.caption("まだ要約がありません。右の「要約を作る（120文字）」を押してください。")
