"""
clustering.py — จัดกลุ่มวิธีแก้ปัญหาที่มีความหมายคล้ายกันเข้าด้วยกัน

ใช้ Groq API (llama-3.3-70b-versatile)
"""

from __future__ import annotations
import json
import os
import requests
from typing import TYPE_CHECKING
import time

if TYPE_CHECKING:
    from viable_graph_app.models import Comment

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def cluster_comments(comments: list) -> list[dict]:
    if not comments:
        return []
    if len(comments) == 1:
        return [_make_group_dict([comments[0]])]
    if not GROQ_API_KEY:
        print("[clustering] GROQ_API_KEY not set -- skipping clustering")
        return [_make_group_dict([c]) for c in comments]

    for attempt in range(3):
        try:
            groups_raw = _call_groq(comments)
            print(f"[clustering] Groq returned groups: {groups_raw}")
            return _build_result(comments, groups_raw)
        except Exception as e:
            if "429" in str(e):
                wait = 5 * (attempt + 1)
                print(f"[clustering] 429 rate limit -- waiting {wait}s (attempt {attempt+1}/3)")
                time.sleep(wait)
            else:
                print(f"[clustering] Groq error: {e} -- falling back to no-grouping")
                break

    return [_make_group_dict([c]) for c in comments]


def _call_groq(comments: list) -> list[list[int]]:
    numbered = "\n".join(
        f"{i}. {c.text}" for i, c in enumerate(comments)
    )

    # ใช้ .format() แทน f-string เพื่อหลีกเลี่ยง {} ใน prompt ชน f-string
    prompt = (
        "คุณคือผู้ช่วยจัดหมวดหมู่ความคิดเห็นภาษาไทย\n\n"
        "ด้านล่างนี้คือรายการวิธีแก้ปัญหาที่ผู้ใช้เสนอ (แต่ละบรรทัดมีหมายเลขนำหน้า):\n"
        + numbered +
        "\n\nงาน: จัดกลุ่มวิธีแก้ที่มีความหมายเหมือนกันหรือคล้ายกันมากเข้าด้วยกัน\n"
        "     แม้จะใช้คำต่างกัน เช่น 'เพิ่มเที่ยวรถป๊อป' กับ 'อยากให้รถโดยสารในมหาลัยวิ่งบ่อยขึ้น' ถือว่าเป็นกลุ่มเดียวกัน\n"
        "     ถ้าวิธีแก้สองอันพูดถึงสิ่งเดียวกันหรือแก้ปัญหาเดียวกัน ให้รวมกลุ่มเสมอ แม้จะใช้ภาษาต่างกัน\n\n"
        "กฎเหล็ก:\n"
        "- ตอบด้วย JSON object ที่มี key ชื่อ 'groups' เท่านั้น\n"
        "- รูปแบบ: {\"groups\": [[0,2],[1],[3,4]]}\n"
        "- แต่ละ sub-array คือกลุ่มหนึ่ง ตัวเลขคือ index ของวิธีแก้\n"
        "- ทุก index ต้องปรากฏใน output ครบ ไม่มีซ้ำ\n"
        "- ถ้าไม่มีอันไหนคล้ายกันเลย ให้แต่ละอันเป็นกลุ่มของตัวเอง"
    )

    resp = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        },
        timeout=30,
    )
    resp.raise_for_status()

    raw = resp.json()["choices"][0]["message"]["content"].strip()
    print(f"[clustering] Raw Groq response: {repr(raw)}")

    parsed = json.loads(raw)

    # Groq json_object mode จะ wrap ใน dict เสมอ เช่น {"groups": [[0,1]]}
    if isinstance(parsed, dict):
        for v in parsed.values():
            if isinstance(v, list):
                parsed = v
                break

    groups_raw: list[list[int]] = parsed
    return groups_raw


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