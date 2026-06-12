"""秀泰影城 (Showtimes) 爬蟲"""
import requests
import json
import time
from datetime import datetime, timedelta

CAPI_BASE = "https://capi.showtimes.com.tw"
WEB_BASE = "https://www.showtimes.com.tw"
CORPORATION_ID = 8  # 秀泰法人ID

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Origin": "https://www.showtimes.com.tw",
    "Referer": "https://www.showtimes.com.tw/",
}

# 秀泰各影城 cinemaCode
CINEMA_IDS = {
    "1": "台北欣欣秀泰影城",
    "2": "大巨蛋秀泰影城",
    "3": "土城秀泰影城",
    "4": "樹林秀泰影城",
    "5": "台中站前秀泰影城",
    "6": "台中文心秀泰影城",
    "7": "台中麗寶秀泰影城",
    "8": "嘉義秀泰影城",
    "9": "台南仁德秀泰影城",
    "10": "台東秀泰影城",
    "11": "花蓮秀泰影城",
    "12": "高雄夢時代秀泰影城",
    "13": "高雄岡山秀泰影城",
    "14": "北港秀泰影城",
    "15": "基隆秀泰影城",
}


def get_events_by_date(date_str):
    """用日期抓取全部秀泰場次 (capi v1)"""
    url = f"{CAPI_BASE}/1/events/listForCorporation/{CORPORATION_ID}"
    try:
        r = requests.get(url, params={"date": date_str, "limit": 3000},
                         headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"  [秀泰capi] {date_str} 錯誤: {e}")
    return []


def get_events_by_cinema_date(cinema_id, date_str):
    """用影城+日期抓取場次"""
    url = f"{CAPI_BASE}/1/events/listByCinema/{cinema_id}"
    try:
        r = requests.get(url, params={"date": date_str, "limit": 500},
                         headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    # try another endpoint variant
    try:
        url2 = f"{CAPI_BASE}/1/cinemas/{cinema_id}/events"
        r = requests.get(url2, params={"date": date_str, "limit": 500},
                         headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def get_cinemas():
    """取得秀泰影城列表"""
    try:
        r = requests.get(f"{CAPI_BASE}/1/cinemas/listForCorporation/{CORPORATION_ID}",
                         headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            result = {}
            for c in data:
                cid = str(c.get("id", ""))
                name = c.get("name", "") or c.get("cinema_name", "")
                if cid and name:
                    result[cid] = name
            if result:
                return result
    except Exception:
        pass
    return CINEMA_IDS


def _safe_dict_get(val, key, default=""):
    """若 val 是 dict 才 .get()，否則回傳 default"""
    if isinstance(val, dict):
        return val.get(key, default)
    return default


def parse_event(event, cinema_name_map):
    """解析單一場次事件"""
    cinema_field = event.get("cinema")
    cinema_id = str(
        event.get("cinemaId") or event.get("cinema_id") or
        _safe_dict_get(cinema_field, "id") or ""
    )
    cinema_name = (
        event.get("cinemaName") or event.get("cinema_name") or
        _safe_dict_get(cinema_field, "name") or
        (cinema_field if isinstance(cinema_field, str) else "") or
        cinema_name_map.get(cinema_id, f"秀泰影城{cinema_id}")
    )

    film_field = event.get("film")
    movie = (event.get("filmName") or event.get("film_name") or
             event.get("movie") or event.get("title") or
             _safe_dict_get(film_field, "name") or "")

    poster = (event.get("filmPoster") or event.get("film_poster") or
              event.get("poster") or event.get("image") or
              _safe_dict_get(film_field, "poster_url") or "")
    if poster and not poster.startswith("http"):
        poster = f"https://assets.showtimes.com.tw/images/{poster}"

    show_dt = (event.get("showTime") or event.get("show_time") or
               event.get("startTime") or event.get("start_time") or
               event.get("datetime") or "")
    if show_dt:
        # normalize datetime to YYYY/MM/DD HH:MM
        show_dt = show_dt.replace("T", " ")[:16].replace("-", "/")

    fmt = (event.get("filmVersion") or event.get("film_version") or
           event.get("version") or event.get("format") or "數位")

    ticket_type_id = (event.get("ticketTypeId") or event.get("ticket_type_id") or
                      event.get("id") or event.get("eventId") or "")
    if ticket_type_id:
        booking_url = f"{WEB_BASE}/ticketing/cart/selectTicketTypes/{ticket_type_id}"
    else:
        booking_url = WEB_BASE

    if not movie or not show_dt:
        return None

    return {
        "source": "秀泰",
        "cinema": cinema_name,
        "movie": movie,
        "poster": poster or "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=900",
        "datetime": show_dt,
        "format": fmt,
        "booking_url": booking_url,
    }


def crawl(days=14):
    """主爬蟲：抓取未來N天秀泰場次"""
    print("[秀泰] 開始爬取...")
    all_rows = []
    cinema_name_map = get_cinemas()

    today = datetime.today()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]

    # 優先嘗試一次抓全部日期
    for date_str in dates:
        print(f"  日期: {date_str}")
        events = get_events_by_date(date_str)
        if events:
            for ev in events:
                row = parse_event(ev, cinema_name_map)
                if row:
                    all_rows.append(row)
            print(f"    取得 {len(events)} 筆")
        else:
            # fallback: 逐影城抓
            for cinema_id, cinema_name in cinema_name_map.items():
                evs = get_events_by_cinema_date(cinema_id, date_str)
                for ev in evs:
                    row = parse_event(ev, cinema_name_map)
                    if row:
                        all_rows.append(row)
                time.sleep(0.2)
        time.sleep(0.5)

    print(f"[秀泰] 共取得 {len(all_rows)} 筆")
    return all_rows


if __name__ == "__main__":
    rows = crawl(days=3)
    print(json.dumps(rows[:3], ensure_ascii=False, indent=2))
