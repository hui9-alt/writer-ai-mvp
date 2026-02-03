import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
import html

import requests
import streamlit as st
import streamlit.components.v1 as components


st.title("Writer AI")

# Worker API のベースURL（Streamlit secrets）
API_BASE = st.secrets["WORKER_API_BASE"]

# ---- session state 初期化 ----
if "draft_text" not in st.session_state:
    st.session_state.draft_text = ""
if "job_id" not in st.session_state:
    st.session_state.job_id = None

text = st.text_area("Idea Terminal", height=200)


def load_prompt(path: str) -> str:
    # app.py と同じフォルダ基準で読む
    p = Path(__file__).parent / path
    return p.read_text(encoding="utf-8")


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


# ---- ジョブ投入 ----
if st.button("Begin the draft.", disabled=not text):
    user_prompt = build_user_prompt_draft(text)

    try:
        r = requests.post(
            f"{API_BASE}/enqueue",
            json={
                "system": SYSTEM_DRAFT,
                "user": user_prompt,
                "model": "gpt-4.1",
            },
            timeout=30,
        )
        r.raise_for_status()
        st.session_state.job_id = r.json()["job_id"]
        st.toast("✅ 投入完了")
    except Exception as e:
        st.error(f"enqueue 失敗: {e}")


# ---- 結果取得（裏でポーリングするだけ。表示は最小） ----
job_id = st.session_state.get("job_id")

if job_id:
    with st.spinner("生成中…（閉じてもOK）"):
        stt = None
        for _ in range(120):  # 最大240秒
            try:
                stt = requests.get(f"{API_BASE}/status/{job_id}", timeout=10).json().get("status")
            except Exception:
                stt = None

            if stt in ("finished", "failed"):
                break
            time.sleep(2)

    try:
        rr = requests.get(f"{API_BASE}/result/{job_id}", timeout=10).json()
        if rr.get("ready"):
            raw = rr["result"]
            raw = raw.replace("【タイトル】", "").strip()
            st.session_state.draft_text = raw
            st.toast("✅ 完成しました")
    except Exception as e:
        st.error(f"result 取得失敗: {e}")


# ---- 出力表示（Copyボタン上／スマホ折り返し／くっきり表示） ----
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

    safe_text = html.escape(full_text_for_copy)

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
              const ok = document.execCommand("copy");
              if (ok) {{
                msg.textContent = "コピーしました ✅";
                return;
              }}
            }} catch (e) {{}}

            try {{
              await navigator.clipboard.writeText(area.value);
              msg.textContent = "コピーしました ✅";
            }} catch (e) {{
              msg.textContent = "コピーできませんでした（長押し→コピーしてね）";
            }}
          }});
        </script>
        """,
        height=460,
    )
