"""威秀影城 (VSCinemas) 爬蟲"""
import requests
import json
import re
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

BASE_URL = "https://www.vscinemas.com.tw"
DEFAULT_POSTER = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=900"

CINEMA_MAP = {
    "A": "台北西門威秀影城",
    "B": "台北信義威秀影城",
    "C": "南港Lalaport威秀影城",
    "D": "京站威秀影城",
    "E": "MUVIE CINEMAS 台北松仁",
    "F": "板橋大遠百威秀影城",
    "G": "林口MITSUI OUTLET PARK威秀影城",
    "H": "新竹大遠百威秀影城",
    "I": "新竹巨城威秀影城",
    "J": "台中大遠百威秀影城",
    "K": "台南南紡威秀影城",
    "L": "台南大遠百威秀影城",
    "M": "花蓮新天堂樂園威秀影城",
    "N": "高雄大遠百威秀影城",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.vscinemas.com.tw/",
    "X-Requested-With": "XMLHttpRequest",
}


def get_cinema_list():
    """取得影城列表"""
    try:
        r = requests.get(
            f"{BASE_URL}/vsweb/api/GetLstDicLocation",
            headers=HEADERS, timeout=15
        )
        if r.status_code == 200 and r.text.strip().startswith("["):
            return r.json()
    except Exception:
        pass
    # fallback: use hardcoded cinema IDs
    return [{"sCinemaCode": k, "sCinemaName": v} for k, v in CINEMA_MAP.items()]


def get_films():
    """取得上映電影列表 (含海報)"""
    films = {}
    try:
        r = requests.get(
            f"{BASE_URL}/vsweb/api/GetLstDicFilm",
            headers=HEADERS, timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            for f in data:
                code = f.get("sFilmCode", "")
                name = f.get("sFilmName", "")
                poster = f.get("sPoster", "") or DEFAULT_POSTER
                if not poster.startswith("http"):
                    poster = BASE_URL + poster if poster else DEFAULT_POSTER
                films[code] = {"name": name, "poster": poster}
    except Exception:
        pass
    return films


def get_sessions_by_cinema(cinema_code, date_str):
    """取得特定影城在指定日期的場次"""
    try:
        r = requests.get(
            f"{BASE_URL}/vsweb/api/GetLstSession",
            params={"sCinemaCode": cinema_code, "sDate": date_str},
            headers=HEADERS, timeout=15
        )
        if r.status_code == 200 and r.text.strip().startswith("["):
            return r.json()
    except Exception:
        pass
    return []


def parse_html_showtimes(cinema_code, cinema_name, date_str, films):
    """HTML fallback: 解析威秀場次頁面"""
    rows = []
    try:
        url = f"{BASE_URL}/vsweb/showtime/index.aspx"
        r = requests.get(url, params={"cinemaid": cinema_code, "date": date_str},
                         headers={**HEADERS, "Accept": "text/html"}, timeout=15)
        if r.status_code != 200:
            return rows
        soup = BeautifulSoup(r.text, "html.parser")
        for movie_block in soup.select(".filmArea, .movieItem, [class*='film']"):
            title_el = movie_block.select_one("h2, h3, .filmTitle, .title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            poster_el = movie_block.select_one("img")
            poster = DEFAULT_POSTER
            if poster_el:
                src = poster_el.get("src", "")
                poster = (BASE_URL + src) if src and not src.startswith("http") else (src or DEFAULT_POSTER)

            for time_el in movie_block.select("a.time, .showtime a, time, [class*='time']"):
                time_text = time_el.get_text(strip=True)
                if not re.match(r"\d{1,2}:\d{2}", time_text):
                    continue
                booking_url = time_el.get("href", "https://www.vscinemas.com.tw/")
                if booking_url and not booking_url.startswith("http"):
                    booking_url = BASE_URL + booking_url
                rows.append({
                    "source": "威秀",
                    "cinema": cinema_name,
                    "movie": title,
                    "poster": poster,
                    "datetime": f"{date_str.replace('-', '/')} {time_text}",
                    "format": "威秀",
                    "booking_url": booking_url or "https://www.vscinemas.com.tw/",
                })
    except Exception as e:
        print(f"  [威秀HTML] {cinema_name} {date_str} 錯誤: {e}")
    return rows


def crawl(days=14):
    """主爬蟲：抓取未來N天的威秀場次"""
    print("[威秀] 開始爬取...")
    all_rows = []
    films = get_films()
    cinemas = get_cinema_list()

    today = datetime.today()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]

    for cinema in cinemas:
        code = cinema.get("sCinemaCode", "")
        name = cinema.get("sCinemaName", code)
        if not code:
            continue
        print(f"  影城: {name}")
        for date_str in dates:
            sessions = get_sessions_by_cinema(code, date_str)
            if sessions:
                for s in sessions:
                    film_code = s.get("sFilmCode", "")
                    film_info = films.get(film_code, {})
                    title = film_info.get("name") or s.get("sFilmName", "")
                    poster = film_info.get("poster", DEFAULT_POSTER)
                    show_time = s.get("sShowTime", "")
                    fmt = s.get("sFilmVersion", "") or s.get("sFormat", "威秀")
                    session_id = s.get("sSessionCode", "") or s.get("sId", "")
                    if session_id:
                        booking_url = f"https://www.vscinemas.com.tw/hold/?session={session_id}"
                    else:
                        booking_url = "https://www.vscinemas.com.tw/"
                    if not title or not show_time:
                        continue
                    date_formatted = date_str.replace("-", "/")
                    all_rows.append({
                        "source": "威秀",
                        "cinema": name,
                        "movie": title,
                        "poster": poster,
                        "datetime": f"{date_formatted} {show_time}",
                        "format": fmt,
                        "booking_url": booking_url,
                    })
            else:
                html_rows = parse_html_showtimes(code, name, date_str, films)
                all_rows.extend(html_rows)
            time.sleep(0.3)
        time.sleep(0.5)

    print(f"[威秀] 共取得 {len(all_rows)} 筆")
    return all_rows


if __name__ == "__main__":
    rows = crawl(days=7)
    print(json.dumps(rows[:3], ensure_ascii=False, indent=2))
