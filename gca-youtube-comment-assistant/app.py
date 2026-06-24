import streamlit as st
from datetime import datetime
from database import init_db, get_unhandled_comments, save_comment, mark_comment_status, clear_new_comments
from youtube_client import (
    get_auth_url,
    handle_oauth_callback,
    is_logged_in,
    get_youtube_service,
    fetch_recent_comments,
    post_reply,
)
from ai_replies import generate_reply, get_google_sheet

st.set_page_config(page_title="GCA YouTube Comment Assistant", layout="wide")

init_db()

SHEET_TAB_NAME = "AI Training Data"

st.title("Green Country Adventures YouTube Comment Assistant")
st.caption("Approval-only mode. Nothing posts unless you click Approve & Post.")

if "code" in st.query_params:
    if handle_oauth_callback():
        st.success("YouTube connected successfully.")

if not is_logged_in():
    st.warning("YouTube is not connected yet.")
    try:
        st.link_button("Connect YouTube", get_auth_url())
    except Exception as e:
        st.error(f"OAuth setup is incomplete: {e}")
    st.stop()

with st.sidebar:
    st.header("Controls")
    max_results = st.slider("Comments to fetch", 5, 50, 25)
    st.success("YouTube connected")

    st.divider()
    st.caption("Use this once after changing filters if old comments are still showing.")
    if st.button("Clear Unhandled Inbox"):
        clear_new_comments()
        st.success("Unhandled inbox cleared. Fetch latest comments again.")
        st.rerun()

if st.button("Fetch Latest Comments"):
    with st.spinner("Fetching YouTube comments..."):
        youtube = get_youtube_service()
        comments = fetch_recent_comments(youtube, max_results=max_results)
        for c in comments:
            save_comment(c)
    st.success("Latest comments fetched. Own comments and already-replied threads were skipped.")

comments = get_unhandled_comments()

if not comments:
    st.info("No unhandled comments yet. Click Fetch Latest Comments.")
else:
    for comment in comments:
        st.divider()
        st.subheader(comment["video_title"] or "YouTube Comment")
        st.write(f'**Viewer:** {comment["author"]}')
        st.write(comment["text"])

        key_base = comment["comment_id"]

        suggestion_key = f"suggestion_{key_base}"
        original_ai_key = f"original_ai_draft_{key_base}"
        change_key = f"change_request_{key_base}"
        version_key = f"reply_version_{key_base}"

        if suggestion_key not in st.session_state:
            first_reply = generate_reply(
                comment_text=comment["text"],
                video_title=comment["video_title"] or "",
                author=comment["author"] or ""
            )
            st.session_state[suggestion_key] = first_reply
            st.session_state[original_ai_key] = first_reply
            st.session_state[version_key] = 0

        reply_box_key = f"reply_box_{key_base}_{st.session_state[version_key]}"

        reply_text = st.text_area(
            "Suggested reply",
            value=st.session_state[suggestion_key],
            key=reply_box_key,
            height=120
        )

        change_request = st.text_area(
            "Suggested changes / personal notes",
            key=change_key,
            height=80,
            placeholder="Example: Mention that I personally like the stereo upgrade best, but the ladder is probably the most practical upgrade."
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("Approve & Post", key=f"approve_{key_base}"):
                final_reply = st.session_state[reply_box_key]

                try:
                    youtube = get_youtube_service()
                    post_reply(
                        youtube=youtube,
                        parent_comment_id=comment["comment_id"],
                        reply_text=final_reply
                    )
                    mark_comment_status(comment["comment_id"], "posted")
                    st.success("Reply posted to YouTube.")
                except Exception as e:
                    st.error(f"YouTube post failed: {e}")
                    st.stop()

                try:
                    sheet = get_google_sheet()
                    worksheet = sheet.worksheet(SHEET_TAB_NAME)

                    worksheet.append_row([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "YouTube",
                        comment["video_title"] or "",
                        comment["author"] or "",
                        comment["text"] or "",
                        st.session_state.get(original_ai_key, ""),
                        st.session_state.get(change_key, ""),
                        final_reply,
                        "Posted",
                    ])

                    st.success("Saved to Google Sheet.")
                except Exception as e:
                    st.error(f"Google Sheet save failed: {e}")
                    st.stop()

                st.stop()

        with col2:
            if st.button("Generate Updated Reply", key=f"regen_{key_base}"):
                updated_reply = generate_reply(
                    comment_text=comment["text"],
                    video_title=comment["video_title"] or "",
                    author=comment["author"] or "",
                    previous_reply=(
                        st.session_state[reply_box_key]
                        + "\n\nKevin's requested changes:\n"
                        + st.session_state.get(change_key, "")
                    )
                )

                st.session_state[suggestion_key] = updated_reply
                st.session_state[version_key] += 1
                st.rerun()

        with col3:
            if st.button("Skip", key=f"skip_{key_base}"):
                mark_comment_status(comment["comment_id"], "skipped")
                st.rerun()

        with col4:
            if st.button("Mark Important", key=f"important_{key_base}"):
                mark_comment_status(comment["comment_id"], "important")
                st.rerun()
