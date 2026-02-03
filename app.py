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
以下の文章を、SNS投稿向けの約2000文字の文章に書き換えてください。

条件：
・タイトルを必ず付ける
・内容を分かりやすくする比喩を入れる
・関連する専門用語を自然に使用する
・「なぜそう言えるのか」という根拠を最低2つ以上入れる
・絵文字を適度に入れる（多すぎない）
・思想エッセイ風で、読者に問いかける構成にする
・入力された文章のそのままの表現は使用しない。

出力は【1パターンのみ】とし、完成度を最大化してください。

元の文章：
<<<
{src}
>>>
"""

# ---- ボタン ----

if st.button("Begin the draft.", disabled=not text):

    with st.status("✍️ 執筆中… 思考を構築しています", expanded=True) as status:

        status.write("🧠 プロンプト準備中...")
        user_prompt = build_user_prompt_draft(text)

        status.write("🚀 OpenAI API 呼び出し中...")
        res = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": SYSTEM_DRAFT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
        )

        status.write("🧹 出力を整形中...")

        raw = res.choices[0].message.content

        # 【タイトル】を削除
        raw = raw.replace("【タイトル】", "").lstrip()

        st.session_state.draft_text = raw

        status.update(label="✅ 完成しました", state="complete")



# ---- 出力（要約 → 本文） ----

if st.session_state.draft_text:

    output = st.session_state.draft_text.strip()
    lines = output.splitlines()

    title = lines[0].strip()
    body = "\n".join(lines[1:]).strip()

    char_count = len(body)

    # コピー用の“全部入り”テキスト
    full_text_for_copy = f"""{title}
本文文字数：{char_count}文字

{body}
"""

    # 表示は今まで通り（見やすさ重視）
    st.subheader(title)
    st.caption(f"本文文字数：{char_count}文字")

    # 右上のコピーボタンで「全部入り」をコピーできる
    st.code(full_text_for_copy, language="markdown")


