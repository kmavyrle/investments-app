# gmail_read_and_download.py
import os, base64, re
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

#SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
TOKEN = Path(r"C:\Users\kmavy\Documents\mydocs\4Sight\token.json")
CREDS = Path(r"C:\Users\kmavy\Documents\mydocs\4Sight\credentials.json")
OUTDIR = Path(r"C:\Users\kmavy\Documents\mydocs\4Sight\attachments")

def get_service():
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS), SCOPES)
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
        TOKEN.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def header(headers, name, default=""):
    name = name.lower()
    for h in headers or []:
        if h.get("name","").lower() == name:
            return h.get("value", default)
    return default

def safe_name(name: str) -> str:
    # remove pathy chars and trim
    name = re.sub(r'[\\/:*?"<>|]+', "_", name).strip()
    return name[:180] or "file"

def list_messages(svc, query, max_results=50):
    res = svc.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    return res.get("messages", []) or []

def download_attachments(svc, msg_id, skip_inline=True, overwrite_existing=True):
    msg = svc.users().messages().get(userId="me", id=msg_id, format="full").execute()
    payload = msg.get("payload", {}) or {}
    parts = payload.get("parts") or [payload]  # handle single-part emails

    stack = parts[:]
    saved = []
    while stack:
        p = stack.pop()
        stack.extend(p.get("parts", []) or [])
        filename = p.get("filename") or ""
        if not filename:
            continue

        # skip inline images/signatures
        headers_map = {h.get("name","").lower(): h.get("value","") for h in p.get("headers", [])}
        disp = headers_map.get("content-disposition", "")
        if skip_inline and "inline" in disp.lower():
            continue

        body = p.get("body", {}) or {}
        if "attachmentId" in body:
            att = svc.users().messages().attachments().get(
                userId="me", messageId=msg_id, id=body["attachmentId"]
            ).execute()
            data = att.get("data")
        else:
            data = body.get("data")

        if not data:
            continue

        OUTDIR.mkdir(parents=True, exist_ok=True)
        path = OUTDIR / safe_name(filename)

        if overwrite_existing:
            # Write atomically: write to temp, then replace target
            tmp_path = path.with_name(path.name + ".tmp")
            if tmp_path.exists():
                os.remove(tmp_path)
            with open(tmp_path, "wb") as f:
                f.write(base64.urlsafe_b64decode(data))
            # If the final exists (e.g., signals.csv), replace it
            os.replace(tmp_path, path)  # atomic on Windows & POSIX
        else:
            # avoid overwrites by numbering
            if path.exists():
                stem, ext = os.path.splitext(path.name)
                i = 1
                while path.exists():
                    path = OUTDIR / f"{stem} ({i}){ext}"
                    i += 1
            with open(path, "wb") as f:
                f.write(base64.urlsafe_b64decode(data))

        saved.append(str(path))
    return msg, saved



def download_signals():
    svc = get_service()
    subj = 'Signals'#input('Subject filter (e.g. Invoice) [leave blank for all]: ').strip()
    max_n = 1
    #max_n = int((input('Max emails to scan [50]: ').strip() or "50"))
    # Build a Gmail query. Always require attachments since we’re downloading them.
    query = "has:attachment"
    if subj:
        # Exact phrase search improves precision; change to subject:Invoice for loose match.
        query += f' subject:"{subj}"'
    # You can add date filters here if you want:
    # query += " newer_than:30d"

    try:
        msgs = list_messages(svc, query, max_results=max_n)
        if not msgs:
            print("No matching emails found.")
            return

        print(f"\nFound {len(msgs)} emails. Saving attachments to: {OUTDIR.resolve()}\n")
        total_files = 0
        for m in msgs:
            msg, files = download_attachments(svc, m["id"], skip_inline=True)
            headers = msg.get("payload", {}).get("headers", [])
            print(f"From: {header(headers,'From')}")
            print(f"Date: {header(headers,'Date')}")
            print(f"Subject: {header(headers,'Subject')}")
            if files:
                for p in files:
                    print(f"  saved: {p}")
                total_files += len(files)
            else:
                print("  (no downloadable attachments)")
            print("-" * 60)
        print(f"\nDone. Files saved: {total_files}")

    except HttpError as e:
        print(f"Gmail API error: {e}")


def delete_emails_by_subject(
    subject: str,
    move_to_trash: bool = True,          # True = safer (recoverable); False = permanent delete
    newer_than: str | None = None,       # e.g. "7d", "6m", "2y"
    older_than: str | None = None,       # e.g. "30d"
    include_query: str | None = None,    # any extra Gmail search (from:, label:, etc.)
    max_to_delete: int | None = None,    # limit, e.g., 200
    dry_run: bool = False                # set True to preview without deleting
):
    """
    Delete (or trash) emails matching a subject plus optional time/extra filters.
    Returns (count, ids).
    """
    svc = get_service()
    # Build Gmail search query
    # Exact phrase match for subject; change to subject:Signals (without quotes) for loose match
    q_parts = [f'subject:"{subject}"']
    if newer_than:
        q_parts.append(f"newer_than:{newer_than}")
    if older_than:
        q_parts.append(f"older_than:{older_than}")
    if include_query:
        q_parts.append(include_query)
    query = " ".join(q_parts)

    ids = list_messages_all(svc, query, max_results=max_to_delete)

    if dry_run:
        print(f"[DRY RUN] Would delete {len(ids)} message(s) matching: {query}")
        return 0, ids

    user = "me"
    count = 0
    for mid in ids:
        if move_to_trash:
            svc.users().messages().trash(userId=user, id=mid).execute()
        else:
            # Note: delete() permanently removes the message (if it's already in Trash).
            svc.users().messages().delete(userId=user, id=mid).execute()
        count += 1

    print(f"Deleted {'(trashed)' if move_to_trash else '(permanent)'}: {count} message(s). Query: {query}")
    return count, ids


def list_messages_all(svc, query, max_results=None):
    """Return all matching message IDs (handles pagination)."""
    user = "me"
    ids, page_token = [], None
    while True:
        req = svc.users().messages().list(
            userId=user, q=query, pageToken=page_token, maxResults=min(500, max_results or 500)
        )
        res = req.execute()
        ids.extend([m["id"] for m in res.get("messages", [])])
        page_token = res.get("nextPageToken")
        if not page_token or (max_results and len(ids) >= max_results):
            break
    return ids if not max_results else ids[:max_results]