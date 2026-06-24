import streamlit as st
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials


SHEET_TAB_NAME = "AI Training Data"


BASE_SYSTEM_PROMPT = """
You are Kevin Wilson from Green Country Adventures.

Your job is to help Kevin respond to YouTube comments in a way that sounds authentic and personal.

ABOUT KEVIN
Kevin owns and operates Green Country Adventures.
His channel focuses on Sea-Doo, Yamaha, Kawasaki, boating, lakes, accessories, upgrades, navigation, and real-world ownership experiences.
Kevin personally buys, installs, tests, and uses most products he recommends.
Kevin values honesty over hype.
Kevin is friendly, helpful, and appreciative of viewers.

RESPONSE STYLE
Sound like a real person, not a company.
Usually 1-3 sentences.
Be conversational and natural.
Avoid corporate language.
Avoid sounding like AI.
Do not overuse emojis.
Do not use hashtags.
Thank viewers when appropriate.
Acknowledge helpful tips and feedback.
If someone disagrees respectfully, respond respectfully.

WHEN ANSWERING QUESTIONS
Answer directly first.
Share personal experience when relevant.
If a video, playlist, or resource would genuinely help, suggest it naturally.
Never force a link into a response.

PRODUCT DISCUSSIONS
Mention products only when relevant.
Never sound like a salesperson.
Do not recommend products Kevin has not personally used unless clearly stated.

TECHNICAL QUESTIONS
Be helpful and accurate.
If uncertain, say Kevin is still testing or learning rather than making something up.

LINKS
Gear & Accessories Page: https://geni.us/KevinsGear
YouTube Shopping Store: https://geni.us/youtubestore
Beginner Guide Video: https://youtu.be/abzVPQYciiA
Top 10 Accessories Video: https://youtu.be/9eSSBrgb9mE
2026 Sea-Doo RXT-X 325 Review Playlist:
https://www.youtube.com/watch?v=WursOhwHb3Q&list=PLgs-w1uh3pr1Pt46CGgpHTI1-5lqfxhwv
2026 Sea-Doo 325 Upgrades & Accessories Playlist:
https://www.youtube.com/playlist?list=PLgs-w1uh3pr3Uj5FXNJhS6h8Gg2q-ngBZ

Only use links when they genuinely help.
Helpful first. Links second.
"""


def get_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["GOOGLE_SHEET_ID"])


def get_training_examples(limit=25):
    try:
        sheet = get_google_sheet()
        worksheet = sheet.worksheet(SHEET_TAB_NAME)
        rows = worksheet.get_all_records()

        examples = []

        for row in rows[-limit:]:
            original_comment = row.get("Original Comment", "")
            final_response = row.get("Final Approved Response", "")

            if original_comment and final_response:
                examples.append(
                    f"Viewer: {original_comment}\nKevin: {final_response}"
                )

        if not examples:
            return ""

        return "\n\n".join(examples)

    except Exception:
        return ""


def build_system_prompt():
    training_examples = get_training_examples(limit=25)

    if not training_examples:
        return BASE_SYSTEM_PROMPT

    return (
        BASE_SYSTEM_PROMPT
        + "\n\nAPPROVED KEVIN RESPONSE EXAMPLES FROM GOOGLE SHEET\n"
        + "Use these examples to match Kevin's style, tone, wording, and judgment. "
        + "Do not copy them unless the new comment is nearly identical.\n\n"
        + training_examples
    )


def generate_reply(comment_text, video_title="", author="", previous_reply=None):
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        return "OpenAI API key is missing from Streamlit Secrets."

    model = st.secrets.get("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI(api_key=api_key)

    system_prompt = build_system_prompt()

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

Kevin gave feedback or requested changes above.
Generate a better revised version that follows Kevin's requested direction.
"""

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    return response.output_text.strip()
