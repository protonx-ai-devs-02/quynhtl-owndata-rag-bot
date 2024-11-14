import streamlit as st
import time, os
from openai import OpenAI
from dotenv import load_dotenv

logo = 'https://product.hstatic.net/200000140863/product/set_mini_crusty__1a324c901b0347c6afa7bc818d387e46_1024x1024.png'
# Display the logo in the sidebar
st.sidebar.caption(':red[HIRO BOT]')
st.sidebar.image(logo, width=500)
st.title("^v^ ")
st.write("Chào mừng bạn đến với Hiro Bot")

load_dotenv()

openai_api_key=os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# Use GPT model
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

if "messages" not in st.session_state:
    st.session_state.messages = []

hello = "Chúc bạn ngày tốt lành!"
st.session_state.messages.append(
    {
        "role": "assistant",
        "content": hello
    }
)

added_one = False
for message in st.session_state.messages:
    if not added_one and message["content"] == hello:
        added_one = True
        with st.chat_message('assistant'):
            time.sleep(0.2)
            st.markdown(hello)
    else:
        if message["content"] != hello:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

if prompt := st.chat_input("Ask your questions?"):
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message('user'):
        st.markdown(prompt)

    with st.chat_message('assistant'):
        full_res = ""
        holder = st.empty()
        for response in client.chat.completions.create(
            model = st.session_state["openai_model"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        ):
            full_res += (response.choices[0].delta.content or "")
            holder.markdown(full_res + "▌")
        holder.markdown(full_res)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": full_res
        }
    )