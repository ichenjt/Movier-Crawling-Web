"""國賓影城 (Ambassador) 爬蟲"""
import requests
import json
import re
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

BASE_URL = "https://www.ambassador.com.tw"
DEFAULT_POSTER = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=900"

# 國賓影城列表 (ID 為網站用 GUID)
CINEMAS = {
    "84b87b82-b936-4a39-b91f-e88328d33b4e": "國賓大戲院",
    # 若有其他分館，格式相同
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
    "Referer": "https://www.ambassador.com.tw/",
}

API_HEADERS = {**HEADERS, "Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}


def get_cinemas_list():
    """嘗試動態取得國賓影城列表"""
    urls = [
        f"{BASE_URL}/api/cinemas",
        f"{BASE_URL}/home/GetCinemas",
        f"{BASE_URL}/home/CinemaList",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=API_HEADERS, timeout=12)
            if r.status_code == 200 and r.text.strip().startswith("["):
                data = r.json()
                result = {}
                for c in data:
                    cid = c.get("ID") or c.get("id") or c.get("CinemaID") or ""
                    name = c.get("Name") or c.get("name") or c.get("CinemaName") or ""
                    if cid and name:
                        result[str(cid)] = name
                if result:
                    return result
        except Exception:
            pass
    return CINEMAS


def get_showtimes_api(cinema_id, date_str):
    """嘗試 API 抓場次"""
    api_urls = [
        f"{BASE_URL}/api/showtimes?cinemaId={cinema_id}&date={date_str}",
        f"{BASE_URL}/home/GetShowtime?ID={cinema_id}&DT={date_str}",
        f"{BASE_URL}/home/Showtime?ID={cinema_id}&DT={date_str}",
        f"{BASE_URL}/api/sessions?cinemaId={cinema_id}&date={date_str}",
    ]
    for url in api_urls:
        try:
            r = requests.get(url, headers=API_HEADERS, timeout=12)
            if r.status_code == 200 and r.text.strip().startswith(("[", "{")):
                return r.json(), url
        except Exception:
            pass
    return None, None


def parse_showtime_html(cinema_id, cinema_name, date_str):
    """HTML 解析國賓場次頁面"""
    rows = []
    # 嘗試日期格式 YYYY/MM/DD (國賓網站格式)
    date_slash = date_str.replace("-", "/")
    urls_to_try = [
        f"{BASE_URL}/home/Showtime?ID={cinema_id}&DT={date_slash}",
        f"{BASE_URL}/home/Showtime?ID={cinema_id}&DT={date_str}",
        f"{BASE_URL}/home/ShowTime?cinemaId={cinema_id}&date={date_str}",
    ]

    html_text = None
    for url in urls_to_try:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200 and len(r.text) > 500:
                html_text = r.text
                break
        except Exception as e:
            print(f"  [國賓] {url} 錯誤: {e}")

    if not html_text:
        return rows

    soup = BeautifulSoup(html_text, "html.parser")

    # 解析電影區塊
    movie_blocks = soup.select(".movie-block, .film-area, [class*='movie'], [class*='film'], .schedule-item")
    if not movie_blocks:
        movie_blocks = soup.select("article, .panel, li[class*='film'], div[data-film]")

    for block in movie_blocks:
        title_el = block.select_one("h2, h3, h4, .title, [class*='title'], strong")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title or len(title) < 2:
            continue

        poster = DEFAULT_POSTER
        img_el = block.select_one("img")
        if img_el:
            src = img_el.get("src", "") or img_el.get("data-src", "")
            if src and not src.endswith(".gif") and not src.endswith(".png"):
                poster = src if src.startswith("http") else BASE_URL + src

        # 場次時間與格式
        format_el = block.select_one(".format, .version, [class*='format'], [class*='version']")
        fmt = format_el.get_text(strip=True) if format_el else "數位"

        time_links = block.select("a[href*='ticket'], a[href*='buy'], a[href*='order'], .time-btn, .showtime")
        if not time_links:
            time_links = block.select("a")

        for tlink in time_links:
            time_text = tlink.get_text(strip=True)
            if not re.match(r"\d{1,2}:\d{2}", time_text):
                continue
            href = tlink.get("href", "")
            booking_url = (href if href.startswith("http") else BASE_URL + href) if href else f"{BASE_URL}/home/Ticket"
            rows.append({
                "source": "國賓",
                "cinema": cinema_name,
                "movie": title,
                "poster": poster,
                "datetime": f"{date_slash} {time_text}",
                "format": fmt,
                "booking_url": booking_url,
            })

    # 如果上面方法沒找到，嘗試通用時間解析
    if not rows:
        # 找所有含時間的連結
        for a in soup.select("a"):
            text = a.get_text(strip=True)
            if not re.match(r"\d{1,2}:\d{2}", text):
                continue
            # 找父元素找電影名稱
            parent = a
            title = ""
            for _ in range(6):
                parent = parent.find_parent()
                if not parent:
                    break
                title_el = parent.find(["h2", "h3", "h4", "strong"])
                if title_el and len(title_el.get_text(strip=True)) > 1:
                    title = title_el.get_text(strip=True)
                    break
            if not title:
                continue
            href = a.get("href", "")
            booking_url = (href if href.startswith("http") else BASE_URL + href) if href else f"{BASE_URL}/home/Ticket"
            rows.append({
                "source": "國賓",
                "cinema": cinema_name,
                "movie": title,
                "poster": DEFAULT_POSTER,
                "datetime": f"{date_slash} {text}",
                "format": "數位",
                "booking_url": booking_url,
            })

    return rows


def crawl(days=14):
    """主爬蟲：抓取未來N天國賓場次"""
    print("[國賓] 開始爬取...")
    all_rows = []

    cinemas = get_cinemas_list()
    today = datetime.today()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]

    for cinema_id, cinema_name in cinemas.items():
        print(f"  影城: {cinema_name}")
        for date_str in dates:
            # 先嘗試 API
            api_data, api_url = get_showtimes_api(cinema_id, date_str)
            if api_data:
                # 解析 API 資料
                items = api_data if isinstance(api_data, list) else (
                    api_data.get("data") or api_data.get("showtimes") or []
                )
                for item in items:
                    title = (item.get("MovieName") or item.get("movie_name") or
                             item.get("title") or item.get("FilmName") or "")
                    show_time = (item.get("ShowTime") or item.get("show_time") or
                                 item.get("time") or "")
                    if show_time:
                        show_time = re.search(r"\d{1,2}:\d{2}", str(show_time))
                        show_time = show_time.group() if show_time else ""
                    poster = item.get("Poster") or item.get("poster") or DEFAULT_POSTER
                    fmt = item.get("Format") or item.get("format") or item.get("Version") or "數位"
                    booking_id = item.get("TicketUrl") or item.get("ticket_url") or item.get("SessionId") or ""
                    booking_url = booking_id if booking_id.startswith("http") else f"{BASE_URL}/home/Ticket"
                    if title and show_time:
                        date_slash = date_str.replace("-", "/")
                        all_rows.append({
                            "source": "國賓",
                            "cinema": cinema_name,
                            "movie": title,
                            "poster": poster,
                            "datetime": f"{date_slash} {show_time}",
                            "format": fmt,
                            "booking_url": booking_url,
                        })
            else:
                # HTML fallback
                rows = parse_showtime_html(cinema_id, cinema_name, date_str)
                all_rows.extend(rows)
            time.sleep(0.4)
        time.sleep(0.5)

    print(f"[國賓] 共取得 {len(all_rows)} 筆")
    return all_rows


if __name__ == "__main__":
    rows = crawl(days=3)
    print(json.dumps(rows[:3], ensure_ascii=False, indent=2))
