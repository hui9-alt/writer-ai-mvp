import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from zoneinfo import ZoneInfo
from datetime import datetime


# .env を読み込む
load_dotenv()

# APIキーを使ってクライアント作成
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("Writer AI")

st.markdown("""
<style>
/* 保険：st.code以外にも当たる可能性のある pre を広めに折り返す */
pre, pre code {
    white-space: pre-wrap !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
}
</style>
""", unsafe_allow_html=True)


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
    
以下の入力文をもとに、SNS投稿向けの思想エッセイを書いてください。

目的：
単なる要約ではなく、文章の内容から一歩踏み込み、
現代の私たちの生き方に接続した「一つの主張」を提示すること。

文字数：
約1000文字
  
スタイル：
・最初にタイトルを書く
・思想エッセイ風
・入力文に関連して、現代社会や人間の生き方に対する「鋭い主張」を打ち出すこと。
・冒頭は、読者の思考や価値観を揺さぶる一文から始める
・一度あえて反対意見や一般論を出し、それを論破する
・なぜそう言えるのか、比喩や具体例で深掘りする
・現代の日常（SNS・仕事・孤独・お金、恋愛・勉強など）と結びつける

注意：
・入力文をそのまま使わない
・痛烈で容赦のない言葉を使う
・遠慮せず断言する
・哲学的だが分かりやすい
・綺麗にまとめようとしない
・読者に不快感すら与えてよい

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
        temperature=0.2,
    )
    st.session_state.draft_text = res.choices[0].message.content

# 出力（ドラフトが存在する場合）
if st.session_state.draft_text:
    st.subheader("✍️ Output")

    lines = st.session_state.draft_text.strip().splitlines()
    title_line = lines[0].strip()
    body = "\n".join(lines[1:]).strip()

    char_count = len(title_line + body)

    now = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M")

　　　　full_output = f"""{title_line}

　　　　文字数: {char_count}文字
　　　　日時: {now}

   {body}"""

    
    st.code(full_output, language="markdown")







