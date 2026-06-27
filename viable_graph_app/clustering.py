"""
clustering.py — จัดกลุ่มวิธีแก้ปัญหาที่มีความหมายคล้ายกันเข้าด้วยกัน

ใช้ Google Gemini 2.5 Flash-Lite (ฟรี 1,000 req/วัน)
"""

from __future__ import annotations
import json
import os
import requests
from typing import TYPE_CHECKING
import time

if TYPE_CHECKING:
    from viable_graph_app.models import Comment

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"


def cluster_comments(comments: list) -> list[dict]:
    if not comments:
        return []
    if len(comments) == 1:
        return [_make_group_dict([comments[0]])]
    if not GEMINI_API_KEY:
        print("[clustering] GEMINI_API_KEY not set -- skipping clustering")
        return [_make_group_dict([c]) for c in comments]

    for attempt in range(3):
        try:
            groups_raw = _call_gemini(comments)
            print(f"[clustering] Gemini returned groups: {groups_raw}")
            return _build_result(comments, groups_raw)
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait = 5 * (attempt + 1)
                print(f"[clustering] rate limit -- waiting {wait}s (attempt {attempt+1}/3)")
                time.sleep(wait)
            else:
                print(f"[clustering] Gemini error: {e} -- falling back to no-grouping")
                break

    return [_make_group_dict([c]) for c in comments]


def _call_gemini(comments: list) -> list[list[int]]:
    n = len(comments)
    numbered = "\n".join(
        f"{i}. {c.text}" for i, c in enumerate(comments)
    )
    valid_indices = list(range(n))

    prompt = (
        f"มีวิธีแก้ปัญหาทั้งหมด {n} รายการ (index 0 ถึง {n-1}):\n"
        + numbered
        + "\n\n"
        "รวมกลุ่มเฉพาะวิธีแก้ที่ใช้ **วิธีการเดียวกัน** เท่านั้น\n"
        "ตัวอย่างที่ **ควร** รวมกลุ่ม: 'เพิ่มท่อระบายน้ำ' กับ 'ต้องการท่อระบายน้ำมากกว่านี้' (วิธีเดียวกัน ต่างแค่คำ)\n"
        "ตัวอย่างที่ **ไม่ควร** รวมกลุ่ม: 'เพิ่มท่อระบายน้ำ' กับ 'ขุดลอกท่อที่อุดตัน' (คนละวิธี แม้จะเกี่ยวกับท่อเหมือนกัน)\n"
        "ตัวอย่างที่ **ไม่ควร** รวมกลุ่ม: 'ลดการเผาขยะ' กับ 'ใช้รถสาธารณะ' (คนละเรื่องกัน)\n"
        "ถ้าไม่แน่ใจ ให้แยกกลุ่มดีกว่ารวมกลุ่มผิด\n\n"
        f"กฎ:\n"
        f"- index ที่ใช้ได้มีเฉพาะ: {valid_indices} เท่านั้น ห้ามใช้ตัวเลขอื่น\n"
        f"- output ต้องมี index ครบทุกตัวจาก 0 ถึง {n-1} ไม่มีซ้ำ ไม่มีขาด\n"
        "- ตอบด้วย JSON เท่านั้น ไม่ต้องมีคำอธิบาย รูปแบบ: {\"groups\": [[0,2],[1],[3]]}"
    )

    resp = requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 512,
                "responseMimeType": "application/json",
            },
        },
        timeout=30,
    )
    resp.raise_for_status()

    raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    print(f"[clustering] Raw Gemini response: {repr(raw)}")

    # strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    parsed = json.loads(raw)

    if isinstance(parsed, dict) and "groups" in parsed:
        return parsed["groups"]
    elif isinstance(parsed, list):
        return parsed
    else:
        raise ValueError(f"Unexpected Gemini response format: {parsed}")


def _build_result(comments: list, groups_raw: list[list[int]]) -> list[dict]:
    result = []
    used = set()

    for group_indices in groups_raw:
        valid = [i for i in group_indices if 0 <= i < len(comments) and i not in used]
        if not valid:
            continue
        used.update(valid)
        group_comments = [comments[i] for i in valid]
        result.append(_make_group_dict(group_comments))

    for i, c in enumerate(comments):
        if i not in used:
            result.append(_make_group_dict([c]))

    result.sort(key=lambda g: g["count"], reverse=True)
    return result


def _make_group_dict(group: list) -> dict:
    representative = group[0].text
    total_rating = sum(c.rating for c in group)
    short_label = (representative[:20] + "...") if len(representative) > 20 else representative

    return {
        "representative": representative,
        "short_label": short_label,
        "count": len(group),
        "members": [c.text for c in group],
        "total_rating": total_rating,
        "bar_value": len(group),
    }