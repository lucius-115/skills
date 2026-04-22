#!/usr/bin/env python3
"""
Video processing script: transcription + SRT subtitles + markdown notes.
Usage:
  python process.py transcribe <video_path> [--lang zh] [--model medium]
  python process.py notes <srt_path> <video_path> <output_md> [--title "xxx"] [--category "xx"]
  python process.py all <video_path> <output_dir> [--lang zh] [--model medium] [--title "xxx"] [--category "xx"] [--subcategory "xx"] [--number "99"]
"""

import sys
import os
import re
import json
import argparse
import subprocess
import uuid
import time
import base64
import requests
from pathlib import Path
from datetime import datetime

BYTEDANCE_APPID = os.environ.get("BYTEDANCE_APPID", "")
BYTEDANCE_TOKEN = os.environ.get("BYTEDANCE_TOKEN", "")
BYTEDANCE_RESOURCE_ID = "volc.seedasr.auc"
BYTEDANCE_SUBMIT_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
BYTEDANCE_QUERY_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"

# Session that bypasses system proxy (proxy causes SSL abort on some Windows setups)
_session = requests.Session()
_session.trust_env = False


def check_deps():
    missing = []
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    if result.returncode != 0:
        missing.append("ffmpeg (please install from https://ffmpeg.org/download.html)")
    try:
        import requests
    except ImportError:
        missing.append("requests")
    return missing


def seconds_to_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def seconds_to_readable(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def extract_audio(video_path: str, audio_path: str):
    """Extract mono MP3 from video for API upload (small file size, sufficient for ASR)."""
    print(f"Extracting audio → {audio_path} ...")
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path,
         "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k", audio_path],
        check=True, capture_output=True
    )
    size_mb = Path(audio_path).stat().st_size / 1024 / 1024
    print(f"Audio extracted. ({size_mb:.1f} MB)")


def _bytedance_submit(audio_path: str) -> str:
    file_ext = Path(audio_path).suffix.lstrip(".")
    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")

    task_id = str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "X-Api-App-Key": BYTEDANCE_APPID,
        "X-Api-Access-Key": BYTEDANCE_TOKEN,
        "X-Api-Resource-Id": BYTEDANCE_RESOURCE_ID,
        "X-Api-Request-Id": task_id,
        "X-Api-Sequence": "-1",
    }
    payload = {
        "user": {"uid": "video_notes"},
        "audio": {"format": file_ext, "data": audio_b64},
        "request": {
            "model_name": "bigmodel",
            "enable_punc": True,
            "enable_itn": True,
            "enable_speaker_info": True,
        },
    }
    print("Uploading audio and submitting task...")
    resp = _session.post(BYTEDANCE_SUBMIT_URL, json=payload, headers=headers, timeout=120)
    if resp.headers.get("X-Api-Status-Code") != "20000000":
        raise Exception(f"Submit failed: {resp.headers.get('X-Api-Message')} | {resp.text}")
    print(f"Task submitted. ID: {task_id}")
    return task_id


def _bytedance_query(task_id: str) -> tuple:
    headers = {
        "Content-Type": "application/json",
        "X-Api-App-Key": BYTEDANCE_APPID,
        "X-Api-Access-Key": BYTEDANCE_TOKEN,
        "X-Api-Resource-Id": BYTEDANCE_RESOURCE_ID,
        "X-Api-Request-Id": task_id,
    }
    resp = _session.post(BYTEDANCE_QUERY_URL, json={}, headers=headers, timeout=30)
    return resp.json(), resp.headers.get("X-Api-Status-Code")


def _parse_segments(api_result: dict) -> list:
    """Convert ByteDance result to Whisper-compatible segment list."""
    result_data = api_result.get("result", {})

    # Try utterances (有时间戳的分段)
    utterances = result_data.get("utterances") or result_data.get("sentences") or []
    if utterances:
        segments = []
        for u in utterances:
            start = u.get("start_time", 0) / 1000.0
            end = u.get("end_time", start + 1) / 1000.0
            text = u.get("text", "").strip()
            if text:
                segments.append({"start": start, "end": end, "text": text})
        if segments:
            return segments

    # Fallback：按句号切分，每段估算时长
    full_text = result_data.get("text", "")
    sentences = [s.strip() for s in re.split(r"[。！？\n]", full_text) if s.strip()]
    if not sentences:
        return [{"start": 0.0, "end": 1.0, "text": full_text}]

    # 估算总时长（假设每字0.3秒）
    total_chars = sum(len(s) for s in sentences)
    cursor = 0.0
    segments = []
    for s in sentences:
        duration = max(1.0, len(s) / total_chars * (total_chars * 0.3))
        segments.append({"start": cursor, "end": cursor + duration, "text": s})
        cursor += duration
    return segments


def transcribe(video_path: str, lang: str = None, model_name: str = "medium") -> dict:
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        audio_path = tmp.name

    try:
        extract_audio(video_path, audio_path)
        task_id = _bytedance_submit(audio_path)
    finally:
        Path(audio_path).unlink(missing_ok=True)

    # 轮询直到完成
    start_time = time.time()
    while True:
        result, code = _bytedance_query(task_id)
        elapsed = int(time.time() - start_time)

        if code == "20000000":
            print(f"\nTranscription complete! ({elapsed}s)")
            segments = _parse_segments(result)
            full_text = result.get("result", {}).get("text", "")
            return {"text": full_text, "segments": segments}
        elif code in ("20000001", "20000002"):
            print(f"Processing... ({elapsed}s elapsed)", flush=True)
            time.sleep(5)
        else:
            raise Exception(f"Transcription failed: code={code}, result={result}")


def write_srt(segments: list, output_path: str):
    lines = []
    for i, seg in enumerate(segments, 1):
        start = seconds_to_srt_time(seg["start"])
        end = seconds_to_srt_time(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"SRT saved: {output_path}")


def build_timestamp_notes(segments: list, interval_sec: int = 60) -> list:
    """Group segments into ~1-min chunks for timestamp notes."""
    notes = []
    chunk_text = []
    chunk_start = None
    last_boundary = 0

    for seg in segments:
        if chunk_start is None:
            chunk_start = seg["start"]
        chunk_text.append(seg["text"].strip())
        if seg["end"] - last_boundary >= interval_sec:
            notes.append({
                "time": seconds_to_readable(chunk_start),
                "text": " ".join(chunk_text)
            })
            chunk_text = []
            chunk_start = None
            last_boundary = seg["end"]

    if chunk_text:
        notes.append({
            "time": seconds_to_readable(chunk_start or 0),
            "text": " ".join(chunk_text)
        })
    return notes


def write_markdown(result: dict, video_path: str, output_path: str,
                   title: str = None, category: str = None,
                   subcategory: str = None, number: str = None):
    video_name = Path(video_path).stem
    if not title:
        title = video_name

    # Duration from last segment
    duration = "--"
    if result.get("segments"):
        last = result["segments"][-1]["end"]
        duration = seconds_to_readable(last)

    # Path structure
    note_filename = f"{number}-{title}" if number else title
    note_path_parts = ["raw"]
    if category:
        note_path_parts.append(category)
    if subcategory:
        note_path_parts.append(subcategory)
    note_path_parts.append(note_filename)
    note_path = "/".join(note_path_parts)

    # Timestamp notes (every ~60s)
    ts_notes = build_timestamp_notes(result.get("segments", []))

    # Full transcript (plain text)
    full_text = result.get("text", "").strip()

    now = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"# {title}",
        "",
        "## 视频信息",
        "",
        f"| 字段 | 值 |",
        f"| ---- | -- |",
        f"| 文件 | `{Path(video_path).name}` |",
        f"| 时长 | {duration} |",
        f"| 日期 | {now} |",
        f"| 分类 | {category or '--'} |",
        f"| 子类 | {subcategory or '--'} |",
        f"| 笔记路径 | `{note_path}` |",
        "",
        "## 内容概述",
        "",
        "> （此处由 Claude 自动生成摘要，运行 skill 后可补充）",
        "",
        "## 关键要点",
        "",
        "- ",
        "",
        "## 时间戳笔记",
        "",
    ]

    for note in ts_notes:
        lines.append(f"- **[{note['time']}]** {note['text']}")

    lines += [
        "",
        "## 完整转录",
        "",
        "```",
        full_text,
        "```",
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Markdown saved: {output_path}")


def cmd_transcribe(args):
    missing = check_deps()
    if missing:
        for m in missing:
            print(f"ERROR: missing {m}")
        sys.exit(1)
    result = transcribe(args.video)
    out_dir = Path(args.video).parent
    srt_path = str(out_dir / (Path(args.video).stem + ".srt"))
    write_srt(result["segments"], srt_path)
    json_path = str(out_dir / (Path(args.video).stem + "_transcript.json"))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Transcript JSON saved: {json_path}")


def cmd_notes(args):
    import json
    json_path = args.srt.replace(".srt", "_transcript.json")
    if not Path(json_path).exists():
        print(f"ERROR: transcript JSON not found at {json_path}. Run 'transcribe' first.")
        sys.exit(1)
    with open(json_path, encoding="utf-8") as f:
        result = json.load(f)
    write_markdown(result, args.video, args.output_md,
                   title=args.title, category=args.category,
                   subcategory=args.subcategory, number=args.number)


def cmd_all(args):
    missing = check_deps()
    if missing:
        for m in missing:
            print(f"ERROR: missing {m}")
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(args.video).stem
    srt_path = str(out_dir / f"{stem}.srt")
    md_filename = f"{args.number}-{args.title}.md" if args.number and args.title else f"{stem}.md"
    md_path = str(out_dir / md_filename)

    result = transcribe(args.video)
    write_srt(result["segments"], srt_path)

    json_path = str(out_dir / f"{stem}_transcript.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    write_markdown(result, args.video, md_path,
                   title=args.title or stem,
                   category=args.category,
                   subcategory=args.subcategory,
                   number=args.number)

    print("\n=== 完成 ===")
    print(f"  SRT 字幕: {srt_path}")
    print(f"  Markdown 笔记: {md_path}")
    print(f"  转录 JSON: {json_path}")


def main():
    parser = argparse.ArgumentParser(description="Video transcription and notes generator")
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="Check dependencies")

    p_t = sub.add_parser("transcribe", help="Transcribe video → SRT + JSON")
    p_t.add_argument("video")
    p_t.add_argument("--lang", default=None, help="Language code e.g. zh, en, ja")
    p_t.add_argument("--model", default="medium", help="Whisper model: tiny/base/small/medium/large")

    p_n = sub.add_parser("notes", help="Generate markdown notes from transcript JSON")
    p_n.add_argument("srt", help="Path to .srt file (transcript JSON must be alongside it)")
    p_n.add_argument("video", help="Original video path (for metadata)")
    p_n.add_argument("output_md", help="Output .md path")
    p_n.add_argument("--title", default=None)
    p_n.add_argument("--category", default=None)
    p_n.add_argument("--subcategory", default=None)
    p_n.add_argument("--number", default=None)

    p_a = sub.add_parser("all", help="Transcribe + SRT + markdown in one step")
    p_a.add_argument("video")
    p_a.add_argument("output_dir")
    p_a.add_argument("--lang", default=None, help="Language code e.g. zh, en, ja")
    p_a.add_argument("--model", default="medium", help="Whisper model: tiny/base/small/medium/large")
    p_a.add_argument("--title", default=None, help="Note title")
    p_a.add_argument("--category", default=None, help="e.g. '06 SEO&相关技术'")
    p_a.add_argument("--subcategory", default=None, help="e.g. '杂记'")
    p_a.add_argument("--number", default=None, help="Note number prefix e.g. '99'")

    args = parser.parse_args()

    if args.command == "check":
        missing = check_deps()
        if missing:
            print("Missing dependencies:")
            for m in missing:
                print(f"  - {m}")
        else:
            print("All dependencies OK.")
    elif args.command == "transcribe":
        cmd_transcribe(args)
    elif args.command == "notes":
        cmd_notes(args)
    elif args.command == "all":
        cmd_all(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
