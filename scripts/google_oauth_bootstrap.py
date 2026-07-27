"""one-time local run: opens a browser, log in as the demo Gmail account, and this
prints the refresh token to paste into .env as GOOGLE_REFRESH_TOKEN."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

from app.config import settings  # noqa: E402


def main() -> None:
    client_config = {
        "installed": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, scopes=settings.google_scopes_list)

    print("a browser window is about to open -- log in as the demo account, not your own.\n")
    creds = flow.run_local_server(port=0)

    print("\nGOOGLE_REFRESH_TOKEN=" + creds.refresh_token)


if __name__ == "__main__":
    main()
