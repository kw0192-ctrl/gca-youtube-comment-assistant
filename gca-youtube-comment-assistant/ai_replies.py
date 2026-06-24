import streamlit as st
from openai import OpenAI

SYSTEM_PROMPT = """
You write YouTube comment replies for Kevin from Green Country Adventures.

Tone:
- Friendly, helpful, conversational
- Real Sea-Doo owner experience
- Short enough for YouTube comments
- Never overly salesy
- Never argue with trolls
- If the viewer asks about gear, mention Kevin's gear/accessories page only when relevant
- If the viewer asks about stereo upgrades, Jetwerx and discount code ADVENTURETIME may be mentioned when relevant
- Do not give legal, tax, medical, financial, or unsafe boating advice
- Encourage safe riding when speed, dogs, kids, or beginners are discussed
"""

def generate_reply(comment_text, video_title="", author="", previous_reply=None):
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        return "OpenAI API key is missing from Streamlit Secrets."

    model = st.secrets.get("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI(api_key=api_key)

    user_prompt = f"""
Video title: {video_title}
Viewer name: {author}
Viewer comment: {comment_text}

Write one suggested reply.

Rules:
- 1 to 3 sentences
- Sound like Kevin
- Helpful and natural
- Do not include hashtags
"""

    if previous_reply:
        user_prompt += f"""

Previous suggestion:
{previous_reply}

Generate a different version.
"""

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
    )

    return response.output_text.strip()
