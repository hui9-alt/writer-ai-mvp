import requests
import time
import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# .env を読み込む
load_dotenv()

# APIキーを使ってクライアント作成
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("Writer AI")
API_BASE = st.secrets["WORKER_API_BASE"]

# ---- session state 初期化 ----
if "draft_text" not in st.session_state:
    st.session_state.draft_text = ""
if "job_id" not in st.session_state:
    st.session_state.job_id = None
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

    user_prompt = build_user_prompt_draft(text)

    with st.status("📮 ジョブ投入中（閉じてもOK）", expanded=True) as status:
        r = requests.post(
            f"{API_BASE}/enqueue",
            params={
                "system": SYSTEM_DRAFT,
                "user": user_prompt,
                "model": "gpt-4.1",
            },
            timeout=30,
        )
        st.session_state.job_id = r.json()["job_id"]
        status.update(label="✅ 投入完了", state="complete")




# ---- 出力（要約 → 本文） ----

job_id = st.session_state.get("job_id")

if job_id:
    with st.status("⏳ 実行中（いつでも閉じてOK）", expanded=True) as s:
        for _ in range(120):  # 最大4分くらい待つ
            stt = requests.get(f"{API_BASE}/status/{job_id}", timeout=10).json()["status"]
            s.write(f"status: {stt}")
            if stt in ("finished", "failed"):
                break
            time.sleep(2)

        rr = requests.get(f"{API_BASE}/result/{job_id}", timeout=10).json()
        if rr.get("ready"):
            st.session_state.draft_text = rr["result"]
            s.update(label="✅ 完成しました", state="complete")
        else:
            s.update(label="⚠️ まだ結果がありません（後で開き直してOK）", state="error")


if st.session_state.draft_text:

    output = st.session_state.draft_text.strip()
    lines = output.splitlines()

    title = lines[0]
    body = "\n".join(lines[1:]).strip()

    char_count = len(body)

    st.subheader(title)
    st.caption(f"本文文字数：{char_count}文字")

    st.code(body, language="markdown")




