from datetime import datetime, timezone, timedelta
import html
import streamlit as st
import streamlit.components.v1 as components
import requests
import time
import os
import streamlit as st
from dotenv import load_dotenv

# .env を読み込む
load_dotenv()

# APIキーを使ってクライアント作成

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

# ---- 出力表示（日時はタイトル直下に入れてコピー対象に／ボタンは上／見た目くっきり） ----
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
"""

    # HTMLに埋め込むのでエスケープ
    safe_text = html.escape(full_text_for_copy)

    # 画面上には「コピー欄の上にタイトル」は出さない（重複防止）
    # 日時は「コピーされる本文内」に入っているので、別表示は不要なら消してOK
    # st.caption(f"出力: {generated_at}")

    components.html(
        f"""
        <div style="display:flex; gap:8px; align-items:center; margin: 6px 0 10px 0;">
          <button id="copyBtn"
            style="padding:10px 12px; border-radius:10px; border:1px solid rgba(0,0,0,.25); background:white; font-weight:600;">
            📋 Copy
          </button>
          <span id="copyMsg" style="opacity:.75; font-size: 13px;"></span>
        </div>

        <textarea id="copyArea"
          style="
            width: 100%;
            height: 380px;
            padding: 12px;
            box-sizing: border-box;
            border-radius: 12px;
            border: 1px solid rgba(0,0,0,.25);
            background: white;
            color: #111;
            font-size: 15px;
            line-height: 1.55;
            white-space: pre-wrap;
            word-break: break-word;
          ">{safe_text}</textarea>

        <script>
          const btn = document.getElementById("copyBtn");
          const area = document.getElementById("copyArea");
          const msg = document.getElementById("copyMsg");

          btn.addEventListener("click", async () => {{
            area.focus();
            area.select();
            try {{
              // まずは execCommand で互換性重視（iOSで強い）
              const ok = document.execCommand("copy");
              if (ok) {{
                msg.textContent = "コピーしました ✅";
                return;
              }}
            }} catch (e) {{}}

            // execCommandがダメなら clipboard API
            try {{
              await navigator.clipboard.writeText(area.value);
              msg.textContent = "コピーしました ✅";
            }} catch (e) {{
              msg.textContent = "コピーできませんでした（長押し→コピーを試してね）";
            }}
          }});
        </script>
        """,
        height=460,
    )


