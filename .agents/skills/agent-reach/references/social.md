
# Social Media & Communities

XiaoHongShu, Twitter/X, Bilibili, V2EX, Reddit, Facebook, Instagram.

## XiaoHongShu / Xiaohongshu (multiple backends)

XiaoHongShu has three backends. **First run `agent-reach doctor --json` to see which `active_backend` is configured for `xiaohongshu`**, then use the matching command group.

### Backend A: OpenCLI (preferred on desktop; reuses the browser's logged-in session)

```bash
# Search for notes
opencli xiaohongshu search "query" -f yaml

# Read a note's body + engagement data (use the full URL from search results, including xsec_token)
opencli xiaohongshu note "NOTE_URL" -f yaml

# Comments (supports nested replies)
opencli xiaohongshu comments NOTE_ID -f yaml

# Home feed recommendations
opencli xiaohongshu feed -f yaml

# A user's public notes
opencli xiaohongshu user USER_ID -f yaml
```

> Requires Chrome to be open with the OpenCLI extension installed. An `AUTH_REQUIRED` error means the user is not logged into XiaoHongShu in the browser — ask them to sign in once in Chrome.

### Backend B: xiaohongshu-mcp (server scenarios)

```bash
# When not logged in: check status first, then fetch the QR code for the user to scan
mcporter call 'xiaohongshu.check_login_status()' --timeout 120000
mcporter call 'xiaohongshu.get_login_qrcode()' --timeout 120000

# Search
mcporter call 'xiaohongshu.search_feeds(keyword: "query")' --timeout 120000

# Note details + comments (take feed_id and xsec_token from search results)
mcporter call 'xiaohongshu.get_feed_detail(feed_id: "...", xsec_token: "...")' --timeout 120000
```

> The first call automatically downloads ~150 MB of headless browser assets; always pass `--timeout 120000`. Search will hang when not logged in — call `check_login_status` first.

### Backend C: xhs-cli (legacy fallback; upstream maintenance halted in 2026-03)

```bash
xhs search "query"          # Search
xhs read NOTE_ID_OR_URL     # Read a note (must use the URL/ID from search results, not a bare note_id)
xhs comments NOTE_ID_OR_URL # Comments
xhs hot                     # Trending
xhs feed                    # Recommendations
```

> Known to be unstable: `xhs user` / `xhs user-posts` / `xhs favorites` may return API errors (upstream maintenance halted, no one to fix). New users should go straight to backends A/B.

### General Notes

> **xsec_token requirement**: XiaoHongShu enforces the xsec_token mechanism, so **you cannot read a note using only a bare note_id**. Correct flow: first search/feed to get results, then use the full URL/ID from those results to read. This applies to all three backends.
>
> **Rate limiting**: High-frequency requests (batch searching, deep comment scraping) will trigger captchas — a platform limit that cannot be bypassed. Wait 2–3 seconds between operations.
>
> **Write operations (post/comment/like)**: Read-only is recommended. Write operations in xhs-cli v0.6.x may return 406 due to signature issues.

## Twitter/X (twitter-cli)

### Stable Commands

```bash
# Home timeline (most stable)
twitter feed -n 20

# Read a single tweet (including replies)
twitter tweet URL_OR_ID

# Read a long-form post / X Article
twitter article URL_OR_ID

# A user's timeline
twitter user-posts @username -n 20

# User profile
twitter user @username
```

### Commands That May Be Unstable

```bash
# Tweet search (Twitter frequently changes GraphQL endpoints; may return 404)
twitter search "query" -n 10

# likes (after 2024 you can only see your own — platform restriction)
twitter likes
```

### Retry Chain When `search` Fails (run in order, stop on success)

1. Retry directly once (sporadic failures are common): `twitter search "query" -n 10`
2. Upgrade and retry: `pipx upgrade twitter-cli && twitter search "query" -n 10`
3. Switch to OpenCLI fallback (desktop, reuses the browser session): `opencli twitter search "query" -f yaml`
4. If none work, detour via stable commands like `twitter feed` / `twitter user-posts @somebody`

### Important Notes

> **Install**: `pipx install twitter-cli` (ensure v0.8.5+)
>
> **Authentication**: Recommended approach is to export cookies via Cookie-Editor and set the env vars `TWITTER_AUTH_TOKEN` + `TWITTER_CT0`. Automatic extraction is not available over SSH/Docker/headless environments.
>
> **IP risk**: Do not call frequently from VPS / datacenter IPs, especially for followers/following — there is a real risk of account suspension. Use residential proxies or run locally.
>
> **OpenCLI fallback**: If OpenCLI is installed on desktop, the full set `opencli twitter search/article/user-posts -f yaml` is available (browser session, no cookie env vars needed).
>
> **Output format**: Prefer `--yaml` or `--json` for structured output — more friendly for AI agents.

## Bilibili

> ⚠️ **Do not use yt-dlp to read Bilibili** — risk-control has fully blocked it with 412 responses; no workaround in practice. Use bili-cli / OpenCLI.

```bash
# Search / Trending / Video details (bili-cli, read-only, no login required)
bili search "query" --type video -n 5
bili hot -n 10
bili video BVxxx

# Subtitles (OpenCLI, requires desktop Chrome)
opencli bilibili subtitle BVxxx
```

> For more commands (audio transcription, direct API fallback) see references/video.md.

## V2EX (public API)

No authentication required — call the public API directly.

### Hot Topics

```bash
curl -s "https://www.v2ex.com/api/topics/hot.json" -H "User-Agent: agent-reach/1.0"
```

### Node Topics

```bash
# node_name examples: python, tech, jobs, qna, programmers
curl -s "https://www.v2ex.com/api/topics/show.json?node_name=python&page=1" -H "User-Agent: agent-reach/1.0"
```

### Topic Details

```bash
# topic_id comes from the URL, e.g. https://www.v2ex.com/t/1234567
curl -s "https://www.v2ex.com/api/topics/show.json?id=TOPIC_ID" -H "User-Agent: agent-reach/1.0"
```

### Topic Replies

```bash
curl -s "https://www.v2ex.com/api/replies/show.json?topic_id=TOPIC_ID&page=1" -H "User-Agent: agent-reach/1.0"
```

### User Info

```bash
curl -s "https://www.v2ex.com/api/members/show.json?username=USERNAME" -H "User-Agent: agent-reach/1.0"
```

### Python Usage Example

```python
from agent_reach.channels.v2ex import V2EXChannel

ch = V2EXChannel()

# Get hot topics
topics = ch.get_hot_topics(limit=10)
for t in topics:
    print(f"[{t['node_title']}] {t['title']} ({t['replies']} replies)")

# Get topics for a node
node_topics = ch.get_node_topics("python", limit=5)

# Get topic details + replies
topic = ch.get_topic(1234567)
print(topic["title"], "—", topic["author"])

# Get user info
user = ch.get_user("Livid")
```

> **Node list**: <https://www.v2ex.com/planes>

## Reddit (multiple backends; login session required)

**Reddit has no zero-config path**: the anonymous `.json` endpoints have been blocked (403), and since 2025-11 Reddit's official API review process is essentially closed to new applicants. Both backends rely on a logged-in session — first run `agent-reach doctor --json` to see Reddit's `active_backend`. A proxy is required to access from mainland China.

### Backend A: OpenCLI (preferred on desktop; reuses the browser's logged-in session)

```bash
# Search posts
opencli reddit search "query" -f yaml

# Read post body + comments
opencli reddit read POST_ID -f yaml

# Browse subreddit / hot / popular
opencli reddit subreddit LocalLLaMA -f yaml
opencli reddit hot -f yaml
opencli reddit popular -f yaml

# Subreddit metadata (subscriber count, description)
opencli reddit subreddit-info LocalLLaMA -f yaml
```

> Requires Chrome to be open with the user logged into reddit.com.

### Backend B: rdt-cli (legacy / server fallback; upstream maintenance halted in 2026-03)

```bash
rdt search "query" --limit 10   # Search posts
rdt read POST_ID                # Read post body + comments
rdt sub python --limit 20       # Browse a subreddit
rdt popular --limit 10          # Browse hot posts
rdt all --limit 10              # Browse /r/all
```

> **Install**: `pipx install 'git+https://github.com/public-clis/rdt-cli.git'` (the PyPI release is outdated; install v0.4.2+ from GitHub). Run `rdt login` before search/read (in headless server environments, write cookies manually — see `doctor` hints).
> Prefer `--yaml` output — more friendly for AI agents.

### Advanced Option: Official API + PRAW (only for users who already have credentials)

Users who registered a Reddit script app before 2025-11 (and still hold client_id/client_secret) can use PRAW against the official API (100 QPM free). New applications require manual approval and are essentially rejected for personal projects — **do not recommend this path to new users**.

## Facebook (OpenCLI; login session required)

Facebook uses OpenCLI, reusing the facebook.com session in the user's Chrome. First run `agent-reach doctor --json` to see Facebook's `active_backend`; it should normally be `OpenCLI`. Do not recommend Jina/Exa/Graph API as the default path.

```bash
# Search users / pages / posts
opencli facebook search "query" -f yaml

# User or page info
opencli facebook profile zuck -f yaml

# Current account's News Feed
opencli facebook feed --limit 10 -f yaml

# Group list / recent activity visible to the current account
opencli facebook groups --limit 20 -f yaml
```

> Requires Chrome to be open with the OpenCLI extension installed and the user logged into facebook.com. Facebook Groups currently only supports reading the group list and recent activity visible to the current account — arbitrary group posts and comments are not part of the API guarantee.

## Instagram (OpenCLI; login session required)

Instagram uses OpenCLI, reusing the instagram.com session in the user's Chrome. First run `agent-reach doctor --json` to see Instagram's `active_backend`; it should normally be `OpenCLI`. Do not default to reviving instaloader — it has historically been unstable with cookies / 401 / 429.

```bash
# Search users (not site-wide post keyword search)
opencli instagram search "query" -f yaml

# User profile
opencli instagram profile nasa -f yaml

# A user's recent posts
opencli instagram user nasa --limit 12 -f yaml

# Explore / Discover
opencli instagram explore --limit 20 -f yaml

# Current account's saved posts
opencli instagram saved --limit 20 -f yaml
```

> Requires Chrome to be open with the OpenCLI extension installed and the user logged into instagram.com. `instagram search` is user search — to read posts, first identify the username, then use `instagram user USERNAME`. If you see 429 / "login required", ask the user to log in again in Chrome and slow down the request rate.
