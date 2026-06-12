"""
clustering.py  –  จัดกลุ่มวิธีแก้ปัญหาที่มีความหมายคล้ายกันเข้าด้วยกัน

Flow:
  1. แปลงข้อความแต่ละ comment → vector ด้วย SentenceTransformer
  2. ใช้ DBSCAN จัดกลุ่ม vector ที่อยู่ใกล้กัน (cosine similarity)
  3. comment ที่ไม่คล้ายใครเลย (outlier) จะได้ label = -1 → แสดงแยกต่างหาก

ตัวแปรสำคัญ:
  embedding_model  – ถูก set โดย apps.py::ready()  ตอน Django เริ่ม
  EPS              – ระยะห่างสูงสุดของ cosine distance ที่ถือว่า "คล้ายกัน"
                     (0 = เหมือนกันทุกประการ, 1 = ตรงข้ามกันสุดขีด)
                     ค่า 0.35 หมายถึง ถ้า cosine similarity >= 0.65 ถือว่าอยู่กลุ่มเดียวกัน
  MIN_SAMPLES      – ต้องมีอย่างน้อยกี่ comment ถึงจะเป็น "กลุ่ม"
                     ตั้งเป็น 2 เพราะต้องการให้แม้แต่คู่เดียวก็จัดกลุ่มได้
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from viable_graph_app.models import Comment

# ตัวแปรนี้จะถูก set โดย apps.py::ready()
# ถ้า import ล้มเหลว (เช่น ยังไม่ได้ติดตั้ง sentence-transformers) จะเป็น None
# และ cluster_comments() จะ fallback ไปใช้โหมดไม่จัดกลุ่มแทน
embedding_model = None

# ── ปรับค่าเหล่านี้เพื่อควบคุมความ "เข้มงวด" ของการจัดกลุ่ม ──
EPS = 0.35          # ยิ่งน้อย = ต้องคล้ายกันมากกว่า | ยิ่งมาก = รวมกลุ่มง่ายขึ้น
MIN_SAMPLES = 2     # จำนวน comment ขั้นต่ำที่จะเป็น "กลุ่ม"


def cluster_comments(comments: list["Comment"]) -> list[dict]:
    """
    รับ list ของ Comment objects แล้วคืน list ของกลุ่ม
    แต่ละกลุ่มเป็น dict รูปแบบ:
    {
        "representative": str,      # ข้อความตัวแทนกลุ่ม (comment แรกในกลุ่ม)
        "short_label":    str,      # ข้อความย่อสำหรับแกน X ของกราฟ
        "count":          int,      # จำนวน comment ในกลุ่ม
        "members":        list[str],# ข้อความทุก comment ในกลุ่ม
        "total_rating":   int,      # ผลรวม rating ในกลุ่ม
        "bar_value":      int,      # ค่าที่ใช้แสดงบนกราฟ (count ถ้าไม่มี rating)
    }
    """
    if not comments:
        return []

    # ── Fallback: ถ้าโมเดลยังไม่ถูกโหลด ให้แสดงแบบไม่จัดกลุ่ม ──
    if embedding_model is None:
        return _no_cluster_fallback(comments)

    # ── ถ้ามีแค่ 1 comment ไม่ต้องจัดกลุ่ม ──
    if len(comments) == 1:
        return _no_cluster_fallback(comments)

    try:
        import numpy as np
        from sklearn.cluster import DBSCAN

        texts = [c.text for c in comments]

        # Step 1: แปลงข้อความเป็น vector
        embeddings = embedding_model.encode(texts, convert_to_numpy=True)

        # Normalize ให้เป็น unit vector ก่อน (จำเป็นสำหรับ cosine distance)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # ป้องกัน division by zero
        embeddings = embeddings / norms

        # Step 2: DBSCAN ด้วย cosine distance (euclidean บน normalized vector = cosine)
        db = DBSCAN(eps=EPS, min_samples=MIN_SAMPLES, metric="euclidean")
        labels = db.fit_predict(embeddings)

        # Step 3: รวม comment ตาม label
        groups: dict[int, list] = {}
        for i, label in enumerate(labels):
            key = int(label)  # -1 = outlier
            if key not in groups:
                groups[key] = []
            groups[key].append(comments[i])

        result = []

        # กลุ่มจริงๆ (label >= 0) เรียงตามขนาดกลุ่มจากมากไปน้อย
        for label in sorted(
            [k for k in groups if k >= 0],
            key=lambda k: len(groups[k]),
            reverse=True,
        ):
            group = groups[label]
            result.append(_make_group_dict(group))

        # Outliers (label = -1) แต่ละอันเป็นกลุ่มของตัวเอง
        for comment in groups.get(-1, []):
            result.append(_make_group_dict([comment]))

        return result

    except Exception as e:
        print(f"[clustering] Error during clustering: {e}")
        return _no_cluster_fallback(comments)


def _make_group_dict(group: list["Comment"]) -> dict:
    """สร้าง dict สรุปข้อมูลของกลุ่มหนึ่ง"""
    representative = group[0].text
    total_rating = sum(c.rating for c in group)
    short_label = (representative[:20] + "…") if len(representative) > 20 else representative

    return {
        "representative": representative,
        "short_label": short_label,
        "count": len(group),
        "members": [c.text for c in group],
        "total_rating": total_rating,
        # bar_value: ใช้ total_rating ถ้ามี, ไม่งั้นใช้จำนวน comment ในกลุ่ม
        "bar_value": total_rating if total_rating > 0 else len(group),
    }


def _no_cluster_fallback(comments: list["Comment"]) -> list[dict]:
    """Fallback สำหรับกรณีที่โมเดลยังไม่พร้อม — แสดงทุก comment แยกกัน"""
    return [_make_group_dict([c]) for c in comments]