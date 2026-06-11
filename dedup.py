"""
CSV 중복 제거 — 닉네임+메시지+금액 기준, 첫 등장만 남김
"""
import csv
from pathlib import Path

folder = Path(__file__).parent
csv_path = folder / "nL6QHnSIyuc_채팅전체.csv"

print(f"읽는 중: {csv_path}", flush=True)
rows = []
with open(csv_path, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        rows.append(row)

print(f"원본: {len(rows)}개", flush=True)

seen = set()
deduped = []
for row in rows:
    key = (row.get("닉네임",""), row.get("메시지",""), row.get("금액",""))
    if key not in seen:
        seen.add(key)
        deduped.append(row)

print(f"중복 제거 후: {len(deduped)}개 (제거: {len(rows)-len(deduped)}개)", flush=True)

out_path = folder / "nL6QHnSIyuc_채팅전체_dedup.csv"
with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(deduped)

print(f"저장 완료: {out_path}", flush=True)
input("\n엔터를 누르면 창이 닫힙니다.")
