
# Video / Podcast

Subtitles and transcripts for YouTube, Bilibili, and Xiaoyuzhou Podcast.

## YouTube (yt-dlp)

### Get Video Metadata

```bash
yt-dlp --dump-json "URL"
```

### Download Subtitles

```bash
# Download subtitles (without downloading the video)
yt-dlp --write-sub --write-auto-sub --sub-lang "zh-Hans,zh,en" --skip-download -o "/tmp/%(id)s" "URL"

# Then read the .vtt file
cat /tmp/VIDEO_ID.*.vtt
```

### Get Comments

```bash
# Extract comments (best-effort, completeness not guaranteed)
yt-dlp --write-comments --skip-download --write-info-json \
  --extractor-args "youtube:max_comments=20" \
  -o "/tmp/%(id)s" "URL"
# Comments live in the .info.json file's comments field
```

### Search Videos

```bash
yt-dlp --dump-json "ytsearch5:query"
```

> **Subtitle note**: Manually uploaded subtitles are reliably extracted; auto-generated subtitles may have duplicate lines between rows and need post-processing.
> **Comment note**: `--write-comments` is based on web scraping (not the YouTube Data API), so some comments may be missing.

### No-Subtitle Fallback: Whisper Audio Transcription

```bash
# Fallback when a video has no subtitles: download audio and transcribe with Whisper (a free Groq key is enough)
agent-reach transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
agent-reach transcribe ./local_audio.mp3 -o /tmp/transcript.txt
```

> `agent-reach transcribe` only accepts public http(s) URLs or local audio files. When using `ytsearch5:`, first pick the specific video URL from the yt-dlp results, then transcribe.
> Configure the key first: `agent-reach configure groq-key gsk_xxx` (free, console.groq.com)
> or `agent-reach configure openai-key sk-xxx`. Default `auto` mode: automatically fall back to OpenAI if Groq fails.

## Bilibili (bili-cli primary, OpenCLI for subtitles)

> ⚠️ **Do not use yt-dlp to read Bilibili**: Bilibili's risk control has fully blocked yt-dlp with 412 responses (verified across the latest version, direct connection / proxy / with cookies — all ineffective). Only use yt-dlp for YouTube.

### Video Details / Search / Hot / Rankings (bili-cli, read-only, no login required)

```bash
# Video details (title / uploader / duration / engagement / subtitle availability)
bili video BVxxx

# Search videos
bili search "query" --type video -n 5

# Hot videos / rankings
bili hot -n 10
bili rank -n 10

# Download audio and split it into ASR-ready WAVs (pair with `agent-reach transcribe` when no subtitles exist)
bili audio BVxxx
```

### Subtitles (OpenCLI, requires desktop Chrome)

```bash
# Subtitles line-by-line with timestamps
opencli bilibili subtitle BVxxx

# OpenCLI can also search / read video metadata (alternative)
opencli bilibili search "query" -f yaml
opencli bilibili video BVxxx -f yaml
```

### Zero-Config Fallback: Direct Search API

```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
curl -s -c /tmp/bili_ck.txt -o /dev/null -A "$UA" "https://www.bilibili.com/"
curl -s -b /tmp/bili_ck.txt -A "$UA" -e "https://www.bilibili.com/" \
  "https://api.bilibili.com/x/web-interface/search/all/v2?keyword=QUERY&page=1"
```

> **Install bili-cli**: `pipx install bilibili-cli` (upstream maintenance halted in 2026-03 but verified healthy; read-only use requires no login. `bili login` via QR code unlocks personal features like feed / favorites).

## Xiaoyuzhou Podcast

### Transcribe a Single Episode (use `--polish` to improve punctuation)

```bash
# Output a Markdown file to /tmp/. `--polish` lets Llama 3.3 70B add Chinese punctuation and reasonable paragraphing
~/.agent-reach/tools/xiaoyuzhou/transcribe.sh --polish "https://www.xiaoyuzhoufm.com/episode/EPISODE_ID"
```

> The transcription prompt already asks Whisper to output Chinese punctuation; if punctuation quality is still poor, add `--polish` to use the free Groq-hosted Llama 3.3 70B for punctuation + paragraphing (a 9-minute podcast adds ~7 seconds). Each transcription adds one more LLM call — use as needed.

### Prerequisites

1. **ffmpeg**: `brew install ffmpeg`
2. **Groq API Key** (free): <https://console.groq.com/keys>
3. **Configure the key**: `agent-reach configure groq-key YOUR_KEY`
4. **First run**: `agent-reach install --env=auto` to install tools

### Check Status

```bash
agent-reach doctor
```

> Markdown output files are saved to tmp by default.

## Selection Guide

| Scenario | Recommended Tool |
|-----|---------|
| YouTube subtitles | yt-dlp |
| Bilibili video details / search | bili-cli |
| Bilibili subtitles | opencli bilibili subtitle |
| Podcast transcription | Xiaoyuzhou transcribe.sh |
| Audio/video without subtitles | agent-reach transcribe (for Bilibili audio, run `bili audio` first) |
