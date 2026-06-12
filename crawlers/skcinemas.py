"""新光影城 (SK Cinemas) 爬蟲"""
import requests
import json
import re
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

BASE_URL = "https://www.skcinemas.com"
API_BASE = "https://api.skcinemas.com"

DEFAULT_POSTER = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=900"

CINEMAS = {
    "1001": "新光影城台北獅子林",
    "1002": "新光影城台北天母",
    "1003": "新光影城台中中港",
    "1004": "新光影城桃園青埔",
    "1005": "新光影城台南西門",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
    "Referer": "https://www.skcinemas.com/",
}

API_HEADERS = {
    **HEADERS,
    "Accept": "application/json",
}


def try_api_sessions(cinema_id, date_str):
    """嘗試 API 端點取得場次"""
    endpoints = [
        f"{API_BASE}/api/v1/sessions?cinemaId={cinema_id}&date={date_str}",
        f"{API_BASE}/v1/sessions?cinemaId={cinema_id}&date={date_str}",
        f"{BASE_URL}/api/sessions?c={cinema_id}&date={date_str}",
        f"{BASE_URL}/Home/GetSessions?cinemaId={cinema_id}&date={date_str}",
        f"{API_BASE}/sessions?cinemaId={cinema_id}&scheduleDate={date_str}",
    ]
    for url in endpoints:
        try:
            r = requests.get(url, headers=API_HEADERS, timeout=12)
            if r.status_code == 200 and (r.text.strip().startswith("[") or r.text.strip().startswith("{")):
                return r.json()
        except Exception:
            pass
    return None


def parse_html_sessions(cinema_id, cinema_name, date_str):
    """HTML 解析新光影城場次頁面"""
    rows = []
    url = f"{BASE_URL}/sessions"
    try:
        r = requests.get(url, params={"c": cinema_id, "date": date_str},
                         headers=HEADERS, timeout=15)
        if r.status_code != 200:
            # try without date param
            r = requests.get(url, params={"c": cinema_id},
                             headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return rows

        soup = BeautifulSoup(r.text, "html.parser")

        # 找電影區塊
        movie_blocks = (
            soup.select(".movie-item, .film-item, [class*='movie'], [class*='film']") or
            soup.select("article, .panel, .card")
        )

        for block in movie_blocks:
            # 電影標題
            title_el = block.select_one("h2, h3, h4, .title, .movie-title, .film-title, strong")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 2:
                continue

            # 海報
            poster = DEFAULT_POSTER
            img_el = block.select_one("img")
            if img_el:
                src = img_el.get("src", "") or img_el.get("data-src", "")
                if src:
                    poster = src if src.startswith("http") else BASE_URL + src

            # 場次時間
            time_links = block.select("a[href*='session'], a[href*='ticket'], a[href*='buy']")
            if not time_links:
                time_links = block.select("a.time, .showtime-item a, .session a, time")

            for tlink in time_links:
                time_text = tlink.get_text(strip=True)
                if not re.match(r"\d{1,2}:\d{2}", time_text):
                    continue
                href = tlink.get("href", "")
                booking_url = (href if href.startswith("http") else BASE_URL + href) if href else f"{BASE_URL}/sessions?c={cinema_id}"
                rows.append({
                    "source": "新光",
                    "cinema": cinema_name,
                    "movie": title,
                    "poster": poster,
                    "datetime": f"{date_str.replace('-', '/')} {time_text}",
                    "format": "數位",
                    "booking_url": booking_url,
                })

        # 若沒找到用另一種結構
        if not rows:
            # 找所有時間連結
            for time_el in soup.select("a[href*='session'], .time-btn, [class*='session'] a"):
                time_text = time_el.get_text(strip=True)
                if not re.match(r"\d{1,2}:\d{2}", time_text):
                    continue
                # 找最近的電影標題
                parent = time_el.find_parent(class_=re.compile(r"movie|film|panel|card|item"))
                if not parent:
                    continue
                title_el = parent.select_one("h2, h3, h4, strong, .title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = time_el.get("href", "")
                booking_url = (href if href.startswith("http") else BASE_URL + href) if href else f"{BASE_URL}/sessions?c={cinema_id}"
                rows.append({
                    "source": "新光",
                    "cinema": cinema_name,
                    "movie": title,
                    "poster": DEFAULT_POSTER,
                    "datetime": f"{date_str.replace('-', '/')} {time_text}",
                    "format": "數位",
                    "booking_url": booking_url,
                })

    except Exception as e:
        print(f"  [新光HTML] {cinema_name} {date_str} 錯誤: {e}")
    return rows


def parse_api_response(data, cinema_name, cinema_id, date_str):
    """解析 API 回傳的場次資料"""
    rows = []
    if isinstance(data, dict):
        items = data.get("sessions") or data.get("data") or data.get("results") or []
    elif isinstance(data, list):
        items = data
    else:
        return rows

    for s in items:
        title = (s.get("filmName") or s.get("film_name") or s.get("movieName") or
                 s.get("movie_name") or s.get("title") or s.get("name") or "")
        show_time = (s.get("showTime") or s.get("show_time") or s.get("startTime") or
                     s.get("start_time") or s.get("time") or "")
        if show_time:
            show_time = re.sub(r"[T ].*$", lambda m: " " + m.group()[-5:], show_time)
            show_time = re.search(r"\d{1,2}:\d{2}", show_time)
            show_time = show_time.group() if show_time else ""

        poster = (s.get("poster") or s.get("posterUrl") or s.get("poster_url") or
                  s.get("filmPoster") or DEFAULT_POSTER)
        fmt = s.get("version") or s.get("format") or s.get("filmVersion") or "數位"
        session_id = s.get("id") or s.get("sessionId") or s.get("session_id") or ""
        booking_url = (f"{BASE_URL}/ticketing/{session_id}" if session_id
                       else f"{BASE_URL}/sessions?c={cinema_id}")

        if not title or not show_time:
            continue
        rows.append({
            "source": "新光",
            "cinema": cinema_name,
            "movie": title,
            "poster": poster,
            "datetime": f"{date_str.replace('-', '/')} {show_time}",
            "format": fmt,
            "booking_url": booking_url,
        })
    return rows


def crawl(days=14):
    """主爬蟲：抓取未來N天新光場次"""
    print("[新光] 開始爬取...")
    all_rows = []

    today = datetime.today()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]

    for cinema_id, cinema_name in CINEMAS.items():
        print(f"  影城: {cinema_name}")
        for date_str in dates:
            # 先嘗試 API
            api_data = try_api_sessions(cinema_id, date_str)
            if api_data:
                rows = parse_api_response(api_data, cinema_name, cinema_id, date_str)
                all_rows.extend(rows)
            else:
                # fallback: HTML
                rows = parse_html_sessions(cinema_id, cinema_name, date_str)
                all_rows.extend(rows)
            time.sleep(0.4)
        time.sleep(0.5)

    print(f"[新光] 共取得 {len(all_rows)} 筆")
    return all_rows


if __name__ == "__main__":
    rows = crawl(days=3)
    print(json.dumps(rows[:3], ensure_ascii=False, indent=2))
