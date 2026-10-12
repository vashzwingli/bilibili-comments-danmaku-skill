#!/usr/bin/env python3
"""Audit numbered Bilibili comments or timestamped danmaku for distribution signals."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


COMMENT_RE = re.compile(r"^\s*(\d{3})(?:\s*[|｜丨]\s*主楼|\s*主楼)?\s*$")
DANMAKU_RE = re.compile(r"^(\d+)\|(.+?)\s*$")
UNICODE_PIPE_DANMAKU_RE = re.compile(r"^(\d+)丨(.+?)\s*$")
LEGACY_DANMAKU_RE = re.compile(r"^\[(\d{2}):(\d{2})\]\s+(.+?)\s*$")
QUESTION_RE = re.compile(r"[?？]|能不能|会不会|有没有|为什么|为啥|怎么|多少|哪里|哪儿|啥时候|几点")
SLANG = ("草", "好家伙", "蹲", "cy", "前排", "绷", "doge", "笑死", "6")


def parse_comments(lines: list[str]) -> list[tuple[int, str]]:
    items: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = COMMENT_RE.match(line)
        if not match or (index > 0 and lines[index - 1].strip()):
            continue
        body_index = index + 1
        while body_index < len(lines) and not lines[body_index].strip():
            body_index += 1
        body = "" if body_index >= len(lines) else lines[body_index].strip()
        items.append((int(match.group(1)), body))
    return items


def parse_danmaku(lines: list[str]) -> list[tuple[int, str]]:
    items: list[tuple[int, str]] = []
    for line in lines:
        match = DANMAKU_RE.match(line)
        if match:
            items.append((int(match.group(1)), match.group(2)))
            continue
        unicode_pipe = UNICODE_PIPE_DANMAKU_RE.match(line)
        if unicode_pipe:
            items.append((int(unicode_pipe.group(1)), unicode_pipe.group(2)))
            continue
        legacy = LEGACY_DANMAKU_RE.match(line)
        if legacy:
            seconds = int(legacy.group(1)) * 60 + int(legacy.group(2))
            items.append((seconds, legacy.group(3)))
    return items


def ngrams(value: str, width: int = 2) -> set[str]:
    compact = re.sub(r"\s+|[，。！？、：；,.!?\[\]()（）《》]", "", value.lower())
    if len(compact) < width:
        return {compact} if compact else set()
    return {compact[i : i + width] for i in range(len(compact) - width + 1)}


def similarity(left: str, right: str) -> float:
    a, b = ngrams(left), ngrams(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def common_report(items: list[tuple[int, str]]) -> None:
    bodies = [body for _, body in items]
    lengths = [len(body) for body in bodies]
    print(f"items: {len(items)}")
    print(f"empty: {sum(not body for body in bodies)}")
    print(f"length <= 6: {sum(length <= 6 for length in lengths)}")
    print(f"length 7-15: {sum(7 <= length <= 15 for length in lengths)}")
    print(f"length 16-24: {sum(16 <= length <= 24 for length in lengths)}")
    print(f"length >= 25: {sum(length >= 25 for length in lengths)}")
    print(f"question-like: {sum(bool(QUESTION_RE.search(body)) for body in bodies)}")
    print(f"slang-marker hits: {sum(any(token.lower() in body.lower() for token in SLANG) for body in bodies)}")

    duplicates = [(body, count) for body, count in Counter(bodies).items() if body and count > 1]
    print("\nexact duplicates:")
    if duplicates:
        for body, count in sorted(duplicates, key=lambda item: (-item[1], item[0])):
            print(f"  x{count} {body}")
    else:
        print("  none")


def report_comments(items: list[tuple[int, str]], threshold: float) -> None:
    print("surface: comments")
    common_report(items)
    ids = [item_id for item_id, _ in items]
    print(f"unique ids: {len(set(ids))}")

    pairs: list[tuple[float, int, int, str, str]] = []
    for left in range(len(items)):
        if len(items[left][1]) < 8:
            continue
        for right in range(left + 1, len(items)):
            if len(items[right][1]) < 8 or items[left][1] == items[right][1]:
                continue
            score = similarity(items[left][1], items[right][1])
            if score >= threshold:
                pairs.append((score, items[left][0], items[right][0], items[left][1], items[right][1]))

    print("\npossible paraphrase pairs:")
    if pairs:
        for score, left_id, right_id, left_body, right_body in sorted(pairs, reverse=True)[:20]:
            print(f"  {score:.2f} #{left_id:03d} {left_body}  <->  #{right_id:03d} {right_body}")
    else:
        print("  none at current threshold")


def report_danmaku(items: list[tuple[int, str]], duration: int | None) -> None:
    print("surface: danmaku")
    common_report(items)
    seconds = [second for second, _ in items]
    decreases = sum(seconds[index] < seconds[index - 1] for index in range(1, len(seconds)))
    print(f"first timestamp: {seconds[0] // 60:02d}:{seconds[0] % 60:02d}")
    print(f"last timestamp: {seconds[-1] // 60:02d}:{seconds[-1] % 60:02d}")
    print(f"timestamp decreases: {decreases}")
    if duration is not None:
        print(f"beyond duration: {sum(second > duration for second in seconds)}")

    repeated = Counter(body for _, body in items)
    print("\nrepeat spread:")
    for body, count in sorted(repeated.items(), key=lambda item: (-item[1], item[0])):
        if count < 2:
            continue
        moments = [second for second, text in items if text == body]
        spread = max(moments) - min(moments)
        stamp_list = ", ".join(f"{second // 60:02d}:{second % 60:02d}" for second in moments)
        print(f"  x{count} spread={spread}s {body}: {stamp_list}")

    bins = Counter(second // 10 for second in seconds)
    end = duration if duration is not None else max(seconds)
    window_count = end // 10 + 1
    print("\n10-second window density (descriptive, not targets):")
    print(f"  occupied windows: {len(bins)} / {window_count}")
    print(f"  empty windows: {max(0, window_count - len(bins))}")
    for window, count in sorted(bins.items(), key=lambda item: (-item[1], item[0]))[:10]:
        print(f"  {window * 10}-{window * 10 + 9}s: {count}")
    ordered = sorted(set(seconds))
    gaps = sorted(((right - left, left, right) for left, right in zip(ordered, ordered[1:])), reverse=True)
    print("largest gaps between entries:")
    for gap, left, right in gaps[:5]:
        print(f"  {left}-{right}s: {gap}s")


def danmaku_errors(lines: list[str], items: list[tuple[int, str]],
                   duration: int | None, strict: bool) -> list[str]:
    """Validate every nonblank input line, rather than silently dropping failures."""
    errors: list[str] = []
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        match = DANMAKU_RE.fullmatch(line)
        if strict:
            if not match or line != line.strip():
                errors.append(f"line {line_number}: expected integer_seconds|content")
            elif not match.group(2).strip() or match.group(2) != match.group(2).strip() or line.split('|', 1)[1] != match.group(2):
                errors.append(f"line {line_number}: empty content or spaces beside separator/at line end")
            continue
        unicode_match = UNICODE_PIPE_DANMAKU_RE.fullmatch(line)
        legacy = LEGACY_DANMAKU_RE.fullmatch(line)
        if not (match or unicode_match or legacy):
            errors.append(f"line {line_number}: unrecognized danmaku line")
        elif legacy and int(legacy.group(2)) >= 60:
            errors.append(f"line {line_number}: seconds field must be 00-59")
        elif not (match or unicode_match or legacy).groups()[-1].strip():
            errors.append(f"line {line_number}: empty content")
    seconds = [second for second, _ in items]
    for index in range(1, len(seconds)):
        if seconds[index] < seconds[index - 1]:
            errors.append(f"entry {index + 1}: timestamp is earlier than preceding entry")
    if duration is not None:
        for index, second in enumerate(seconds, 1):
            if second > duration:
                errors.append(f"entry {index}: {second}s exceeds duration {duration}s")
    return errors


def parse_duration(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.fullmatch(r"(\d+):(\d{2})", value)
    if not match or int(match.group(2)) >= 60:
        raise argparse.ArgumentTypeError("duration must use M:SS with seconds 00-59")
    return int(match.group(1)) * 60 + int(match.group(2))


def positive_count(value: str) -> int:
    try:
        count = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected-count must be a positive integer") from error
    if count <= 0:
        raise argparse.ArgumentTypeError("expected-count must be a positive integer")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--surface", choices=("auto", "comments", "danmaku"), default="auto")
    parser.add_argument("--duration", type=parse_duration, help="video duration as M:SS for danmaku bounds")
    parser.add_argument("--expected-count", type=positive_count, help="required number of parsed items")
    parser.add_argument("--strict-format", action="store_true", help="require canonical integer_seconds|content danmaku on every nonblank line")
    parser.add_argument("--similarity", type=float, default=0.58)
    args = parser.parse_args()

    lines = args.file.read_text(encoding="utf-8-sig").splitlines()
    comments = parse_comments(lines)
    danmaku = parse_danmaku(lines)
    surface = args.surface
    if surface == "auto":
        timestamp_like = any(re.match(r"^(?:[-+]?\d+[|丨｜:]|\[\d+:)", line) for line in lines)
        surface = "danmaku" if len(danmaku) > len(comments) or (not comments and timestamp_like) else "comments"

    if surface == "comments" and args.strict_format:
        parser.error("--strict-format applies only to danmaku")
    errors: list[str] = []

    if surface == "comments":
        if not comments:
            print("No numbered comments found.")
            return 1
        report_comments(comments, args.similarity)
        items = comments
    else:
        errors = danmaku_errors(lines, danmaku, args.duration, args.strict_format)
        if not danmaku:
            print("No timestamped danmaku found.")
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        report_danmaku(danmaku, args.duration)
        items = danmaku

    if args.expected_count is not None and len(items) != args.expected_count:
        errors.append(f"expected {args.expected_count} items, parsed {len(items)}")
    for error in errors:
        print(f"ERROR: {error}")

    print("\nReminder: statistics do not prove naturalness. Check topic matrices, staged debates, theme maintenance, and noise manually.")
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
