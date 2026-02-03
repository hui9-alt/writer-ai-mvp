from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI


# -----------------------------
# App Config
# -----------------------------
APP_TITLE = "Writer AI"
TZ = ZoneInfo("Asia/Tokyo")

st.set_page_config(page_title=APP_TITLE, page_icon="✍️", layout="centered")
st.title(APP_TITLE)

# -----------------------------
# Secrets (Streamlit Cloud)
# -----------------------------
# Streamlit Cloud の Settings > Secrets に以下を入れてください:
# OPENAI_API_KEY = "sk-...."
# (任意) OPENAI_MODEL = "gpt-4.1"
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
except Exception:
    st.error("OPENAI_API_KEY が未設定です。Streamlit Cloud の Settings > Secrets に設定してください。")
    st.stop()

OPENAI_MODEL = st.secrets.get("OPENAI_MODEL", "gpt-4.1")

client = OpenAI(api_key=OPENAI_API_KEY)


# -----------------------------
# Prompt
# -----------------------------
SYSTEM_PROMPT = """あなたは優秀な日本語の編集者兼エッセイストです。
以下のルールに厳密に従って出力してください。

# 出力フォーマット（厳守）
1行目：タイトルのみ（装飾記号や「タイトル：」などの接頭辞は付けない）
2行目：空行
3行目以降：本文

# 注意
- 出力は1パターンのみ
- 入力文の表現をそのまま使わず、必ず言い換える
- 思想エッセイ風で、読者に問いかける構成にする
"""

USER_INSTRUCTION = """以下の文章を、SNS投稿向けの約2000文字の文章に書き換えてください。

条件：
・タイトルを必ず付ける
・内容を分かりやすくする比喩を入れる
・関連する専門用語を自然に使用する
・「なぜそう言えるのか」という根拠を最低2つ以上入れる
・絵文字を適度に入れる（多すぎない）
・思想エッセイ風で、読者に問いかける構成にする
・入力された文章のそのままの表現は使用しない
・本文はできるだけ「約2000文字」に近づける（目安: 1800〜2200文字）

文章：
"""


def build_messages(src_text: str, extra_adjust: str = ""):
    user = USER_INSTRUCTION + src_text.strip()
    if extra_adjust:
        user += "\n\n追加調整指示：\n" + extra_adjust.strip()
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def split_title_and_body(text: str) -> tuple[str, str]:
    lines = (text or "").strip().splitlines()
    if not lines:
        return "", ""
    title = lines[0].strip()

    body_lines = lines[1:]
    while body_lines and body_lines[0].strip() == "":
        body_lines = body_lines[1:]
    body = "\n".join(body_lines).strip()
    return title, body


def jst_now_str() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M")


def count_chars(s: str) -> int:
    return len(s)


def generate_once(src: str, extra_adjust: str = "") -> str:
    res = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=build_messages(src, extra_adjust=extra_adjust),
        temperature=0.85,
    )
    return (res.choices[0].message.content or "").strip()


def generate_around_2000(src: str) -> tuple[str, str, str]:
    """
    1) まず生成
    2) 本文が短すぎ/長すぎなら、追加指示を付けて最大2回リトライ
    """
    raw = generate_once(src)
    title, body = split_title_and_body(raw)
    n = count_chars(body)

    # 目標レンジ（だいたい）
    low, high = 1800, 2200

    if low <= n <= high and title and body:
        return title, body, raw

    # リトライ指示を作る
    for _ in range(2):
        if n < low:
            adjust = (
                f"本文が{n}文字で短い。"
                f"根拠をさらに具体化し、比喩や具体例を増やし、"
                f"論理のつなぎを補強して、本文を{low}〜{high}文字に増やして。"
                f"冗長な繰り返しは避ける。"
            )
        else:
            adjust = (
                f"本文が{n}文字で長い。"
                f"主張を保ったまま重複や回り道を削り、"
                f"核心（比喩・専門用語・根拠2つ以上・問いかけ構成）を残して、"
                f"本文を{low}〜{high}文字に収めて。"
            )

        raw = generate_once(src, extra_adjust=adjust)
        title, body = split_title_and_body(raw)
        n = count_chars(body)

        if low <= n <= high and title and body:
            break

    return title, body, raw


# -----------------------------
# Session State
# -----------------------------
if "output_title" not in st.session_state:
    st.session_state.output_title = ""
if "output_body" not in st.session_state:
    st.session_state.output_body = ""
if "output_meta" not in st.session_state:
    st.session_state.output_meta = ""
if "output_full" not in st.session_state:
    st.session_state.output_full = ""


# -----------------------------
# UI
# -----------------------------
st.subheader("Idea Terminal")
src = st.text_area(
    "入力文章（都度入力）",
    value="",
    height=240,
    placeholder="ここに文章を貼り付けてください",
)

col1, col2 = st.columns([1, 1])
with col1:
    generate_btn = st.button("執筆開始", use_container_width=True)
with col2:
    clear_btn = st.button("クリア", use_container_width=True)

if clear_btn:
    st.session_state.output_title = ""
    st.session_state.output_body = ""
    st.session_state.output_meta = ""
    st.session_state.output_full = ""
    st.rerun()

if generate_btn:
    if not src.strip():
        st.warning("入力文章が空です。")
        st.stop()

    with st.spinner("執筆中...（約2000字に調整しています）"):
        try:
            title, body, raw = generate_around_2000(src)
        except Exception as e:
            st.error(f"生成に失敗しました: {e}")
            st.stop()

    # 表示とコピー用のメタ
    meta = f"文字数: {count_chars(body)}  |  出力日時: {jst_now_str()}"
    full = f"{title}\n{meta}\n\n{body}".strip()

    st.session_state.output_title = title
    st.session_state.output_body = body
    st.session_state.output_meta = meta
    st.session_state.output_full = full


# -----------------------------
# Output
# -----------------------------
if st.session_state.output_full:
    st.divider()
    st.subheader("Output")

    # 先頭：タイトル
    st.markdown(f"## {st.session_state.output_title}")

    # その下：文字数＋出力日時
    st.caption(st.session_state.output_meta)

    # コピーボタン（確実にクリップボードへ）
    copy_text = (
        st.session_state.output_full
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("$", "\\$")
    )

    components.html(
        f"""
        <div style="margin: 10px 0 14px 0;">
          <button id="copyBtn"
            style="
              padding: 10px 14px;
              border-radius: 10px;
              border: 1px solid rgba(255,255,255,0.2);
              cursor: pointer;
              width: 100%;
              font-size: 14px;
            ">
            📋 出力をコピー（タイトル+メタ+本文）
          </button>
          <div id="copyMsg" style="margin-top: 8px; font-size: 12px; opacity: 0.85;"></div>
        </div>

        <script>
          const textToCopy = `{copy_text}`;
          const btn = document.getElementById("copyBtn");
          const msg = document.getElementById("copyMsg");

          btn.addEventListener("click", async () => {{
            try {{
              await navigator.clipboard.writeText(textToCopy);
              msg.textContent = "コピーしました ✅";
              setTimeout(() => msg.textContent = "", 1500);
            }} catch (e) {{
              msg.textContent = "コピーに失敗しました。ブラウザの権限設定をご確認ください。";
            }}
          }});
        </script>
        """,
        height=90,
    )

    # その下：本文
    st.markdown(st.session_state.output_body)
