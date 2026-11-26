import json
from pathlib import Path

import streamlit as st
from scripts.rag_query import (answer_query, section_head, label, chat_answer,
                               warm_llm, _load, NOT_FOUND, DISCLAIMER)

HINDI_FILE = Path(__file__).parent / "data" / "hindi_sections.json"

st.set_page_config(page_title="Nyay AI", page_icon="⚖️")


@st.cache_resource(show_spinner="Model taiyar ho raha hai (pehli baar 1-2 min)...")
def warm_up():
    _load()        # embedder, Chroma, reranker
    warm_llm()     # Gemma into memory
    return True


warm_up()


@st.cache_data(show_spinner=False)
def load_hindi():
    if not HINDI_FILE.exists():
        return {}
    return json.loads(HINDI_FILE.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def find_clauses(q: str):
    res = answer_query(q)
    return {
        "mode": res["mode"],
        "options": [
            {"source": c["source"], "section": c["section"], "title": c["title"],
             "rerank": c["rerank"], "label": label(c), "text": section_head(c)}
            for c in res["options"]
        ],
    }


@st.cache_data(show_spinner=False)
def make_chat(q: str, law_text: str):
    return chat_answer(q, law_text)


def hindi_key(opt: dict):
    if "Landlords" in opt["source"]:
        return f"tn_{opt['section']}"
    if "consumer" in opt["source"].lower():
        return f"cpa_{opt['section']}"
    return None


def render_answer(res: dict):
    if res["mode"] == "not_found" or not res["options"]:
        st.write(NOT_FOUND)
        return

    top = res["options"][0]
    entry = load_hindi().get(hindi_key(top) or "")

    if entry:
        # Hand-written, reviewed Hindi always wins
        st.markdown(f"**{entry['title_hi']}**")
        st.write(entry["summary_hi"])
        if not entry.get("reviewed"):
            st.caption("यह AI-तैयार अनुवाद है, वकील से जाँच करवा लें।")
    elif res.get("chat"):
        st.write(res["chat"])
    else:
        st.info("Is sawaal ka seedha jawab abhi nahi ban paaya. Neeche kanoon ka mool paath dekhiye.")

    with st.expander(f"Kanoon ka mool paath: {top['label']}"):
        st.write(" ".join(top["text"].split())[:900])

    others = [f"Section {o['section']}" for o in res["options"][1:] if o["section"]]
    if others:
        st.caption("Sambandhit dhaaraen: " + ", ".join(others))

    st.caption(DISCLAIMER)


if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("⚖️ Nyay AI")
st.caption("Kiraye aur upbhokta (consumer) kanoon ki jaankari, Hindi ya Hinglish mein")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m["role"] == "user":
            st.write(m["content"])
        else:
            render_answer(m["content"])

prompt = st.chat_input("Apna sawaal likhiye (Hindi ya Hinglish mein)")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Kanoon mein dhoondh rahe hain..."):
            res = find_clauses(prompt)

        if res["options"]:
            top = res["options"][0]
            if not load_hindi().get(hindi_key(top) or ""):
                with st.spinner("Jawab bana rahe hain..."):
                    res["chat"] = make_chat(prompt, top["text"])

        render_answer(res)

    st.session_state.messages.append({"role": "assistant", "content": res})