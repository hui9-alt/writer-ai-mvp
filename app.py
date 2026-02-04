import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# .env を読み込む
load_dotenv()

# APIキーを使ってクライアント作成
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("Writer AI")

# ---- session state 初期化 ----
if "draft_text" not in st.session_state:
    st.session_state.draft_text = ""
if "summary_text" not in st.session_state:
    st.session_state.summary_text = ""

text = st.text_area("Idea Terminal", height=200)

# ---- プロンプト（本文） ----

def load_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_DRAFT = load_prompt("prompt_draft.txt")

def build_user_prompt_draft(src: str) -> str:
    return f"""
以下の文章を、SNS投稿向けの約500文字の文章に書き換えてください。

条件：
・タイトルを必ず付ける
・内容を分かりやすくする比喩を入れる
・関連する専門用語を自然に使用する
・「なぜそう言えるのか」という根拠を最低2つ以上入れる
・絵文字を適度に入れる（多すぎない）
・思想エッセイ風で、読者に問いかける構成にする
・入力された文章のそのままの表現は使用しない。

元の文章：
<<<
{src}
>>>
"""

# ---- ボタン ----

if st.button("Begin the draft.", disabled=not text):
    # 本文生成
    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_DRAFT},
            {"role": "user", "content": build_user_prompt_draft(text)},
        ],
        temperature=0.6,
    )
    st.session_state.draft_text = res.choices[0].message.content

from datetime import datetime

# 出力（ドラフトが存在する場合）
if st.session_state.draft_text:
    st.subheader("✍️ Output")

    # 出力された文章からタイトル行を取り出す
    lines = st.session_state.draft_text.strip().splitlines()
    title_line = lines[0].strip()
    body = "\n".join(lines[1:]).strip()

    # 文字数をカウント（タイトル＋本文）
    char_count = len(title_line + body)

    # 現在の日時を取得
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 表示用にまとめる
    full_output = f"{title_line}\n\n文字数: {char_count}文字　日時: {now}\n\n{body}"

    # Markdown形式で出力
    st.code(full_output, language="markdown")


