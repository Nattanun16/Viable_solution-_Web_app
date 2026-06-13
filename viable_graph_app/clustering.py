"""
clustering.py — จัดกลุ่มวิธีแก้ปัญหาที่มีความหมายคล้ายกันเข้าด้วยกัน

ใช้ Gemini API (gemini-2.0-flash) แทน sentence-transformers
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
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


def cluster_comments(comments: list) -> list[dict]:
    if not comments:
        return []
    if len(comments) == 1:
        return [_make_group_dict([comments[0]])]
    if not GEMINI_API_KEY:
        print("[clustering] GEMINI_API_KEY not set -- skipping clustering")
        return [_make_group_dict([c]) for c in comments]

    # ── retry สูงสุด 3 ครั้ง ถ้าเจอ 429 ──
    for attempt in range(3):
        try:
            groups_raw = _call_gemini(comments)
            print(f"[clustering] Gemini returned groups: {groups_raw}")  # DEBUG
            return _build_result(comments, groups_raw)
        except Exception as e:
            if "429" in str(e):
                wait = 5 * (attempt + 1)
                print(f"[clustering] 429 rate limit -- waiting {wait}s (attempt {attempt+1}/3)")
                time.sleep(wait)
            else:
                print(f"[clustering] Gemini error: {e} -- falling back to no-grouping")
                break

    return [_make_group_dict([c]) for c in comments]


def _call_gemini(comments: list) -> list[list[int]]:
    """
    ส่ง comment ทั้งหมดไปให้ Gemini จัดกลุ่ม
    คืนค่า list ของกลุ่ม เช่น [[0, 2], [1], [3, 4]]
    """
    numbered = "\n".join(
        f"{i}. {c.text}" for i, c in enumerate(comments)
    )

    prompt = f"""คุณคือผู้ช่วยจัดหมวดหมู่ความคิดเห็นภาษาไทย

ด้านล่างนี้คือรายการวิธีแก้ปัญหาที่ผู้ใช้เสนอ (แต่ละบรรทัดมีหมายเลขนำหน้า):
{numbered}

งาน: จัดกลุ่มวิธีแก้ที่มีความหมายเหมือนกันหรือคล้ายกันมากเข้าด้วยกัน
     แม้จะใช้คำต่างกัน เช่น "เพิ่มเที่ยวรถป๊อป" กับ "อยากให้รถโดยสารในมหาลัยวิ่งบ่อยขึ้น" ถือว่าเป็นกลุ่มเดียวกัน
     ถ้าวิธีแก้สองอันพูดถึงสิ่งเดียวกันหรือแก้ปัญหาเดียวกัน ให้รวมกลุ่มเสมอ แม้จะใช้ภาษาต่างกัน

กฎเหล็ก:
- ตอบด้วย JSON เท่านั้น ห้ามมีข้อความอื่น ห้ามใส่ ```json หรือ ``` ใดๆ ทั้งสิ้น
- รูปแบบ: array ของ array เท่านั้น เช่น [[0,2],[1],[3,4]]
- แต่ละ sub-array คือกลุ่มหนึ่ง ตัวเลขคือ index ของวิธีแก้
- ทุก index ต้องปรากฏใน output ครบ ไม่มีซ้ำ
- ถ้าไม่มีอันไหนคล้ายกันเลย ให้แต่ละอันเป็นกลุ่มของตัวเอง เช่น [[0],[1],[2]]"""

    resp = requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",  # บังคับให้ Gemini ตอบ JSON เสมอ
            },
        },
        timeout=30,
    )
    resp.raise_for_status()

    raw = (
        resp.json()
        ["candidates"][0]["content"]["parts"][0]["text"]
        .strip()
    )

    print(f"[clustering] Raw Gemini response: {repr(raw)}")  # DEBUG

    # ลบ markdown code block ถ้า Gemini ยังใส่มา (safety)
    if raw.startswith("```"):
        lines = raw.strip().split("\n")
        # ตัดบรรทัดแรก (```json หรือ ```) และบรรทัดสุดท้าย (```)
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        raw = "\n".join(inner).strip()

    groups_raw: list[list[int]] = json.loads(raw)
    return groups_raw


def _build_result(comments: list, groups_raw: list[list[int]]) -> list[dict]:
    """แปลง [[0,2],[1],[3]] -> list ของ group dict"""
    result = []
    used = set()

    for group_indices in groups_raw:
        valid = [i for i in group_indices if 0 <= i < len(comments) and i not in used]
        if not valid:
            continue
        used.update(valid)
        group_comments = [comments[i] for i in valid]
        result.append(_make_group_dict(group_comments))

    # เพิ่ม comment ที่ Gemini ไม่ได้ include มา (safety)
    for i, c in enumerate(comments):
        if i not in used:
            result.append(_make_group_dict([c]))

    # เรียงจากกลุ่มใหญ่ไปเล็ก
    result.sort(key=lambda g: g["count"], reverse=True)
    return result


def _make_group_dict(group: list) -> dict:
    """สร้าง dict สรุปข้อมูลของกลุ่มหนึ่ง"""
    representative = group[0].text
    total_rating = sum(c.rating for c in group)
    short_label = (representative[:20] + "...") if len(representative) > 20 else representative

    return {
        "representative": representative,
        "short_label": short_label,
        "count": len(group),
        "members": [c.text for c in group],
        "total_rating": total_rating,
        "bar_value": len(group),  # แก้: ใช้จำนวน comment ในกลุ่มเสมอ (ไม่ใช้ rating)
    }