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

st.title("Python")

st.markdown("""
<style>

/* 全体の上余白を減らす */
.block-container {
    padding-top: 2rem !important;
}

/* テキストエリアを少し上に詰める */
div[data-testid="stTextArea"] {
    margin-top: -10px;
}

/* Begin the draft ボタンを大きく横長に */
div.stButton {
    margin-top: 30px;   /* ←ここで位置調整（増やすと下がる） */
}

div.stButton {
    margin-top: -150px;
    transform: translateX(3000px);  /* +で右 / -で左 */
}


div.stButton > button {
    width: 100%;
    height: 60px;
    font-size: 22px;
    font-weight: bold;
    border-radius: 10px;
}


/* 押したとき気持ちよく */
div.stButton > button:hover {
    transform: scale(1.01);
}

/* 出力エリア折り返し保険 */
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

text = st.text_area("", height=200)

# ---- プロンプト（本文） ----

def load_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_DRAFT = load_prompt("prompt_draft.txt")

def build_user_prompt_draft(src: str) -> str:
    return f"""
    
以下の入力文をもとに、SNS投稿向けの思想エッセイを書いてください。

目的：
単なる書き換えではなく、文章の内容から一歩踏み込み、
現代の私たちの生き方に接続した「一つの主張」を提示すること。

スタイル：
・入力文の内容を約2000文字の文章に書き換える
・最初にタイトルを書く
・思想エッセイ風
・冒頭は、現代の日常と結びつけつつ、読者の思考や価値観を揺さぶる一文から始める
・一度あえて反対意見や一般論を出し、それを論破する
・なぜそう言えるのか、比喩や具体例で深掘りする
・入力文をそのまま使わない
・痛烈で容赦のない言葉を使う
・遠慮せず断言する
・哲学的だが分かりやすい
・読者に不快感すら与えてよい

元の文章：
<<<
{src}
>>>
"""

# ---- ボタン ----

if st.button("Begin", disabled=not text):
    # 本文生成
    res = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": SYSTEM_DRAFT},
            {"role": "user", "content": build_user_prompt_draft(text)},
        ],
        temperature=0.7,
    )
    st.session_state.draft_text = res.choices[0].message.content

# 出力（ドラフトが存在する場合）
if st.session_state.draft_text:
    st.subheader("Output")

    # 空行を除去して行配列を作る
    lines = [l.strip() for l in st.session_state.draft_text.splitlines() if l.strip()]

    # 先頭が【タイトル】系なら捨てる
    if lines and "タイトル" in lines[0]:
        lines = lines[1:]

    title_line = lines[0] if lines else ""
    body = "\n".join(lines[1:]) if len(lines) > 1 else ""

    now = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M")

    # 表示と同じ基準で文字数を計算
    full_output_tmp = f"""{title_line}

{body}"""
    char_count = len(full_output_tmp)

    full_output = f"""{title_line}

文字数: {char_count}文字
日時: {now}

{body}"""

    st.code(full_output, language="markdown")








