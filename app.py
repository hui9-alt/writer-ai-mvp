from datetime import datetime, timezone, timedelta
import streamlit as st
import requests
import time
from dotenv import load_dotenv

# .env を読み込む
load_dotenv()

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

    # ※ ここは元コードに「ジョブ作成API呼び出し」が載っていなかったので、
    # 既存実装に合わせて job_id をセットしてください。
    #
    # 例（あなたのWorker仕様に合わせて調整）:
    # r = requests.post(f"{API_BASE}/start", json={
    #     "system": SYSTEM_DRAFT,
    #     "user": user_prompt
    # }, timeout=30).json()
    # st.session_state.job_id = r["job_id"]

# ---- 出力（要約 → 本文） ----
job_id = st.session_state.get("job_id")

if job_id:
    with st.status("⏳ 実行中（いつでも閉じてOK）", expanded=True) as s:
        for _ in range(120):
            stt = requests.get(f"{API_BASE}/status/{job_id}", timeout=10).json()["status"]
            s.write(f"status: {stt}")
            if stt in ("finished", "failed"):
                break
            time.sleep(2)

        rr = requests.get(f"{API_BASE}/result/{job_id}", timeout=10).json()

        if rr.get("ready"):
            raw = rr["result"]
            raw = raw.replace("【タイトル】", "").strip()
            st.session_state.draft_text = raw
            s.update(label="✅ 完成しました", state="complete")
        else:
            s.update(label="⚠️ まだ結果がありません（後で開き直してOK）", state="error")

# ---- 出力表示（HTMLなし版）----
if st.session_state.draft_text:
    output = st.session_state.draft_text.strip()
    lines = output.splitlines()

    title = (lines[0].strip() if lines else "").strip()
    body = "\n".join(lines[1:]).strip()

    # 出力日時（JST）
    jst = timezone(timedelta(hours=9))
    generated_at = datetime.now(jst).strftime("%Y-%m-%d %H:%M")

    # コピー対象（タイトル＋日時＋本文）
    full_text_for_copy = f"""{title}

出力: {generated_at}

{body}
""".strip()

    st.subheader("Output")

    # 1) コピーボタン（右上のアイコン）付きで表示されることが多い
    # ※ Streamlitのバージョン/環境により見え方が少し違う場合があります
    st.code(full_text_for_copy, language="markdown")

    # 2) iOS向けの保険：長押しでコピーしやすいテキストエリアも併設
    st.text_area("Copy area (長押し→コピーOK)", value=full_text_for_copy, height=380)

    # 3) さらに保険：テキストとしてDLもできる
    st.download_button(
        "⬇️ Download as .txt",
        data=full_text_for_copy,
        file_name=f"draft_{generated_at.replace(':','-').replace(' ','_')}.txt",
        mime="text/plain",
    )
