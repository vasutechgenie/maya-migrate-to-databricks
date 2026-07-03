#!/usr/bin/env python3
"""
publish_to_linkedin.py -- post the blog series to LinkedIn via the official API.

Standard library only (no third-party deps). Reads a post's markdown, converts the body
to LinkedIn-friendly plain text, appends hashtags, and creates a text share as the
authenticated member.

Setup (one time):
  export LINKEDIN_ACCESS_TOKEN="..."          # member token with w_member_social scope
  export LINKEDIN_AUTHOR_URN="urn:li:person:..."  # from GET /v2/userinfo -> sub

Usage:
  python3 publish_to_linkedin.py --all --dry-run          # preview everything
  python3 publish_to_linkedin.py --file 01_migration_factory.md
  python3 publish_to_linkedin.py --all                    # publish all (careful!)

Always run --dry-run first.
"""
import argparse
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API_URL = "https://api.linkedin.com/v2/ugcPosts"
ASSET_URL = "https://api.linkedin.com/v2/assets?action=registerUpload"
MAX_LEN = 3000  # LinkedIn share commentary limit


def parse_post(path):
    """Return (meta, body_text) from a markdown file with YAML-ish front matter."""
    raw = open(path, encoding="utf-8").read()
    meta, body = {}, raw
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            fm = raw[3:end].strip()
            body = raw[end + 4:].lstrip("\n")
            for line in fm.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip().strip('"')
    return meta, body


def to_plain_text(md):
    """Convert a subset of markdown to clean plain text for a LinkedIn share."""
    lines = []
    for ln in md.splitlines():
        s = ln.rstrip()
        if s.startswith("```"):
            continue
        if s.lstrip().startswith("!["):           # embedded figure image
            continue
        if re.match(r"^\*Figure \d", s.lstrip()):  # figure caption line
            continue
        s = re.sub(r"^#{1,6}\s*", "", s)          # headings
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)     # bold
        s = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"\1", s)  # italics
        s = re.sub(r"`([^`]+)`", r"\1", s)         # inline code
        s = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", s)  # links -> text
        s = re.sub(r"^\s*[-*]\s+", "- ", s)        # bullets
        lines.append(s)
    text = "\n".join(lines).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def build_text(meta, body):
    text = to_plain_text(body)
    tags = meta.get("hashtags", "").strip()
    if tags:
        text = f"{text}\n\n{tags}"
    if len(text) > MAX_LEN:
        text = text[:MAX_LEN - 3].rstrip() + "..."
    return text


def _api_json(url, token, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Restli-Protocol-Version", "2.0.0")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def upload_image(path, token, author):
    """Register + upload an image; return its asset URN (feedshare-image recipe)."""
    reg = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": author,
            "serviceRelationships": [
                {"relationshipType": "OWNER",
                 "identifier": "urn:li:userGeneratedContent"}
            ],
        }
    }
    resp = _api_json(ASSET_URL, token, reg)["value"]
    asset = resp["asset"]
    upload_url = (resp["uploadMechanism"]
                  ["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]
                  ["uploadUrl"])
    with open(path, "rb") as fh:
        blob = fh.read()
    put = urllib.request.Request(upload_url, data=blob, method="POST")
    put.add_header("Authorization", f"Bearer {token}")
    put.add_header("Content-Type", "image/png")
    with urllib.request.urlopen(put) as r:
        r.read()
    return asset


def publish(text, token, author, dry_run=True, image_path=None, image_caption=""):
    share = {
        "shareCommentary": {"text": text},
        "shareMediaCategory": "NONE",
    }
    if dry_run:
        print("----- DRY RUN: would POST the following text -----")
        print(text)
        if image_path:
            print(f"[image attached: {os.path.basename(image_path)}]")
        print(f"----- ({len(text)} chars) -----\n")
        return {"dry_run": True}
    if image_path and os.path.exists(image_path):
        asset = upload_image(image_path, token, author)
        share["shareMediaCategory"] = "IMAGE"
        share["media"] = [{
            "status": "READY",
            "media": asset,
            "description": {"text": image_caption[:200]} if image_caption else {},
            "title": {"text": "Figure"},
        }]
    payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": share},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Restli-Protocol-Version", "2.0.0")
    try:
        with urllib.request.urlopen(req) as resp:
            pid = resp.headers.get("x-restli-id", "(unknown)")
            print(f"published: {pid}")
            return {"id": pid}
    except urllib.error.HTTPError as e:
        print(f"ERROR {e.code}: {e.read().decode('utf-8', 'ignore')}", file=sys.stderr)
        raise


def files_for(args):
    if args.file:
        p = args.file if os.path.isabs(args.file) else os.path.join(HERE, args.file)
        return [p]
    return sorted(glob.glob(os.path.join(HERE, "[0-9][0-9]_*.md")))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Publish the blog series to LinkedIn")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", help="single post filename (in this folder)")
    g.add_argument("--all", action="store_true", help="all posts, in order")
    ap.add_argument("--dry-run", action="store_true", help="preview only, no network")
    ap.add_argument("--no-image", action="store_true",
                    help="publish text only, do not attach the post's figure")
    args = ap.parse_args(argv)

    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    author = os.environ.get("LINKEDIN_AUTHOR_URN")
    if not args.dry_run and not (token and author):
        print("error: set LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN "
              "(or use --dry-run)", file=sys.stderr)
        sys.exit(2)

    for path in files_for(args):
        meta, body = parse_post(path)
        text = build_text(meta, body)
        title = meta.get("title", os.path.basename(path))
        print(f"### {title}  [{os.path.basename(path)}]")
        image_path = None
        if not args.no_image and meta.get("image"):
            cand = os.path.join(HERE, meta["image"])
            if os.path.exists(cand):
                image_path = cand
        caption = ""
        m = re.search(r"^\*Figure \d[^\n]*\*", body, re.M)
        if m:
            caption = m.group(0).strip("*").strip()
        publish(text, token, author, dry_run=args.dry_run,
                image_path=image_path, image_caption=caption)


if __name__ == "__main__":
    main()
