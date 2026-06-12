import streamlit as st
import streamlit.components.v1 as components
import json, re, html, os
from collections import defaultdict
from datetime import datetime

st.set_page_config(
    page_title="Movier｜全台電影場次查詢",
    layout="wide"
)
st.markdown("""
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1 style="
font-size:72px;
font-weight:900;
color:white;
margin-bottom:0;
">
Movier.
</h1>

<p style="
font-size:24px;
color:white;
margin-top:0;
font-weight:700;
">
全台電影場次快速查詢平台
</p>

<p style="
font-size:18px;
color:white;
opacity:.9;
margin-bottom:36px;
">
整合威秀、新光、秀泰、國賓影城，即時查詢各地電影時段。
</p>
""", unsafe_allow_html=True)

freshness = get_data_freshness()
if freshness:
    st.markdown(f'<p style="font-size:14px;color:rgba(255,255,255,.75);margin-top:-20px;margin-bottom:10px;">{freshness}</p>', unsafe_allow_html=True)

DEFAULT_POSTER = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=900"

@st.cache_data
def load_rows():
    with open("movie_rows.json", "r", encoding="utf-8") as f:
        return json.load(f)

def get_data_freshness():
    try:
        mtime = os.path.getmtime("movie_rows.json")
        updated = datetime.fromtimestamp(mtime)
        delta = datetime.now() - updated
        if delta.days >= 2:
            return f"⚠️ 資料上次更新：{updated.strftime('%Y/%m/%d')}（{delta.days} 天前，可能過期）"
        return f"✅ 資料更新於：{updated.strftime('%Y/%m/%d %H:%M')}"
    except Exception:
        return ""

def classify(cinema):
    if any(x in cinema for x in ["信義", "松仁", "大巨蛋"]):
        return "台北市", "信義 / 松仁"
    if any(x in cinema for x in ["西門", "欣欣", "獅子林"]):
        return "台北市", "西門 / 西區"
    if "天母" in cinema:
        return "台北市", "天母"
    if "長春" in cinema or cinema == "國賓大戲院":
        return "台北市", "長春"
    if "南港" in cinema:
        return "台北市", "南港"
    if "國賓大戲院" in cinema:
        return "台北市", "西門 / 欣欣"

    if "板橋" in cinema:
        return "新北市", "板橋"
    if "新莊" in cinema:
        return "新北市", "新莊"
    if "林口" in cinema:
        return "新北市", "林口"
    if "淡水" in cinema:
        return "新北市", "淡水"
    if "土城" in cinema:
        return "新北市", "土城"
    if "樹林" in cinema:
        return "新北市", "樹林"

    if "青埔" in cinema:
        return "桃園市", "青埔"
    if "八德" in cinema:
        return "桃園市", "八德"
    if "桃園" in cinema:
        return "桃園市", "桃園區"

    if "巨城" in cinema:
        return "新竹市", "巨城"
    if "新竹" in cinema:
        return "新竹市", "遠百 / 市區"

    if any(x in cinema for x in ["台中中港", "台中大遠百", "TIGER", "Tiger", "MUVIE CINEMAS 台中"]):
        return "台中市", "七期 / 新光遠百老虎城"
    if "站前" in cinema:
        return "台中市", "火車站"
    if "文心" in cinema:
        return "台中市", "文心"
    if "麗寶" in cinema:
        return "台中市", "麗寶"

    if "嘉義" in cinema:
        return "嘉義市", "嘉義市區"

    if "南紡" in cinema:
        return "台南市", "南紡"
    if "仁德" in cinema:
        return "台南市", "仁德"
    if "台南" in cinema and "西門" in cinema:
        return "台南市", "西門"

    if "夢時代" in cinema or "高雄大遠百" in cinema:
        return "高雄市", "夢時代 / 大遠百"
    if "草衙" in cinema:
        return "高雄市", "草衙道"
    if "義大" in cinema:
        return "高雄市", "義大"
    if "岡山" in cinema:
        return "高雄市", "岡山"

    if "屏東" in cinema:
        return "屏東縣", "屏東市"
    if "花蓮" in cinema:
        return "花蓮縣", "花蓮市"
    if "台東" in cinema:
        return "台東縣", "台東市"
    if "基隆" in cinema:
        return "基隆市", "基隆市區"
    if "金門" in cinema:
        return "金門縣", "金門"
    if "北港" in cinema:
        return "雲林縣", "北港"

    return "其他", "其他"

def norm_movie(s):
    s = str(s)
    s = re.sub(r"[\s　:：\-_\(\)（）【】\[\]！!‧・.。,，]", "", s)
    for x in ["電影版", "數位", "中文版", "英文版", "國語版", "日語版", "4K", "修復版"]:
        s = s.replace(x, "")
    return s.lower()

def same_movie(a, b):
    x, y = norm_movie(a), norm_movie(b)
    return x == y or x in y or y in x


def render_ads(rows):
    seen = set()
    cards = ""

    for r in rows:
        p = r.get("poster")
        title = r.get("movie", "")
        if not p or p == DEFAULT_POSTER or p in seen:
            continue
        seen.add(p)
        cards += f"""
        <div class="ad-card">
            <img src="{p}">
            <div class="ad-title">{html.escape(title)}</div>
        </div>
        """
        if len(seen) >= 12:
            break

    cards = cards + cards

    components.html(f"""
    <style>
    body {{
        margin:0;
        background:#4d93b8;
        font-family:'Inter','Noto Sans TC',sans-serif;
    }}
    .ad-viewport {{
        width:100%;
        overflow:hidden;
        padding:6px 0 18px;
    }}
    .ad-track {{
        display:flex;
        gap:20px;
        width:max-content;
        animation:scrollAds 38s linear infinite;
    }}
    .ad-track:hover {{
        animation-play-state:paused;
    }}
    .ad-card {{
        flex:0 0 210px;
        height:315px;
        border-radius:24px;
        overflow:hidden;
        background:#111827;
        position:relative;
        box-shadow:0 14px 34px rgba(0,0,0,.24);
    }}
    .ad-card img {{
        width:100%;
        height:100%;
        object-fit:cover;
    }}
    .ad-title {{
        position:absolute;
        left:0;
        right:0;
        bottom:0;
        padding:42px 13px 14px;
        color:white;
        font-size:17px;
        font-weight:900;
        background:linear-gradient(transparent,rgba(0,0,0,.9));
        text-shadow:0 4px 12px rgba(0,0,0,.75);
    }}
    @keyframes scrollAds {{
        from {{ transform:translateX(0); }}
        to {{ transform:translateX(-50%); }}
    }}
    </style>
    <div class="ad-viewport">
        <div class="ad-track">{cards}</div>
    </div>
    """, height=355)

def render_showtimes(movie, rows):
    poster = rows[0].get("poster") or DEFAULT_POSTER
    groups = defaultdict(list)
    for r in rows:
        groups[r["cinema"]].append(r)

    cinema_html = ""
    for cinema, items in groups.items():
        items = sorted(items, key=lambda x: x["datetime"])
        source = " + ".join(sorted(set(i["source"] for i in items)))

        date_groups = defaultdict(list)
        used = set()
        for item in items:
            parts = item["datetime"].split(" ")
            if len(parts) < 2:
                continue
            date = parts[0][5:]
            time = parts[1][:5]
            key = (date, time, item.get("format", ""))
            if key in used:
                continue
            used.add(key)
            date_groups[date].append((time, item["booking_url"]))

        dates_html = ""
        for date, times in date_groups.items():
            btns = "".join([
                f'<a class="time-btn" href="{url}" target="_blank">{time}</a>'
                for time, url in times
            ])
            dates_html += f"""
            <div class="date-block">
                <div class="date-title">{date}</div>
                <div class="time-row">{btns}</div>
            </div>
            """

        cinema_html += f"""
        <div class="cinema-block">
            <div class="cinema-title">{html.escape(cinema)}</div>
            <div class="source">{html.escape(source)}</div>
            {dates_html}
        </div>
        """

    components.html(f"""
    <style>
    body {{
        margin:0;
        background:#4d93b8;
        font-family:'Inter','Noto Sans TC',sans-serif;
    }}
    .show-wrap {{
        display:grid;
        grid-template-columns:330px 1fr;
        gap:34px;
        align-items:start;
    }}
    .poster {{
        width:330px;
        height:495px;
        object-fit:cover;
        border-radius:28px;
        box-shadow:0 16px 36px rgba(0,0,0,.26);
    }}
    @media (max-width: 768px) {{
        .show-wrap {{
            display:block;
        }}
    
        .poster {{
            width:100%;
            height:auto;
            max-height:430px;
            object-fit:contain;
            margin-bottom:18px;
        }}
    
        .card {{
            padding:22px;
            border-radius:24px;
            max-height:none;
            overflow:visible;
        }}
    
        .movie-title {{
            font-size:32px;
        }}
    }}
    .card {{
        background:rgba(255,255,255,.96);
        border-radius:34px;
        padding:38px;
        color:#10263a;
        box-shadow:0 18px 42px rgba(0,0,0,.18);
        max-height:780px;
        overflow-y:auto;
    }}
    .movie-title {{
        font-size:44px;
        font-weight:900;
        line-height:1.18;
        margin-bottom:12px;
    }}
    .meta {{
        font-size:18px;
        font-weight:900;
        color:#526575;
        margin-bottom:26px;
    }}
    .cinema-block {{
        border-top:1px solid #d9e2ea;
        padding-top:22px;
        margin-top:22px;
    }}
    .cinema-title {{
        font-size:27px;
        font-weight:900;
    }}
    .source {{
        font-size:16px;
        font-weight:900;
        color:#64748b;
        margin:8px 0 16px;
    }}
    .date-title {{
        font-size:17px;
        font-weight:900;
        color:#64748b;
        margin:16px 0 8px;
    }}
    .time-row {{
        display:flex;
        flex-wrap:wrap;
        gap:12px;
    }}
    .time-btn {{
        display:inline-block;
        padding:12px 25px;
        border-radius:999px;
        background:linear-gradient(135deg,#4f46e5,#7c3aed);
        color:white;
        text-decoration:none;
        font-size:20px;
        font-weight:900;
    }}
    </style>

    <div class="show-wrap">
        <img class="poster" src="{poster}">
        <div class="card">
            <div class="movie-title">{html.escape(movie)}</div>
            <div class="meta">威秀 + 秀泰 + 新光 + 國賓</div>
            {cinema_html}
        </div>
    </div>
    """, height=1280, scrolling=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Noto+Sans+TC:wght@500;700;900&display=swap');
html, body, [class*="css"] {
    font-family:'Inter','Noto Sans TC',sans-serif !important;
}
header, footer, #MainMenu {visibility:hidden;}
.stApp {background:#4d93b8;}
.block-container {
    max-width:1180px;
    padding:2.5rem 2rem 5rem;
}
.logo {
    color:white;
    font-size:84px;
    font-weight:900;
    letter-spacing:-4px;
    line-height:1;
    margin-bottom:20px;
}
.tagline {
    color:white;
    font-size:23px;
    font-weight:900;
    margin-bottom:26px;
}
label {
    color:white !important;
    font-size:18px !important;
    font-weight:900 !important;
}
.stButton > button {
    background:#111827;
    color:white;
    border:none;
    border-radius:999px;
    padding:14px 34px;
    font-size:18px;
    font-weight:900;
}
.page-title {
    color:white;
    font-size:56px;
    font-weight:900;
    letter-spacing:-2px;
    line-height:1.05;
    margin:18px 0 28px;
    font-family:'Inter','Noto Sans TC',sans-serif;
}
.notice {
    color:rgba(255,255,255,.95);
    font-size:19px;
    font-weight:800;
    letter-spacing:-0.3px;
    margin-top:22px;
}
@media (max-width: 768px) {
    .block-container {
        padding: 1.2rem 1rem 3rem;
    }

    .logo {
        font-size: 52px;
        letter-spacing: -2px;
    }

    .tagline {
        font-size: 17px;
        line-height: 1.3;
    }

    .ad-card {
        flex: 0 0 150px;
        height: 225px;
        border-radius: 18px;
    }

    .ad-title {
        font-size: 14px;
        padding: 34px 10px 12px;
    }

    .show-wrap {
        display: block;
    }

    .poster {
        width: 100%;
        height: auto;
        max-height: 520px;
        object-fit: contain;
        margin-bottom: 20px;
    }

    .card {
        padding: 24px;
        border-radius: 26px;
        max-height: none;
    }

    .movie-title {
        font-size:56px;
        font-weight:900;
        color:#10233d;
        line-height:1.02;
        letter-spacing:-2px;
        margin-bottom:12px;
        font-family:'Inter','Noto Sans TC',sans-serif;
    }

    .cinema-title {
        font-size:42px;
        font-weight:900;
        color:#10233d;
        letter-spacing:-1.5px;
        line-height:1.08;
        margin-bottom:8px;
        font-family:'Inter','Noto Sans TC',sans-serif;
    }

    .time-btn {
        font-size: 18px;
        padding: 10px 20px;
    }
}
</style>
""", unsafe_allow_html=True)

rows = load_rows()
for r in rows:
    c, a = classify(r.get("cinema", ""))
    r["city"] = c
    r["area"] = a

if "page" not in st.session_state:
    st.session_state.page = "home"

if st.session_state.page == "home":
    render_ads(rows)

    city_area = defaultdict(set)
    for r in rows:
        if r["city"] != "其他":
            city_area[r["city"]].add(r["area"])

    CITY_ORDER = [
        "金門縣", "屏東縣", "高雄市", "台南市", "嘉義市",
        "台中市", "新竹市", "桃園市", "新北市", "台北市", "基隆市",
        "花蓮縣", "台東縣"
    ]

    cities = [c for c in CITY_ORDER if c in city_area]
    cities += [c for c in sorted(city_area.keys()) if c not in cities and c != "其他"]

    city = st.selectbox("選擇縣市", cities)

    AREA_ORDER = [
        "七期 / 新光遠百老虎城", "信義 / 松仁", "西門 / 西區",
        "火車站", "文心", "麗寶", "長春", "天母", "大巨蛋",
        "板橋", "新莊", "淡水", "林口", "土城", "樹林",
        "桃園區", "青埔", "八德", "巨城", "遠百 / 市區",
        "南紡", "西門", "仁德", "夢時代 / 大遠百", "草衙道", "義大", "岡山"
    ]

    areas = [a for a in AREA_ORDER if a in city_area[city]]
    areas += [a for a in sorted(city_area[city]) if a not in areas]

    area = st.selectbox("選擇區域", areas)

    if st.button("查詢電影"):
        st.session_state.city = city
        st.session_state.area = area
        st.session_state.page = "movies"
        st.rerun()

elif st.session_state.page == "movies":
    city = st.session_state.city
    area = st.session_state.area

    filtered = [
        r for r in rows
        if r.get("city") == city and r.get("area") == area
    ]

    st.markdown(f'<div class="page-title">{city}｜{area}</div>', unsafe_allow_html=True)

    if not filtered:
        st.warning("這個區域目前沒有抓到場次。")
    else:
        display = {}
        for r in filtered:
            key = norm_movie(r["movie"])
            if key not in display:
                display[key] = r["movie"]

        selected = st.selectbox("選擇電影", sorted(display.values()))

        if st.button("查看場次"):
            st.session_state.selected_movie = selected
            st.session_state.selected_rows = [
                r for r in filtered
                if same_movie(r["movie"], selected)
            ]
            st.session_state.page = "showtimes"
            st.rerun()

    if st.button("回首頁"):
        st.session_state.page = "home"
        st.rerun()

elif st.session_state.page == "showtimes":
    render_showtimes(
        st.session_state.selected_movie,
        st.session_state.selected_rows
    )

    st.markdown('<div class="notice">各影城訂票會導回官方網站完成。</div>', unsafe_allow_html=True)

    if st.button("回上一步"):
        st.session_state.page = "movies"
        st.rerun()
