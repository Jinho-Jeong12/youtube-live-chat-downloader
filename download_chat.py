"""
유튜브 라이브 채팅 다운로더
- 로그인 불필요 영상: requests로 바로 수집
- 로그인 필요 영상 (멤버십 등): Chrome 세션으로 쿠키 인증 후 수집
- 결과: 시간 / 유형 / 닉네임 / 메시지 / 금액 → CSV + Excel
"""

import sys
import subprocess

def _install(packages: list[str]):
    missing = []
    for pkg in packages:
        module = pkg.split("==")[0].replace("-", "_")
        # webdriver_manager 예외 처리
        if module == "webdriver_manager":
            module = "webdriver_manager"
        try:
            __import__(module)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[자동 설치] 필요한 패키지를 설치합니다: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        print("[자동 설치] 완료.\n")

_install(["selenium", "webdriver-manager", "requests", "openpyxl"])

import csv
import json
import re
import time
from pathlib import Path

import hashlib
import time as _time

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


CHROME_PROFILE = r"C:\Users\novaj\AppData\Local\Google\Chrome\User Data"


# ── 로그인 없이 세션 생성 (공개 영상) ────────────────────────────────────────

def make_session_without_login(video_id: str):
    """로그인 없이 YouTube 페이지에서 ytInitialData 추출"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"페이지 로드 중: {url}", flush=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    page_source = resp.text

    m = re.search(r"var ytInitialData\s*=\s*(\{.+?\});\s*(?:var |window\[|</script)", page_source, re.DOTALL)
    if not m:
        raise RuntimeError("ytInitialData를 찾지 못했습니다. 로그인이 필요한 영상일 수 있습니다.")
    initial_data = json.loads(m.group(1))

    m2 = re.search(r'"INNERTUBE_API_KEY"\s*:\s*"([^"]+)"', page_source)
    api_key = m2.group(1) if m2 else "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"

    m3 = re.search(r'"INNERTUBE_CONTEXT_CLIENT_VERSION"\s*:\s*"([^"]+)"', page_source)
    client_ver = m3.group(1) if m3 else "2.20240101.00.00"

    session.headers.update({
        "Referer": url,
        "Origin": "https://www.youtube.com",
    })
    print("페이지 로딩 완료 (로그인 없음)\n", flush=True)
    return session, initial_data, api_key, client_ver


# ── Selenium으로 인증된 세션 생성 (로그인 필요 영상) ─────────────────────────

def make_session_via_chrome(video_id: str) -> tuple[requests.Session, str]:
    """Chrome 프로필로 YouTube 페이지 열고 → 쿠키 + ytInitialData 추출"""

    print("\n" + "="*50, flush=True)
    print("잠시 후 Chrome 창이 자동으로 열립니다.", flush=True)
    print("Chrome 창에서 YouTube에 로그인한 뒤,", flush=True)
    print("이 터미널 창으로 돌아와 엔터를 눌러주세요.", flush=True)
    print("="*50, flush=True)
    while input("이해하셨으면 ok 입력: ").strip().lower() != "ok":
        print("ok를 입력해주세요.", flush=True)

    print("ChromeDriver 설치 확인 중...", flush=True)
    driver_path = ChromeDriverManager().install()
    print(f"ChromeDriver 준비 완료", flush=True)

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    print("Chrome 실행 중...", flush=True)
    driver = webdriver.Chrome(service=Service(driver_path), options=options)
    print("Chrome 실행됨", flush=True)

    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        # 먼저 유튜브 로그인 페이지로 이동
        print("YouTube 로그인 페이지를 엽니다...", flush=True)
        driver.get("https://www.youtube.com")
        print("\n" + "="*50, flush=True)
        print("Chrome 창에서 YouTube에 로그인해주세요.", flush=True)
        print("로그인 완료 후 이 터미널 창으로 돌아와 엔터를 눌러주세요.", flush=True)
        print("="*50, flush=True)
        input("로그인 완료 후 엔터: ")

        print(f"\n페이지 로드 중: {url}", flush=True)
        driver.get(url)

        print("페이지 로딩 대기 중...", flush=True)
        WebDriverWait(driver, 15).until(
            lambda d: "ytInitialData" in d.page_source
        )
        print("페이지 로딩 완료", flush=True)

        # ytInitialData 추출
        page_source = driver.page_source
        m = re.search(r"var ytInitialData\s*=\s*(\{.+?\});\s*(?:var |window\[|</script)", page_source, re.DOTALL)
        if not m:
            raise RuntimeError("ytInitialData를 찾지 못했습니다.")
        initial_data = json.loads(m.group(1))

        # 디버그: ytInitialData 저장
        debug_path = Path(__file__).parent / "_debug_initial.json"
        debug_path.write_text(json.dumps(initial_data, ensure_ascii=False, indent=2)[:100000], encoding="utf-8")
        print(f"  데이터 저장 위치: {debug_path}", flush=True)

        # API key 추출
        m2 = re.search(r'"INNERTUBE_API_KEY"\s*:\s*"([^"]+)"', page_source)
        api_key = m2.group(1) if m2 else "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"

        m3 = re.search(r'"INNERTUBE_CONTEXT_CLIENT_VERSION"\s*:\s*"([^"]+)"', page_source)
        client_ver = m3.group(1) if m3 else "2.20240101.00.00"

        # Selenium 쿠키 → requests.Session
        all_cookies = driver.get_cookies()
        sapisid = next((c["value"] for c in all_cookies if c["name"] == "SAPISID"), None)
        sapisid3 = next((c["value"] for c in all_cookies if c["name"] == "__Secure-3PAPISID"), None)
        logged_in = bool(sapisid or sapisid3)

        print(f"로그인 상태: {'✓ 로그인됨' if logged_in else '✗ 로그아웃'}", flush=True)
        if not logged_in:
            raise RuntimeError("Chrome에서 YouTube 로그인이 필요합니다.")

        # SAPISIDHASH 헤더 생성 (YouTube API 인증에 필수)
        sid = sapisid3 or sapisid
        ts = int(_time.time())
        hash_val = hashlib.sha1(f"{ts} {sid} https://www.youtube.com".encode()).hexdigest()
        auth_header = f"SAPISIDHASH {ts}_{hash_val}"
        print(f"인증 헤더 생성 완료", flush=True)

        session = requests.Session()
        session.headers.update({
            "User-Agent": driver.execute_script("return navigator.userAgent"),
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Referer": url,
            "Origin": "https://www.youtube.com",
            "Authorization": auth_header,
            "X-Origin": "https://www.youtube.com",
        })
        for cookie in all_cookies:
            session.cookies.set(cookie["name"], cookie["value"], domain=cookie.get("domain", ".youtube.com"))

        return session, initial_data, api_key, client_ver

    finally:
        driver.quit()
        print("Chrome 창 닫힘\n", flush=True)


# ── 채팅 replay API ───────────────────────────────────────────────────────────

def find_continuation_token(data: dict) -> str | None:
    # 1순위: 알려진 경로 직접 탐색
    def dig(obj, keys):
        for k in keys:
            if not isinstance(obj, dict):
                return None
            obj = obj.get(k)
            if obj is None:
                return None
        return obj

    known_paths = [
        ["contents","twoColumnWatchNextResults","conversationBar","liveChatRenderer","continuations",0,"reloadContinuationData","continuation"],
        ["contents","twoColumnWatchNextResults","conversationBar","liveChatRenderer","continuations",0,"liveChatReplayContinuationData","continuation"],
        ["contents","twoColumnWatchNextResults","conversationBar","liveChatRenderer","continuations",0,"invalidationContinuationData","continuation"],
    ]
    for path in known_paths:
        val = data
        for k in path:
            if isinstance(val, list):
                val = val[k] if k < len(val) else None
            elif isinstance(val, dict):
                val = val.get(k)
            else:
                val = None
            if val is None:
                break
        if isinstance(val, str) and len(val) > 20:
            return val

    # 2순위: 전체 JSON에서 livechat 관련 continuation 키워드 탐색
    text = json.dumps(data)
    for pattern in [
        r'"reloadContinuationData"\s*:\s*\{[^}]*"continuation"\s*:\s*"([A-Za-z0-9_\-]{30,})"',
        r'"liveChatReplayContinuationData"\s*:\s*\{[^}]*"continuation"\s*:\s*"([A-Za-z0-9_\-]{30,})"',
        r'"continuation"\s*:\s*"([A-Za-z0-9_\-]{30,})"',
    ]:
        m = re.search(pattern, text)
        if m:
            return m.group(1)
    return None


def fetch_chat_page(session: requests.Session, continuation: str, api_key: str, client_ver: str, player_offset_ms: int = 0) -> dict:
    url = f"https://www.youtube.com/youtubei/v1/live_chat/get_live_chat_replay?key={api_key}"
    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": client_ver,
                "hl": "ko",
            }
        },
        "continuation": continuation,
    }
    if player_offset_ms > 0:
        payload["currentPlayerState"] = {"playerOffsetMs": str(player_offset_ms)}
    for attempt in range(10):
        try:
            resp = session.post(url, json=payload, timeout=15)
            if resp.status_code in (503, 429, 500):
                wait = 2 ** attempt  # 1, 2, 4, 8, 16 ...
                print(f"  서버 오류({resp.status_code}) — {wait}초 후 재시도...", flush=True)
                _time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            if attempt == 9:
                raise
            _time.sleep(2)
    raise RuntimeError("최대 재시도 횟수 초과")


def get_runs_text(runs: list) -> str:
    parts = []
    for r in runs:
        if "text" in r:
            parts.append(r["text"])
        elif "emoji" in r:
            sc = r["emoji"].get("shortcuts")
            parts.append(sc[0] if sc else "")
    return "".join(parts)


def sec_to_timestamp(sec: float) -> str:
    total = int(sec)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def parse_actions(actions: list) -> list[dict]:
    results = []
    for action in actions:
        # replayChatItemAction 감싸기 처리
        inner = action.get("replayChatItemAction", {}).get("actions", [action])
        for a in inner:
            item = a.get("addChatItemAction", {}).get("item", {})
            for renderer_key, msg_type in [
                ("liveChatTextMessageRenderer",    "채팅"),
                ("liveChatPaidMessageRenderer",    "슈퍼챗"),
                ("liveChatMembershipItemRenderer", "멤버십"),
            ]:
                r = item.get(renderer_key)
                if not r:
                    continue
                offset_ms = int(
                    r.get("videoOffsetTimeMsec")
                    or r.get("timestampUsec", 0) and 0  # usec은 별도 처리
                    or 0
                )
                # replayChatItemAction에서 videoOffsetTimeMsec 가져오기
                if offset_ms == 0:
                    offset_ms = int(action.get("replayChatItemAction", {}).get("videoOffsetTimeMsec", 0) or 0)
                author = r.get("authorName", {}).get("simpleText", "")
                text   = get_runs_text(r.get("message", {}).get("runs", []))
                amount = r.get("purchaseAmountText", {}).get("simpleText", "")
                if not text and msg_type == "멤버십":
                    text = get_runs_text(r.get("headerSubtext", {}).get("runs", []))
                results.append({
                    "시간":    sec_to_timestamp(offset_ms / 1000),
                    "유형":    msg_type,
                    "닉네임":  author,
                    "메시지":  text,
                    "금액":    amount,
                    "_sec":   offset_ms / 1000,
                })
    return results


def _checkpoint_path(output_dir: Path, base_name: str) -> Path:
    return output_dir / f"{base_name}_체크포인트.json"


def _save_checkpoint(messages: list[dict], output_dir: Path, base_name: str, continuation: str | None = None):
    fields = ["시간", "유형", "닉네임", "메시지", "금액"]
    path = output_dir / f"{base_name}_채팅전체.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(messages)
    if continuation is not None:
        cp = _checkpoint_path(output_dir, base_name)
        cp.write_text(json.dumps({"continuation": continuation, "count": len(messages)}, ensure_ascii=False), encoding="utf-8")
    print(f"  [중간저장] {len(messages)}개 → {path.name}", flush=True)


def _load_existing_csv(output_dir: Path, base_name: str) -> tuple[list[dict], set] | None:
    csv_path = output_dir / f"{base_name}_채팅전체.csv"
    if not csv_path.exists():
        return None
    messages = []
    keys = set()
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            messages.append(row)
            keys.add((row["닉네임"], row["메시지"], row["금액"]))
    return messages, keys


def select_output_dir() -> Path:
    """GUI 폴더 선택 다이얼로그로 저장 위치를 선택. 실패 시 직접 입력."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(
            title="채팅 기록 저장 위치를 선택하세요",
            initialdir=Path.home() / "Desktop",
        )
        root.destroy()
        if folder:
            return Path(folder)
    except Exception as e:
        print(f"폴더 선택 창을 열지 못했습니다: {e}")

    print("저장할 폴더 경로를 직접 입력하세요 (비워두면 스크립트 폴더에 저장):")
    path_input = input("경로: ").strip()
    if path_input:
        p = Path(path_input)
        p.mkdir(parents=True, exist_ok=True)
        return p
    return Path(__file__).parent


def fetch_all_chat(session: requests.Session, initial_data: dict, api_key: str, client_ver: str, video_id: str = "chat", output_dir: Path | None = None) -> list[dict]:
    if output_dir is None:
        output_dir = Path(__file__).parent
    cp_path = _checkpoint_path(output_dir, video_id)

    existing_messages: list[dict] = []
    existing_keys: set = set()
    fast_forward = False

    # 방법 1: 체크포인트 JSON + CSV → 토큰 직접 이어받기
    if cp_path.exists():
        try:
            cp_data = json.loads(cp_path.read_text(encoding="utf-8"))
            continuation = cp_data["continuation"]
            loaded = _load_existing_csv(output_dir, video_id)
            if loaded:
                existing_messages, existing_keys = loaded
            print(f"[체크포인트 이어받기] {len(existing_messages)}개 → 저장된 토큰부터 재개", flush=True)
        except Exception as e:
            print(f"체크포인트 손상({e}), CSV 이어받기 시도...", flush=True)
            cp_path.unlink(missing_ok=True)
            continuation = None

    # 방법 2: CSV만 있음 → 마지막 메시지 내용으로 끊긴 곳 탐색
    if not cp_path.exists():
        loaded = _load_existing_csv(output_dir, video_id)
        if loaded:
            existing_messages, existing_keys = loaded
            # 마지막 50개 메시지의 (닉네임+메시지) 집합
            tail_keys = set()
            for m in existing_messages[-50:]:
                tail_keys.add((m.get("닉네임",""), m.get("메시지","")))
            print(f"[CSV 이어받기] 기존 {len(existing_messages)}개 로드 — 끊긴 곳 탐색 중...", flush=True)
            fast_forward = True
        continuation = find_continuation_token(initial_data)
        if not continuation:
            raise RuntimeError("채팅 replay 토큰을 찾지 못했습니다.")
        if not existing_messages:
            print(f"[새로 수집]", flush=True)

    print("채팅 수집 중...", flush=True)
    new_messages: list[dict] = []
    page = 0
    tail_matched = False
    seen_tokens: set[str] = set()  # 무한반복 방지

    while continuation:
        page += 1
        if continuation in seen_tokens:
            print(f"  채팅 전수 수집 완료.", flush=True)
            break
        seen_tokens.add(continuation)
        data = fetch_chat_page(session, continuation, api_key, client_ver)

        live_chat = (
            data.get("continuationContents", {}).get("liveChatContinuation")
            or data.get("contents", {}).get("liveChatContinuation")
            or {}
        )

        actions = live_chat.get("actions", [])
        parsed = parse_actions(actions)

        if fast_forward:
            # 이 페이지 마지막 메시지가 tail_keys에 있으면 아직 구간 안 → 통째로 스킵
            if parsed:
                last_msg = parsed[-1]
                if (last_msg["닉네임"], last_msg["메시지"]) in tail_keys:
                    tail_matched = True
                    if page % 100 == 0:
                        print(f"  [탐색중] {page}페이지 스킵...", flush=True)
                    # 페이지 전체 스킵
                elif tail_matched:
                    # tail_keys 구간을 막 넘어섬 → 여기서부터 수집
                    fast_forward = False
                    print(f"  끊긴 곳 발견 (페이지 {page})! 수집 재개합니다.", flush=True)
                    new_on_page = [m for m in parsed
                                   if (m["닉네임"], m["메시지"]) not in existing_keys]
                    new_messages.extend(new_on_page)
                else:
                    # tail_keys를 아직 못 봄 → 스킵 계속
                    if page % 100 == 0:
                        print(f"  [탐색중] {page}페이지...", flush=True)
        else:
            new_messages.extend(parsed)
            if page % 50 == 0:
                total = len(existing_messages) + len(new_messages)
                print(f"  {total}개 수집 중...", flush=True)

        continuation = None
        for c in live_chat.get("continuations", []):
            for key in c:
                token = c[key].get("continuation")
                if token:
                    continuation = token
                    break
            if continuation:
                break

        # 500페이지마다 체크포인트 저장 (탐색 완료 후에만)
        if not fast_forward and page % 500 == 0:
            all_so_far = existing_messages + new_messages
            _save_checkpoint(all_so_far, output_dir, video_id, continuation)

    # 완료 시 체크포인트 삭제
    if cp_path.exists():
        cp_path.unlink()

    all_messages = existing_messages + new_messages
    print(f"총 {len(all_messages)}개 (기존 {len(existing_messages)}개 + 새로 {len(new_messages)}개)", flush=True)
    return all_messages


# ── 저장 ─────────────────────────────────────────────────────────────────────

def save_results(messages: list[dict], output_dir: Path, base_name: str):
    fields = ["시간", "유형", "닉네임", "메시지", "금액"]

    csv_path = output_dir / f"{base_name}_채팅전체.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(messages)
    print(f"[CSV]   {csv_path}")

    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "전체 채팅"
        ws.append(fields)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1565C0")
            cell.alignment = Alignment(horizontal="center")

        type_colors = {"슈퍼챗": "FFCDD2", "멤버십": "C8E6C9", "채팅": "FFFFFF"}
        for m in messages:
            ws.append([m["시간"], m["유형"], m["닉네임"], m["메시지"], m["금액"]])
            color = type_colors.get(m["유형"], "FFFFFF")
            for cell in ws[ws.max_row]:
                cell.fill = PatternFill("solid", fgColor=color)

        ws.column_dimensions["A"].width = 10
        ws.column_dimensions["B"].width = 10
        ws.column_dimensions["C"].width = 22
        ws.column_dimensions["D"].width = 60
        ws.column_dimensions["E"].width = 14

        xlsx_path = output_dir / f"{base_name}_채팅.xlsx"
        wb.save(xlsx_path)
        print(f"[Excel] {xlsx_path}")
    except Exception as e:
        print(f"Excel 저장 실패: {e}")


# ── 실행 ─────────────────────────────────────────────────────────────────────

def extract_video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_\-]{11})", url)
    return m.group(1) if m else url.strip()


def main():
    print("=== 유튜브 라이브 채팅 다운로더 ===\n")

    url = (sys.argv[1] if len(sys.argv) >= 2
           else input("유튜브 영상 URL 붙여넣기: ").strip())
    if not url:
        input("URL 없음. 엔터로 종료.")
        sys.exit(0)

    video_id = extract_video_id(url)

    print("\n채팅 기록을 저장할 폴더를 선택해주세요.")
    output_dir = select_output_dir()
    print(f"저장 위치: {output_dir}\n")

    ans = input("구글 로그인이 있어야 접근 가능한 영상인가요? (멤버십 등) [y/n]: ").strip().lower()
    need_login = ans == "y"

    try:
        if need_login:
            session, initial_data, api_key, client_ver = make_session_via_chrome(video_id)
        else:
            session, initial_data, api_key, client_ver = make_session_without_login(video_id)
        messages = fetch_all_chat(session, initial_data, api_key, client_ver, video_id, output_dir)
    except Exception as e:
        print(f"\n[오류] {e}")
        input("\n엔터를 누르면 창이 닫힙니다.")
        sys.exit(1)

    save_results(messages, output_dir, video_id)
    print(f"\n완료! 결과 파일이 저장되었습니다.\n저장 위치: {output_dir}")
    input("\n엔터를 누르면 창이 닫힙니다.")


if __name__ == "__main__":
    main()
