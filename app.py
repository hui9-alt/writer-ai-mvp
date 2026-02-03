from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
import os

import streamlit as st
import streamlit.components.v1 as components

# OpenAI SDK（pip install openai）
from openai import OpenAI


# -----------------------------
# 基本設定
# -----------------------------
APP_TITLE = "Writer AI"
TZ = ZoneInfo("Asia/Tokyo")

st.set_page_config(page_title=APP_TITLE, page_icon="✍️", layout="centered")
st.title(APP_TITLE)

# Secrets / Env
def get_secret(key: str, default: str | None = None) -> str | None:
    # Streamlit Cloud: st.secrets
    if key in st.secrets:
        return str(st.secrets[key])
    # Local: env
    return os.getenv(key, default)


OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
OPENAI_MODEL = get_secret("OPENAI_MODEL", "gpt-4.1")  # 好きなモデル名に変更OK
OPENAI_BASE_URL = get_secret("OPENAI_BASE_URL")  # 互換エンドポイントがあるなら設定

if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY が未設定です。Streamlit Secrets か環境変数に設定してください。")
    st.stop()

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL or None,
)

# -----------------------------
# prompt_draft.txt 読み込み
# -----------------------------
@st.cache_data(show_spinner=False)
def load_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


DEFAULT_INPUT = load_text_file("prompt_draft.txt")

# -----------------------------
# 生成プロンプト
# -----------------------------
SYSTEM_PROMPT = """あなたは優秀な日本語の編集者兼エッセイストです。
以下のルールに厳密に従って出力してください。

# 出力フォーマット（厳守）
1行目：タイトルのみ（装飾記号や「タイトル：」などの接頭辞は付けない）
2行目：空行
3行目以降：本文

# 注意
- 出力は1パターンのみ
- 完成度を最大化する
"""

USER_INSTRUCTION = """以下の文章を、SNS投稿向けの約2000文字の文章に書き換えてください。

条件：
・タイトルを必ず付ける
・内容を分かりやすくする比喩を入れる
・関連する専門用語を自然に使用する
・「なぜそう言えるのか」という根拠を最低2つ以上入れる
・絵文字を適度に入れる（多すぎない）
・思想エッセイ風で、読者に問いかける構成にする
・入力された文章のそのままの表現は使用しない。

文章：
"""

def build_messages(src_text: str):
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_INSTRUCTION + src_text.strip()},
    ]


# -----------------------------
# 出力を「タイトル + 本文」に分割
# -----------------------------
def split_title_and_body(text: str) -> tuple[str, str]:
    lines = (text or "").strip().splitlines()
    if not lines:
        return "", ""

    title = lines[0].strip()

    # 2行目が空行の想定だが、多少崩れても本文を抽出
    body_lines = lines[1:]
    # 先頭の空行を除去
    while body_lines and body_lines[0].strip() == "":
        body_lines = body_lines[1:]

    body = "\n".join(body_lines).strip()
    return title, body


def jst_now_str() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M")


def count_chars(s: str) -> int:
    # 日本語の「文字数」= Pythonのlenで概ねOK（改行も1文字として数える）
    return len(s)


# -----------------------------
# セッション状態
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
    "入力文章",
    value=DEFAULT_INPUT,
    height=240,
    placeholder="ここに文章を貼り付けてください（prompt_draft.txt があれば初期表示されます）",
)

col1, col2 = st.columns([1, 1])
with col1:
    generate = st.button("執筆開始", use_container_width=True)
with col2:
    clear = st.button("クリア", use_container_width=True)

if clear:
    st.session_state.output_title = ""
    st.session_state.output_body = ""
    st.session_state.output_meta = ""
    st.session_state.output_full = ""
    st.rerun()

if generate:
    if not src.strip():
        st.warning("入力文章が空です。")
        st.stop()

    with st.spinner("執筆中..."):
        try:
            res = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=build_messages(src),
                temperature=0.85,
            )
            raw = res.choices[0].message.content or ""
        except Exception as e:
            st.error(f"生成に失敗しました: {e}")
            st.stop()

    title, body = split_title_and_body(raw)

    # UI表示用メタ
    # コピー対象には「タイトル + メタ + 本文」を一括で入れる
    meta = f"文字数: {count_chars(body)}  |  出力日時: {jst_now_str()}"
    full = f"{title}\n{meta}\n\n{body}".strip()

    st.session_state.output_title = title
    st.session_state.output_body = body
    st.session_state.output_meta = meta
    st.session_state.output_full = full


# -----------------------------
# 出力表示（生成後）
# -----------------------------
if st.session_state.output_full:
    st.divider()
    st.subheader("Output")

    # 先頭：タイトル
    st.markdown(f"## {st.session_state.output_title}")

    # その下：文字数＋出力日時
    st.caption(st.session_state.output_meta)

    # コピーボタン（クリップボード）
    # Streamlit単体だと「押してコピー」を安定実装しづらいので最小限のJSを使用
    copy_text = st.session_state.output_full.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
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
            📋 出力をコピー
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
        height=80,
    )

    # その下：生成された文章（本文）
    st.markdown(st.session_state.output_body)
