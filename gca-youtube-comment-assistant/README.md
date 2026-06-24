# GCA YouTube Comment Assistant - Cloud Version

This version is designed for Streamlit Community Cloud so Kevin can use it from iPhone, iPad, or Mac through a private webpage.

## Important

Do NOT upload `client_secret.json` to GitHub.

This version uses Streamlit Secrets instead.

## Deployment overview

1. Upload these files to a private GitHub repository.
2. Deploy the repo on Streamlit Community Cloud.
3. Copy your Streamlit app URL.
4. In Google Cloud, create an OAuth Client ID of type "Web application".
5. Add this redirect URI:

   https://YOUR-STREAMLIT-APP-URL.streamlit.app

6. Add your secrets to Streamlit Cloud Advanced Settings.

## Required Streamlit Secrets

Paste this into Streamlit Cloud Secrets and replace the values:

```toml
OPENAI_API_KEY = "your_openai_api_key"
OPENAI_MODEL = "gpt-4.1-mini"

GOOGLE_CLIENT_ID = "your_google_web_oauth_client_id"
GOOGLE_CLIENT_SECRET = "your_google_web_oauth_client_secret"
REDIRECT_URI = "https://your-streamlit-app-url.streamlit.app"
```

## Safety

Approval-only mode. Nothing posts unless Kevin clicks Approve & Post.
