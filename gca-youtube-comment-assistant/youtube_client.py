import streamlit as st
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def get_client_config():
    return {
        "web": {
            "client_id": st.secrets["GOOGLE_CLIENT_ID"],
            "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [st.secrets["REDIRECT_URI"]],
        }
    }


def make_flow():
    return Flow.from_client_config(
        get_client_config(),
        scopes=SCOPES,
        redirect_uri=st.secrets["REDIRECT_URI"]
    )


def get_auth_url():
    flow = make_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    st.session_state["oauth_state"] = state
    return auth_url


def handle_oauth_callback():
    params = st.query_params
    if "code" not in params:
        return False

    flow = make_flow()
    code = params["code"]

    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        st.session_state["youtube_creds"] = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }
        st.query_params.clear()
        return True
    except Exception as e:
        st.error(f"OAuth login failed: {e}")
        return False


def is_logged_in():
    return "youtube_creds" in st.session_state


def get_youtube_service():
    if not is_logged_in():
        raise RuntimeError("Not logged into YouTube yet.")

    creds = Credentials(**st.session_state["youtube_creds"])
    return build("youtube", "v3", credentials=creds)


def get_my_channel_id(youtube):
    response = youtube.channels().list(
        part="id,snippet",
        mine=True
    ).execute()

    items = response.get("items", [])
    if not items:
        raise ValueError("No YouTube channel found for this Google account.")

    return items[0]["id"], items[0]["snippet"].get("title", "My YouTube Channel")


def get_video_titles(youtube, video_ids):
    if not video_ids:
        return {}

    titles = {}
    ids = list(set([v for v in video_ids if v]))

    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        response = youtube.videos().list(
            part="snippet",
            id=",".join(batch)
        ).execute()

        for item in response.get("items", []):
            titles[item["id"]] = item["snippet"].get("title", "")

    return titles


def _get_author_channel_id(comment_snippet):
    """Safely return a comment author's YouTube channel ID."""
    return (
        comment_snippet
        .get("authorChannelId", {})
        .get("value", "")
    )


def _thread_has_reply_from_me(thread_item, my_channel_id):
    """Return True if this comment thread already has a reply from your channel."""
    replies = thread_item.get("replies", {}).get("comments", [])

    for reply in replies:
        reply_author_channel_id = _get_author_channel_id(reply.get("snippet", {}))
        if reply_author_channel_id == my_channel_id:
            return True

    return False


def fetch_recent_comments(youtube, max_results=25):
    """
    Fetch recent top-level YouTube comments that still need attention.

    This skips:
    - comments written by your own channel
    - comment threads where your channel has already replied
    """
    channel_id, channel_title = get_my_channel_id(youtube)

    request = youtube.commentThreads().list(
        part="snippet,replies",
        allThreadsRelatedToChannelId=channel_id,
        maxResults=max_results,
        order="time",
        textFormat="plainText"
    )
    response = request.execute()

    raw_comments = []
    video_ids = []

    for item in response.get("items", []):
        snippet = item.get("snippet", {})
        top_comment = snippet.get("topLevelComment", {})
        top = top_comment.get("snippet", {})

        top_author_channel_id = _get_author_channel_id(top)

        # Do not show comments you made yourself.
        if top_author_channel_id == channel_id:
            continue

        # Do not show comment threads you already replied to.
        if _thread_has_reply_from_me(item, channel_id):
            continue

        video_id = snippet.get("videoId", "")
        video_ids.append(video_id)

        raw_comments.append({
            "comment_id": top_comment.get("id", ""),
            "thread_id": item.get("id", ""),
            "video_id": video_id,
            "video_title": "",
            "author": top.get("authorDisplayName", ""),
            "text": top.get("textDisplay", ""),
            "published_at": top.get("publishedAt", ""),
            "channel_title": channel_title
        })

    titles = get_video_titles(youtube, video_ids)

    for c in raw_comments:
        c["video_title"] = titles.get(c["video_id"], "")

    return raw_comments


def post_reply(youtube, parent_comment_id, reply_text):
    body = {
        "snippet": {
            "parentId": parent_comment_id,
            "textOriginal": reply_text
        }
    }

    return youtube.comments().insert(
        part="snippet",
        body=body
    ).execute()
