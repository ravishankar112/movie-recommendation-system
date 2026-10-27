import csv
import hashlib
import io
import json
import os
import random
import re
import sqlite3
import threading
import time
from datetime import date, datetime
from html import escape
from urllib.parse import quote_plus

import pandas as pd
import requests
import streamlit as st


# CONFIG
API_BASE = os.getenv("API_BASE", "https://movie-rec-466x.onrender.com")

# For local testing use: API_BASE=http://127.0.0.1:8000
DB_PATH = os.getenv("DB_PATH", "movie_app.db")
TMDB_IMG = "https://image.tmdb.org/t/p/w500"
DEVELOPER = "Ravi Shankar Kumar"
DEVELOPER_ROLE = "AI/ML Engineer"

# Used to hash name + date of birth. Set your own value in production: APP_SALT=some-long-random-text
APP_SALT = os.getenv("APP_SALT", "movie-rec-ravi-shankar-kumar-v1")
MAX_LOGIN_FAILS = 5
LOCK_SECONDS = 60

HOME_PAGE_SIZE = 12
HOME_MAX = 60
RECENT_MAX = 12
SEARCH_HISTORY_MAX = 8
YEAR_MIN, YEAR_MAX = 1950, 2030

POPULAR_KEYWORDS = [
    "Avengers", "Batman", "Spider", "Love", "Harry Potter", "Star Wars",
    "Joker", "Fast", "Mission", "Toy Story", "Horror", "War",
]

st.set_page_config(page_title="Movie Recommender", page_icon="🎬", layout="wide")


# STYLES
BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp { font-family: 'Poppins', sans-serif; }

#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1400px; }
h1, h2, h3, h4 { font-family: 'Poppins', sans-serif !important; font-weight: 700 !important; }

/* ---------- Banner ---------- */
.stApp .banner {
  padding: 1.8rem 2rem; border-radius: 20px;
  background: linear-gradient(120deg, #7b1230 0%, #c8344e 55%, #f2994a 100%);
  box-shadow: 0 12px 30px rgba(200, 52, 78, 0.28); margin-bottom: 1.2rem;
}
.stApp .banner h1 { color: #ffffff !important; font-size: 2.3rem; margin: 0 0 0.3rem 0; font-weight: 800 !important; }
.stApp .banner p { color: #ffeede !important; margin: 0; font-size: 1rem; }

.stApp .banner .ml-pills span {
  display: inline-block; margin: 0.7rem 0.4rem 0 0; padding: 0.15rem 0.75rem; border-radius: 999px;
  font-size: 0.8rem; font-weight: 600; color: #ffffff;
  background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.32);
}

.small-muted { opacity: 0.7; font-size: 0.92rem; }

.section-title {
  font-size: 1.35rem; font-weight: 700; margin: 1.4rem 0 0.8rem 0;
  padding-left: 0.8rem; border-left: 5px solid #c8344e;
}
.kw-label { font-size: 0.9rem; font-weight: 600; margin: 0.6rem 0 0.3rem 0; opacity: 0.85; }

/* ---------- Posters ---------- */
div[data-testid="stImage"] img {
  border-radius: 14px; box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
div[data-testid="stImage"] img:hover { transform: translateY(-4px); box-shadow: 0 14px 28px rgba(200, 52, 78, 0.4); }
.no-poster {
  aspect-ratio: 2 / 3; border-radius: 14px; border: 1px dashed rgba(128,128,128,0.5);
  display: flex; align-items: center; justify-content: center; opacity: 0.7; font-size: 0.9rem;
}

/* ---------- Title + stickers under poster ---------- */
.movie-title {
  font-size: 0.92rem; line-height: 1.2rem; height: 2.4rem; overflow: hidden;
  font-weight: 600; margin: 0.5rem 0 0.25rem 0;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.stk-row { display: flex; flex-wrap: wrap; gap: 4px; min-height: 1.6rem; margin-bottom: 0.35rem; }
.stApp .stk {
  display: inline-block; padding: 0.1rem 0.5rem; border-radius: 999px;
  font-size: 0.72rem; font-weight: 600; line-height: 1.2rem; white-space: nowrap;
}
.stApp .stk.red   { background: #c8344e; color: #ffffff; }
.stApp .stk.gold  { background: #f2b84b; color: #2a1c00; }
.stApp .stk.green { background: #1f9d63; color: #ffffff; }
.stApp .stk.blue  { background: #2f6fed; color: #ffffff; }
.stApp .stk.pink  { background: #e0529c; color: #ffffff; }
.stApp .stk.grey  { background: rgba(128,128,128,0.35); color: inherit; }

/* ---------- Buttons ---------- */
.stButton > button, .stDownloadButton > button {
  width: 100%; border-radius: 999px; border: 1.5px solid #c8344e; color: #c8344e;
  background: transparent; font-weight: 600; transition: all 0.2s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover { background: #c8344e; color: #ffffff; border-color: #c8344e; }
[class*="st-key-chip_"] button { font-size: 0.8rem; padding: 0.15rem 0.6rem; min-height: 0; }
.stApp a.linkbtn {
  display: block; text-align: center; text-decoration: none !important;
  padding: 0.42rem 0.8rem; border-radius: 999px; font-weight: 600; font-size: 0.95rem;
  border: 1.5px solid #c8344e; color: #c8344e !important; transition: all 0.2s ease;
}
.stApp a.linkbtn:hover { background: #c8344e; color: #ffffff !important; }

/* ---------- Details ---------- */
.card {
  border: 1px solid rgba(128, 128, 128, 0.25); border-radius: 18px;
  padding: 18px 20px; background: rgba(128, 128, 128, 0.08);
}
.stApp .chip {
  display: inline-block; padding: 0.2rem 0.75rem; margin: 0 0.4rem 0.4rem 0;
  border-radius: 999px; font-size: 0.85rem; font-weight: 500; background: #c8344e; color: #ffffff;
}
.stApp .chip.gold { background: #f2b84b; color: #2a1c00; }
.stApp .chip.grey { background: rgba(128,128,128,0.35); color: inherit; }

/* ---------- Developer credit ---------- */
/* ---------- Developer card (AI/ML theme) ---------- */
.stApp .dev-card {
  position: relative; overflow: hidden; margin-top: 1.2rem; padding: 1rem 1rem 0.9rem 1rem;
  border-radius: 16px; color: #ffffff; border: 1px solid rgba(255,255,255,0.14);
  background:
    radial-gradient(120% 90% at 100% 0%, rgba(242,184,75,0.30), transparent 55%),
    linear-gradient(145deg, #1b1230 0%, #4a1230 55%, #c8344e 135%);
}
.dev-card .label { font-size: 0.78rem; color: #ffd9c2; }
.dev-card .name { font-size: 1.12rem; font-weight: 700; color: #ffffff; margin: 0.1rem 0 0.4rem 0; }
.dev-card .role {
  display: inline-block; padding: 0.12rem 0.65rem; border-radius: 999px;
  font-size: 0.78rem; font-weight: 700; background: #f2b84b; color: #2a1c00;
}
.dev-card svg { display: block; width: 100%; height: 56px; margin: 0.5rem 0 0.3rem 0; }
.dev-card .tags span, .about-hero .tags span {
  display: inline-block; margin: 0.15rem 0.25rem 0 0; padding: 0.05rem 0.55rem; border-radius: 999px;
  font-size: 0.7rem; font-weight: 600; color: #ffffff;
  background: rgba(255,255,255,0.14); border: 1px solid rgba(255,255,255,0.22);
}

/* ---------- Login ---------- */
.stApp .login-card {
  padding: 1.4rem 1.6rem 1.2rem 1.6rem; border-radius: 20px; color: #ffffff; margin-bottom: 1rem;
  border: 1px solid rgba(255,255,255,0.14);
  background:
    radial-gradient(100% 120% at 100% 0%, rgba(242,184,75,0.28), transparent 55%),
    linear-gradient(145deg, #1b1230 0%, #4a1230 60%, #c8344e 140%);
}
.stApp .login-card h2 { color: #ffffff !important; margin: 0 0 0.3rem 0; font-weight: 800 !important; }
.stApp .login-card p { color: #f1e6f5 !important; margin: 0; font-size: 0.95rem; line-height: 1.6; }
.login-card svg { display: block; width: 100%; height: 60px; margin-top: 0.8rem; }
.user-chip {
  padding: 0.5rem 0.8rem; border-radius: 12px; margin-bottom: 0.5rem;
  border: 1px solid rgba(128,128,128,0.3); background: rgba(128,128,128,0.1);
}

/* ---------- About page ---------- */
.stApp .about-hero {
  display: flex; flex-wrap: wrap; gap: 1.5rem; align-items: center;
  padding: 1.8rem 2rem; border-radius: 22px; color: #ffffff; margin-bottom: 1rem;
  border: 1px solid rgba(255,255,255,0.14);
  background:
    radial-gradient(90% 120% at 100% 0%, rgba(242,184,75,0.30), transparent 55%),
    linear-gradient(145deg, #1b1230 0%, #4a1230 55%, #c8344e 140%);
}
.about-hero .art { flex: 1 1 260px; max-width: 360px; }
.about-hero .art svg { width: 100%; height: auto; display: block; }
.about-hero .text { flex: 2 1 320px; }
.about-hero .label { font-size: 0.85rem; color: #ffd9c2; }
.about-hero .name { font-size: 2rem; font-weight: 800; color: #ffffff; line-height: 1.15; margin: 0.1rem 0 0.5rem 0; }
.about-hero .role {
  display: inline-block; padding: 0.15rem 0.8rem; border-radius: 999px;
  font-size: 0.9rem; font-weight: 700; background: #f2b84b; color: #2a1c00;
}
.about-hero .desc { color: #f1e6f5; margin: 0.8rem 0 0.4rem 0; line-height: 1.7; }
.stApp .pipe {
  border: 1px solid rgba(128,128,128,0.28); border-radius: 16px; padding: 1rem 1.1rem;
  background: rgba(128,128,128,0.08); height: 100%;
}
.pipe .num {
  display: inline-block; width: 1.7rem; height: 1.7rem; line-height: 1.7rem; text-align: center;
  border-radius: 50%; background: #c8344e; color: #ffffff; font-weight: 700; font-size: 0.9rem;
}
.pipe .ttl { font-weight: 700; margin: 0.5rem 0 0.2rem 0; }
.pipe .txt { font-size: 0.88rem; opacity: 0.85; line-height: 1.55; }

.footer {
  text-align: center; opacity: 0.75; font-size: 0.92rem;
  margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid rgba(128,128,128,0.3);
}
.footer b { color: #c8344e; }

@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
"""

DARK_CSS = """
<style>
.stApp, section[data-testid="stSidebar"] { background: #12101a !important; }
header[data-testid="stHeader"] { background: transparent !important; }
.stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stMetricValue"],
.stApp [data-testid="stMetricLabel"], .stApp summary { color: #f3eff8 !important; }
.stApp .banner h1 { color: #ffffff !important; }
.stApp .banner p { color: #ffeede !important; }
.stApp .stTextInput input, .stApp .stTextArea textarea,
.stApp div[data-baseweb="select"] > div, .stApp div[data-baseweb="base-input"] {
  background: #1d1a28 !important; color: #f3eff8 !important; border-color: rgba(255,255,255,0.15) !important;
}
.stApp div[data-baseweb="select"] * { color: #f3eff8 !important; }
div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li, div[data-baseweb="popover"] div[role="listbox"] {
  background: #1d1a28 !important; color: #f3eff8 !important;
}
div[data-baseweb="popover"] li:hover { background: #2b2640 !important; }
.stApp [data-testid="stExpander"], .stApp [data-testid="stFileUploaderDropzone"] {
  border-color: rgba(255,255,255,0.15) !important; background: transparent !important;
}
.stApp .card { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.14); }
.stApp .movie-title { color: #f3eff8; }
</style>
"""

st.markdown(BASE_CSS, unsafe_allow_html=True)

# DATABASE (SQLite, permanent storage)
DB_LOCK = threading.Lock()


@st.cache_resource
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS library (
                profile TEXT NOT NULL,
                tmdb_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                poster_url TEXT,
                genres TEXT DEFAULT '',
                status TEXT DEFAULT 'to_watch',
                rating INTEGER DEFAULT 0,
                note TEXT DEFAULT '',
                added_at TEXT,
                rev INTEGER DEFAULT 1,
                PRIMARY KEY (profile, tmdb_id)
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS recent (
                profile TEXT NOT NULL,
                tmdb_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                poster_url TEXT,
                viewed_at TEXT,
                PRIMARY KEY (profile, tmdb_id)
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS accounts (
                user_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                created_at TEXT,
                last_login TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS searches (
                profile TEXT NOT NULL,
                term TEXT NOT NULL,
                searched_at TEXT,
                PRIMARY KEY (profile, term)
            )"""
        )
    return conn


def db_exec(sql, args=()):
    conn = get_db()
    with DB_LOCK, conn:
        conn.execute(sql, args)


def db_query(sql, args=()):
    with DB_LOCK:
        return get_db().execute(sql, args).fetchall()


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def clean_name(name: str) -> str:
    """Keeps letters (any language), digits, space, - and _ ; collapses extra spaces."""
    name = re.sub(r"[^\w\- ]", "", name or "", flags=re.UNICODE)
    return " ".join(name.split())[:30]


def me() -> str:
    return st.session_state.profile


def logged_in() -> bool:
    return bool(st.session_state.get("profile"))


# ---- library ----
def lib_get(mid):
    if not logged_in():
        return None
    rows = db_query(
        "SELECT * FROM library WHERE profile=? AND tmdb_id=?", (me(), int(mid))
    )
    return rows[0] if rows else None


def lib_save(movie: dict, status: str = "to_watch"):
    if not logged_in():
        return
    db_exec(
        """INSERT INTO library
           (profile, tmdb_id, title, poster_url, genres, status, rating, note, added_at, rev)
           VALUES (?,?,?,?,?,?,0,'',?,1)
           ON CONFLICT(profile, tmdb_id) DO UPDATE SET status=excluded.status, rev=library.rev+1""",
        (
            me(),
            int(movie["tmdb_id"]),
            movie["title"],
            movie.get("poster_url"),
            movie.get("genres", ""),
            status,
            now_iso(),
        ),
    )


def lib_update(mid, **fields):
    if not logged_in():
        return
    allowed = {"status", "rating", "note"}
    cols = [k for k in fields if k in allowed]
    if not cols:
        return
    sets = ", ".join(f"{c}=?" for c in cols) + ", rev=rev+1"
    db_exec(
        f"UPDATE library SET {sets} WHERE profile=? AND tmdb_id=?",
        tuple(fields[c] for c in cols) + (me(), int(mid)),
    )


def lib_delete(mid):
    if not logged_in():
        return
    db_exec("DELETE FROM library WHERE profile=? AND tmdb_id=?", (me(), int(mid)))


def lib_clear():
    if not logged_in():
        return
    db_exec("DELETE FROM library WHERE profile=?", (me(),))


ORDERS = {
    "Recently added": "added_at DESC",
    "Title (A–Z)": "title COLLATE NOCASE ASC",
    "My rating": "rating DESC, added_at DESC",
}


def lib_list(order: str = "Recently added"):
    if not logged_in():
        return []
    return db_query(
        f"SELECT * FROM library WHERE profile=? ORDER BY {ORDERS.get(order, ORDERS['Recently added'])}",
        (me(),),
    )


def lib_import(items):
    if not logged_in():
        return 0
    count = 0
    for it in items:
        try:
            mid = int(it["tmdb_id"])
            title = str(it["title"])
        except (KeyError, TypeError, ValueError):
            continue
        status = it.get("status") if it.get("status") in ("to_watch", "watched") else "to_watch"
        try:
            rating = max(0, min(5, int(it.get("rating") or 0)))
        except (TypeError, ValueError):
            rating = 0
        db_exec(
            """INSERT INTO library
               (profile, tmdb_id, title, poster_url, genres, status, rating, note, added_at, rev)
               VALUES (?,?,?,?,?,?,?,?,?,1)
               ON CONFLICT(profile, tmdb_id) DO UPDATE SET
                 title=excluded.title, poster_url=excluded.poster_url, genres=excluded.genres,
                 status=excluded.status, rating=excluded.rating, note=excluded.note, rev=library.rev+1""",
            (
                me(),
                mid,
                title,
                it.get("poster_url"),
                it.get("genres") or "",
                status,
                rating,
                str(it.get("note") or ""),
                it.get("added_at") or now_iso(),
            ),
        )
        count += 1
    return count


#  recently viewed
def recent_add(movie: dict):
    if not logged_in():
        return
    db_exec(
        """INSERT INTO recent (profile, tmdb_id, title, poster_url, viewed_at)
           VALUES (?,?,?,?,?)
           ON CONFLICT(profile, tmdb_id) DO UPDATE SET
             viewed_at=excluded.viewed_at, title=excluded.title, poster_url=excluded.poster_url""",
        (me(), int(movie["tmdb_id"]), movie["title"], movie.get("poster_url"), now_iso()),
    )
    db_exec(
        """DELETE FROM recent WHERE profile=? AND tmdb_id NOT IN
           (SELECT tmdb_id FROM recent WHERE profile=? ORDER BY viewed_at DESC LIMIT ?)""",
        (me(), me(), RECENT_MAX),
    )


def recent_list():
    if not logged_in():
        return []
    rows = db_query(
        "SELECT * FROM recent WHERE profile=? ORDER BY viewed_at DESC LIMIT ?",
        (me(), RECENT_MAX),
    )
    return [
        {"tmdb_id": r["tmdb_id"], "title": r["title"], "poster_url": r["poster_url"]}
        for r in rows
    ]


# search history 
def search_add(term: str):
    if not logged_in():
        return
    term = term.strip().lower()
    if len(term) < 2:
        return
    db_exec(
        """INSERT INTO searches (profile, term, searched_at) VALUES (?,?,?)
           ON CONFLICT(profile, term) DO UPDATE SET searched_at=excluded.searched_at""",
        (me(), term, now_iso()),
    )
    db_exec(
        """DELETE FROM searches WHERE profile=? AND term NOT IN
           (SELECT term FROM searches WHERE profile=? ORDER BY searched_at DESC LIMIT ?)""",
        (me(), me(), SEARCH_HISTORY_MAX),
    )


def search_recent():
    if not logged_in():
        return []
    rows = db_query(
        "SELECT term FROM searches WHERE profile=? ORDER BY searched_at DESC LIMIT ?",
        (me(), SEARCH_HISTORY_MAX),
    )
    return [r["term"] for r in rows]


def search_clear():
    if not logged_in():
        return
    db_exec("DELETE FROM searches WHERE profile=?", (me(),))


# accounts (login with name + date of birth) 
def make_user_id(name: str, dob: date) -> str:
    """Account id = slow hash of name + date of birth. The date of birth itself is never stored."""
    key = " ".join(clean_name(name).lower().split())
    raw = f"{key}|{dob.isoformat()}".encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", raw, APP_SALT.encode("utf-8"), 120_000).hex()[:32]


def account_get(uid: str):
    rows = db_query("SELECT * FROM accounts WHERE user_id=?", (uid,))
    return rows[0] if rows else None


def account_create(uid: str, display_name: str):
    db_exec(
        "INSERT INTO accounts (user_id, display_name, created_at, last_login) VALUES (?,?,?,?)",
        (uid, display_name, now_iso(), now_iso()),
    )


def account_touch(uid: str):
    db_exec("UPDATE accounts SET last_login=? WHERE user_id=?", (now_iso(), uid))


def account_delete():
    uid = me()
    for table in ("library", "recent", "searches"):
        db_exec(f"DELETE FROM {table} WHERE profile=?", (uid,))
    db_exec("DELETE FROM accounts WHERE user_id=?", (uid,))


def logout():
    st.session_state.clear()
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.rerun()


def file_slug() -> str:
    return re.sub(r"\W+", "_", st.session_state.get("display_name") or "library").strip("_") or "library"



# STATE
VIEWS = ("home", "details", "library", "stats", "about")

if "view" not in st.session_state:
    st.session_state.view = "home"
if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None
if "home_limit" not in st.session_state:
    st.session_state.home_limit = HOME_PAGE_SIZE
if "last_category" not in st.session_state:
    st.session_state.last_category = None
if "profile" not in st.session_state:
    st.session_state.profile = None  # set after login (hashed account id)
if "display_name" not in st.session_state:
    st.session_state.display_name = None


# ROUTING (query params)
qp_view = st.query_params.get("view")
qp_id = st.query_params.get("id")
if qp_view in VIEWS:
    st.session_state.view = qp_view
if qp_id:
    try:
        st.session_state.selected_tmdb_id = int(qp_id)
        st.session_state.view = "details"
    except ValueError:
        pass


def _go(view: str):
    st.session_state.view = view
    st.query_params["view"] = view
    if "id" in st.query_params:
        del st.query_params["id"]
    st.rerun()


def goto_home():
    _go("home")


def goto_details(tmdb_id: int):
    st.session_state.view = "details"
    st.session_state.selected_tmdb_id = int(tmdb_id)
    st.query_params["view"] = "details"
    st.query_params["id"] = str(int(tmdb_id))
    st.rerun()



# API HELPERS (retry for cold-start servers)
class ApiError(Exception):
    pass


@st.cache_data(ttl=60, show_spinner=False)
def _fetch(path: str, params_items: tuple):
    last = "Unknown error"
    for attempt in range(3):
        try:
            r = requests.get(f"{API_BASE}{path}", params=dict(params_items), timeout=30)
        except requests.RequestException as e:
            last = f"Request failed: {e}"
            time.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code >= 500:
            last = f"HTTP {r.status_code}: {r.text[:200]}"
            time.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code >= 400:
            raise ApiError(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()
    raise ApiError(last)


def api_get_json(path: str, params: dict | None = None):
    try:
        data = _fetch(path, tuple(sorted((params or {}).items())))
        return data, None
    except Exception as e:  # errors are not cached
        return None, str(e)


# UI HELPERS
def toast(msg: str):
    try:
        st.toast(msg)
    except Exception:
        pass


def show_image(url: str):
    """Works on new and old Streamlit versions."""
    for kwargs in ({"width": "stretch"}, {"use_container_width": True}, {"use_column_width": True}):
        try:
            st.image(url, **kwargs)
            return
        except Exception:
            continue


def section_title(text: str):
    st.markdown(f"<div class='section-title'>{escape(text)}</div>", unsafe_allow_html=True)


def stars(n: int) -> str:
    return "★" * n + "☆" * (5 - n) if n else ""


def stickers_html(m: dict, lib_row, rank: int | None) -> str:
    out = []
    if rank:
        out.append(f"<span class='stk red'>#{rank}</span>")
    rating = m.get("vote_average")
    if isinstance(rating, (int, float)) and rating > 0:
        out.append(f"<span class='stk gold'>★ {rating:.1f}</span>")
    year = (m.get("release_date") or "")[:4]
    if year.isdigit():
        out.append(f"<span class='stk grey'>{year}</span>")
    if lib_row is not None:
        if lib_row["status"] == "watched":
            out.append("<span class='stk green'>✔ Watched</span>")
        else:
            out.append("<span class='stk blue'>🔖 To Watch</span>")
        if lib_row["rating"]:
            out.append(f"<span class='stk pink'>♥ {lib_row['rating']}/5</span>")
    return "".join(out)


def poster_grid(cards, cols=6, key_prefix="grid", show_rank=False):
    if not cards:
        st.info("No movies to show.")
        return

    lib_map = {r["tmdb_id"]: r for r in lib_list()}
    rows = (len(cards) + cols - 1) // cols
    idx = 0
    for r in range(rows):
        colset = st.columns(cols)
        for c in range(cols):
            if idx >= len(cards):
                break
            m = cards[idx]
            idx += 1

            tmdb_id = m.get("tmdb_id")
            title = m.get("title", "Untitled")
            poster = m.get("poster_url")
            try:
                lib_row = lib_map.get(int(tmdb_id)) if tmdb_id else None
            except (TypeError, ValueError):
                lib_row = None
            rank = idx if (show_rank and idx <= 10) else None

            with colset[c]:
                if poster:
                    show_image(poster)
                else:
                    st.markdown("<div class='no-poster'>No poster</div>", unsafe_allow_html=True)

                st.markdown(
                    f"<div class='movie-title' title='{escape(title, quote=True)}'>{escape(title)}</div>"
                    f"<div class='stk-row'>{stickers_html(m, lib_row, rank)}</div>",
                    unsafe_allow_html=True,
                )
                if m.get("caption"):
                    st.caption(m["caption"])

                if st.button("Open", key=f"{key_prefix}_{r}_{c}_{idx}_{tmdb_id}"):
                    if tmdb_id:
                        goto_details(tmdb_id)


def to_cards_from_tfidf_items(tfidf_items):
    cards = []
    for x in tfidf_items or []:
        tmdb = x.get("tmdb") or {}
        if tmdb.get("tmdb_id"):
            cards.append(
                {
                    "tmdb_id": tmdb["tmdb_id"],
                    "title": tmdb.get("title") or x.get("title") or "Untitled",
                    "poster_url": tmdb.get("poster_url"),
                }
            )
    return cards


def rows_to_cards(rows):
    return [
        {"tmdb_id": r["tmdb_id"], "title": r["title"], "poster_url": r["poster_url"]}
        for r in rows
    ]


def footer():
    st.markdown(
        f"<div class='footer'>Designed &amp; developed by <b>{DEVELOPER}</b> "
        f"<span class='chip'>{DEVELOPER_ROLE}</span></div>",
        unsafe_allow_html=True,
    )


def neural_svg(w: int = 240, h: int = 60, layers=(3, 5, 4, 2)) -> str:
    """Small neural-network drawing used as the AI/ML motif."""
    pad = 12
    xs = [pad + i * (w - 2 * pad) / (len(layers) - 1) for i in range(len(layers))]
    pts = []
    for li, n in enumerate(layers):
        pts.append([(xs[li], h * (k + 1) / (n + 1)) for k in range(n)])
    lines, dots = [], []
    for li in range(len(layers) - 1):
        for (x1, y1) in pts[li]:
            for (x2, y2) in pts[li + 1]:
                lines.append(
                    f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' "
                    f"stroke='rgba(255,255,255,0.28)' stroke-width='0.8'/>"
                )
    for li, layer in enumerate(pts):
        fill = "#f2b84b" if 0 < li < len(layers) - 1 else "#ffffff"
        for (x, y) in layer:
            dots.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3.2' fill='{fill}'/>")
    return (
        f"<svg viewBox='0 0 {w} {h}' xmlns='http://www.w3.org/2000/svg' "
        f"preserveAspectRatio='xMidYMid meet' role='img' aria-label='Neural network'>"
        + "".join(lines)
        + "".join(dots)
        + "</svg>"
    )


def dev_card_html() -> str:
    return (
        "<div class='dev-card'>"
        "<div class='label'>Developed by</div>"
        f"<div class='name'>{DEVELOPER}</div>"
        f"<span class='role'>{DEVELOPER_ROLE}</span>"
        f"{neural_svg(240, 56)}"
        "<div class='tags'><span>Machine Learning</span><span>NLP</span>"
        "<span>Recommender Systems</span></div>"
        "</div>"
    )


# ---- keyword chips (click to search) ----
def set_search(term: str):
    st.session_state.search_text = term


def keyword_chips(terms, prefix: str, per_row: int = 6):
    for start in range(0, len(terms), per_row):
        part = terms[start : start + per_row]
        cols = st.columns(per_row)
        for i, term in enumerate(part):
            with cols[i]:
                st.button(
                    term.title(),
                    key=f"chip_{prefix}_{start + i}",
                    on_click=set_search,
                    args=(term,),
                )



# Robust TMDB search parsing
# Supports BOTH API shapes:
# 1) raw TMDB: {"results":[{id,title,poster_path,vote_average,...}]}
# 2) list cards: [{tmdb_id,title,poster_url,...}]
# Multi-word keywords: every word must appear in the title.

def parse_tmdb_search_to_cards(data, keyword: str, limit: int = 24):
    tokens = [t for t in re.split(r"\s+", keyword.strip().lower()) if t]

    if isinstance(data, dict) and "results" in data:
        raw_items = []
        for m in data.get("results") or []:
            title = (m.get("title") or "").strip()
            tmdb_id = m.get("id")
            poster_path = m.get("poster_path")
            if not title or not tmdb_id:
                continue
            raw_items.append(
                {
                    "tmdb_id": int(tmdb_id),
                    "title": title,
                    "poster_url": f"{TMDB_IMG}{poster_path}" if poster_path else None,
                    "release_date": m.get("release_date", ""),
                    "vote_average": m.get("vote_average"),
                }
            )
    elif isinstance(data, list):
        raw_items = []
        for m in data:
            tmdb_id = m.get("tmdb_id") or m.get("id")
            title = (m.get("title") or "").strip()
            if not title or not tmdb_id:
                continue
            raw_items.append(
                {
                    "tmdb_id": int(tmdb_id),
                    "title": title,
                    "poster_url": m.get("poster_url"),
                    "release_date": m.get("release_date", ""),
                    "vote_average": m.get("vote_average"),
                }
            )
    else:
        return [], []

    matched = [x for x in raw_items if all(t in x["title"].lower() for t in tokens)]
    final_list = matched if matched else raw_items  # never blank

    suggestions = []
    for x in final_list[:10]:
        year = (x.get("release_date") or "")[:4]
        label = f"{x['title']} ({year})" if year else x["title"]
        suggestions.append((label, x["tmdb_id"]))

    return suggestions, final_list[:limit]


def filter_by_year(cards, year_range):
    if tuple(year_range) == (YEAR_MIN, YEAR_MAX):
        return cards
    out = []
    for c in cards:
        y = (c.get("release_date") or "")[:4]
        if y.isdigit() and year_range[0] <= int(y) <= year_range[1]:
            out.append(c)
    return out


def sort_cards(cards, mode: str):
    if mode == "Title (A–Z)":
        return sorted(cards, key=lambda x: x["title"].lower())
    if mode == "Newest first":
        return sorted(cards, key=lambda x: x.get("release_date") or "", reverse=True)
    if mode == "Top rated":
        return sorted(cards, key=lambda x: x.get("vote_average") or 0, reverse=True)
    return cards  # Relevance


# PERSONALISED "FOR YOU"
def get_for_you(limit: int = 12):
    rows = list(lib_list())
    if not rows:
        return []

    liked = sorted([r for r in rows if r["rating"] >= 4], key=lambda r: -r["rating"])
    watched = [r for r in rows if r["status"] == "watched"]
    seeds = (liked or watched or rows)[:3]
    saved_ids = {r["tmdb_id"] for r in rows}

    scores, meta = {}, {}
    for s in seeds:
        bundle, err = api_get_json(
            "/movie/search",
            params={"query": s["title"], "tfidf_top_n": 12, "genre_limit": 12},
        )
        if err or not bundle:
            continue
        weighted = [(c, 2) for c in to_cards_from_tfidf_items(bundle.get("tfidf_recommendations"))]
        weighted += [(c, 1) for c in (bundle.get("genre_recommendations") or [])]
        for c, w in weighted:
            cid = c.get("tmdb_id")
            if not cid or cid in saved_ids:
                continue
            scores[cid] = scores.get(cid, 0) + w
            if cid not in meta:
                meta[cid] = {
                    "tmdb_id": cid,
                    "title": c.get("title", "Untitled"),
                    "poster_url": c.get("poster_url"),
                    "caption": f"Because of {s['title']}",
                }
    ranked = sorted(scores, key=lambda k: -scores[k])[:limit]
    return [meta[k] for k in ranked]


# LOGIN (name + date of birth)
def dob_input(label: str, key: str):
    kwargs = dict(
        value=date(2000, 1, 1),
        min_value=date(1900, 1, 1),
        max_value=date.today(),
        key=key,
    )
    try:
        return st.date_input(label, format="DD/MM/YYYY", **kwargs)
    except TypeError:  # older Streamlit without the format option
        return st.date_input(label, **kwargs)


def sign_in(uid: str, display_name: str, welcome: str):
    account_touch(uid)
    st.session_state.profile = uid
    st.session_state.display_name = display_name
    st.session_state.welcome = welcome
    st.session_state.login_fails = 0
    st.session_state.auth_open = False
    st.rerun()


def handle_auth(name: str, dob, create: bool):
    st.session_state.auth_open = True
    wait = int(st.session_state.get("lock_until", 0) - time.time())
    if wait > 0:
        st.error(f"Too many wrong attempts. Please try again in {wait} seconds.")
        return

    name_c = clean_name(name)
    if len(name_c) < 2:
        st.error("Please enter your full name (at least 2 letters).")
        return
    if dob >= date.today():
        st.error("Date of birth must be in the past.")
        return

    uid = make_user_id(name_c, dob)
    acc = account_get(uid)

    if create:
        if acc:
            st.error("An account with this name and date of birth already exists. Please log in.")
            return
        account_create(uid, name_c)
        sign_in(uid, name_c, f"Account created. Welcome, {name_c}!")
    else:
        if not acc:
            fails = st.session_state.get("login_fails", 0) + 1
            st.session_state.login_fails = fails
            if fails >= MAX_LOGIN_FAILS:
                st.session_state.lock_until = time.time() + LOCK_SECONDS
                st.session_state.login_fails = 0
            st.error(
                "No account found for this name and date of birth. "
                "Check the details or create a new account."
            )
            return
        sign_in(uid, acc["display_name"], f"Welcome back, {acc['display_name']}!")


def render_auth_sidebar():
    """Optional account: guests can use the app, but nothing is saved for them."""
    if logged_in():
        st.markdown(
            f"<div class='user-chip'>👤 Signed in as <b>{escape(st.session_state.display_name)}</b></div>",
            unsafe_allow_html=True,
        )
        if st.button("🚪 Logout"):
            logout()
        return

    st.markdown(
        "<div class='user-chip'>👤 Browsing as <b>Guest</b><br>"
        "<span class='small-muted'>Nothing you view is saved. Log in to keep your library, "
        "ratings and history.</span></div>",
        unsafe_allow_html=True,
    )
    with st.expander("🔑 Login / Create account", expanded=st.session_state.get("auth_open", False)):
        tab_login, tab_new = st.tabs(["Login", "Create account"])
        with tab_login:
            n1 = st.text_input("Full name", key="login_name", placeholder="e.g. Ravi Shankar Kumar")
            d1 = dob_input("Date of birth", "login_dob")
            if st.button("Login", key="login_btn"):
                handle_auth(n1, d1, create=False)
        with tab_new:
            n2 = st.text_input("Full name", key="new_name", placeholder="e.g. Ravi Shankar Kumar")
            d2 = dob_input("Date of birth", "new_dob")
            st.caption("Remember these two details. You need both every time you log in.")
            if st.button("Create account", key="create_btn"):
                handle_auth(n2, d2, create=True)


def require_login(feature: str):
    """Stops the page for guests with a friendly note."""
    if logged_in():
        return
    st.info(
        f"🔒 {feature} is available after you log in. Open **🔑 Login / Create account** "
        "in the sidebar. If you stay as a guest, nothing is saved."
    )
    footer()
    st.stop()


# SIDEBAR
with st.sidebar:
    st.markdown("## 🎬 Menu")

    render_auth_sidebar()

    lib_count = len(lib_list())

    if st.button("🏠 Home"):
        goto_home()
    if st.button(f"📚 My Library ({lib_count})" if logged_in() else "📚 My Library 🔒"):
        _go("library")
    if st.button("📊 My Stats" if logged_in() else "📊 My Stats 🔒"):
        _go("stats")
    if st.button("🧠 About Project"):
        _go("about")
    if st.button("🎲 Surprise Me"):
        pool, _err = api_get_json("/home", params={"category": "popular", "limit": 24})
        if pool:
            pick = random.choice(pool)
            if pick.get("tmdb_id"):
                goto_details(pick["tmdb_id"])
        else:
            st.warning("Could not pick a movie right now.")

    st.markdown("---")
    st.markdown("### 🏠 Home Feed (only home)")
    home_category = st.selectbox(
        "Category",
        ["trending", "popular", "top_rated", "now_playing", "upcoming"],
        index=0,
    )
    grid_cols = st.slider("Grid columns", 4, 8, 6)

    st.markdown("---")
    theme = st.radio("🎨 Appearance", ["Auto", "Dark"], horizontal=True)
    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()

    st.markdown(dev_card_html(), unsafe_allow_html=True)

if theme == "Dark":
    st.markdown(DARK_CSS, unsafe_allow_html=True)

_welcome = st.session_state.pop("welcome", None)
if _welcome:
    toast(_welcome)

if st.session_state.last_category != home_category:
    st.session_state.last_category = home_category
    st.session_state.home_limit = HOME_PAGE_SIZE * 2

# HEADER
if logged_in():
    who = f"Signed in as <b>{escape(st.session_state.display_name)}</b>."
else:
    who = "Browsing as <b>Guest</b>. Log in from the sidebar to save your movies."
st.markdown(
    f"""
<div class='banner'>
  <h1>🎬 Movie Recommender</h1>
  <p>Search → open → rate &amp; save → get recommendations made for you. {who}</p>
  <div class='ml-pills'><span>TF-IDF Recommender</span><span>Genre Matching</span><span>Personalised For You</span></div>
</div>
""",
    unsafe_allow_html=True,
)

# VIEW: HOME
if st.session_state.view == "home":
    typed = st.text_input(
        "Search by movie title (keyword)",
        key="search_text",
        placeholder="Type: avenger, batman, love...  then press Enter",
    )

    # SEARCH MODE 
    if typed.strip():
        if len(typed.strip()) < 2:
            st.caption("Type at least 2 characters for suggestions.")
        else:
            with st.spinner("Searching... (the server may take a few seconds to wake up)"):
                data, err = api_get_json("/tmdb/search", params={"query": typed.strip()})

            if err or data is None:
                st.error(f"Search failed: {err}")
            else:
                suggestions, cards = parse_tmdb_search_to_cards(
                    data, typed.strip(), limit=24
                )

                if st.session_state.get("last_search_logged") != (me(), typed.strip().lower()):
                    search_add(typed)
                    st.session_state.last_search_logged = (me(), typed.strip().lower())

                if suggestions:
                    labels = ["-- Select a movie --"] + [s[0] for s in suggestions]
                    selected = st.selectbox("Suggestions", labels, index=0)

                    if selected != "-- Select a movie --":
                        label_to_id = {s[0]: s[1] for s in suggestions}
                        goto_details(label_to_id[selected])
                else:
                    st.info("No suggestions found. Try one of these keywords:")
                    keyword_chips(POPULAR_KEYWORDS[:6], "nores")

                with st.expander("⚙️ Filters & sorting"):
                    f1, f2 = st.columns(2)
                    with f1:
                        sort_mode = st.selectbox(
                            "Sort by", ["Relevance", "Top rated", "Newest first", "Title (A–Z)"]
                        )
                    with f2:
                        year_range = st.slider(
                            "Release year", YEAR_MIN, YEAR_MAX, (YEAR_MIN, YEAR_MAX)
                        )

                shown = sort_cards(filter_by_year(cards, year_range), sort_mode)
                section_title(f"Results ({len(shown)})")
                if not shown:
                    st.info("No movies match these filters. Try widening the year range.")
                poster_grid(shown, cols=grid_cols, key_prefix="search_results")

        footer()
        st.stop()

    # KEYWORD HELPERS 
    history = search_recent()
    if history:
        h1, h2 = st.columns([5, 1])
        with h1:
            st.markdown("<div class='kw-label'>🕘 Your recent searches</div>", unsafe_allow_html=True)
        with h2:
            if st.button("Clear", key="chip_clear_history"):
                search_clear()
                st.rerun()
        keyword_chips(history, "hist")

    st.markdown("<div class='kw-label'>🔥 Popular keywords</div>", unsafe_allow_html=True)
    keyword_chips(POPULAR_KEYWORDS, "pop")

    # FOR YOU
    if lib_count:
        with st.spinner("Picking movies for you..."):
            for_you = get_for_you(limit=grid_cols * 2)
        if for_you:
            section_title("✨ Recommended For You")
            poster_grid(for_you, cols=grid_cols, key_prefix="for_you")

    # RECENTLY VIEWED 
    recent_cards = recent_list()
    if recent_cards:
        section_title("🕘 Recently Viewed")
        poster_grid(recent_cards[:grid_cols], cols=grid_cols, key_prefix="recent")

    # HOME FEED 
    section_title(f"🏠 Home — {home_category.replace('_', ' ').title()}")

    limit = min(st.session_state.home_limit, HOME_MAX)
    with st.spinner("Loading movies..."):
        home_cards, err = api_get_json(
            "/home", params={"category": home_category, "limit": limit}
        )
    if err or not home_cards:
        st.error(f"Home feed failed: {err or 'Unknown error'}")
        footer()
        st.stop()

    poster_grid(
        home_cards,
        cols=grid_cols,
        key_prefix="home_feed",
        show_rank=(home_category in ("trending", "popular", "top_rated")),
    )

    if limit < HOME_MAX and len(home_cards) >= limit:
        _l, mid, _r = st.columns([2, 1, 2])
        with mid:
            if st.button("⬇️ Load more", key="load_more"):
                st.session_state.home_limit = limit + HOME_PAGE_SIZE
                st.rerun()

    footer()

# VIEW: LIBRARY

elif st.session_state.view == "library":
    a, b = st.columns([3, 1])
    with a:
        st.markdown("### 📚 My Library")
    with b:
        if st.button("← Back to Home"):
            goto_home()

    require_login("My Library")
    sort_lib = st.selectbox("Sort by", list(ORDERS.keys()))
    rows = lib_list(sort_lib)

    if not rows:
        st.info("Your library is empty. Open a movie and choose “To Watch” or “Watched”.")
    else:
        to_watch = [r for r in rows if r["status"] == "to_watch"]
        watched = [r for r in rows if r["status"] == "watched"]
        tab_all, tab_tw, tab_w = st.tabs(
            [f"All ({len(rows)})", f"To Watch ({len(to_watch)})", f"Watched ({len(watched)})"]
        )
        with tab_all:
            poster_grid(rows_to_cards(rows), cols=grid_cols, key_prefix="lib_all")
        with tab_tw:
            poster_grid(rows_to_cards(to_watch), cols=grid_cols, key_prefix="lib_tw")
        with tab_w:
            poster_grid(rows_to_cards(watched), cols=grid_cols, key_prefix="lib_w")

    section_title("Backup & restore")
    export_rows = [
        {
            "tmdb_id": r["tmdb_id"],
            "title": r["title"],
            "poster_url": r["poster_url"],
            "genres": r["genres"],
            "status": r["status"],
            "rating": r["rating"],
            "note": r["note"],
            "added_at": r["added_at"],
        }
        for r in rows
    ]
    buf = io.StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=["tmdb_id", "title", "poster_url", "genres", "status", "rating", "note", "added_at"],
    )
    w.writeheader()
    w.writerows(export_rows)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "📥 Download CSV", data=buf.getvalue(), file_name=f"{file_slug()}_library.csv", mime="text/csv"
        )
    with c2:
        st.download_button(
            "📥 Download JSON",
            data=json.dumps(export_rows, indent=2),
            file_name=f"{file_slug()}_library.json",
            mime="application/json",
        )
    with c3:
        if st.button("🗑️ Clear library"):
            st.session_state.confirm_clear = True

    if st.session_state.get("confirm_clear"):
        st.warning("This removes every saved movie, rating and note for this profile.")
        y, n = st.columns(2)
        with y:
            if st.button("Yes, clear everything"):
                lib_clear()
                st.session_state.confirm_clear = False
                st.rerun()
        with n:
            if st.button("Cancel"):
                st.session_state.confirm_clear = False
                st.rerun()

    up = st.file_uploader("Restore from a JSON backup", type=["json"])
    if up is not None and st.button("Import backup"):
        try:
            items = json.load(up)
            if not isinstance(items, list):
                raise ValueError("The file must contain a list of movies.")
            n_imp = lib_import(items)
            toast(f"Imported {n_imp} movie(s)")
            st.rerun()
        except Exception as e:
            st.error(f"Import failed: {e}")

    section_title("Account")
    if st.button("🗑️ Delete my account", key="del_acc"):
        st.session_state.confirm_delete = True
    if st.session_state.get("confirm_delete"):
        st.warning(
            "This permanently deletes your account, library, ratings, notes and history."
        )
        dy, dn = st.columns(2)
        with dy:
            if st.button("Yes, delete my account", key="del_yes"):
                account_delete()
                logout()
        with dn:
            if st.button("Cancel", key="del_no"):
                st.session_state.confirm_delete = False
                st.rerun()

    footer()


# VIEW: STATS
elif st.session_state.view == "stats":
    a, b = st.columns([3, 1])
    with a:
        st.markdown("### 📊 My Stats")
    with b:
        if st.button("← Back to Home"):
            goto_home()

    require_login("My Stats")
    rows = lib_list()
    if not rows:
        st.info("No data yet. Save and rate a few movies to see your stats.")
    else:
        watched = [r for r in rows if r["status"] == "watched"]
        rated = [r["rating"] for r in rows if r["rating"] > 0]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Saved movies", len(rows))
        m2.metric("Watched", len(watched))
        m3.metric("To watch", len(rows) - len(watched))
        m4.metric("Average rating", f"{sum(rated) / len(rated):.1f} ★" if rated else "-")

        left, right = st.columns(2)
        with left:
            section_title("Favourite genres")
            counts = {}
            for r in rows:
                for g in (r["genres"] or "").split(", "):
                    if g.strip():
                        counts[g.strip()] = counts.get(g.strip(), 0) + 1
            if counts:
                df = pd.DataFrame(
                    sorted(counts.items(), key=lambda x: -x[1]), columns=["Genre", "Movies"]
                ).set_index("Genre")
                st.bar_chart(df)
            else:
                st.caption("Genres appear after you save movies from their details page.")
        with right:
            section_title("Your ratings")
            if rated:
                dist = {("★" * n): rated.count(n) for n in range(1, 6)}
                st.bar_chart(pd.DataFrame({"Movies": dist}))
            else:
                st.caption("Rate a movie to see the breakdown.")

        top = sorted([r for r in rows if r["rating"] > 0], key=lambda r: -r["rating"])[:5]
        if top:
            section_title("Top rated by you")
            poster_grid(rows_to_cards(top), cols=min(grid_cols, 5), key_prefix="stats_top")

    footer()

# VIEW: ABOUT

elif st.session_state.view == "about":
    a, b = st.columns([3, 1])
    with a:
        st.markdown("### 🧠 About this project")
    with b:
        if st.button("← Back to Home"):
            goto_home()

    st.markdown(
        "<div class='about-hero'>"
        f"<div class='art'>{neural_svg(360, 220, (4, 6, 6, 3))}</div>"
        "<div class='text'>"
        "<div class='label'>Developed by</div>"
        f"<div class='name'>{DEVELOPER}</div>"
        f"<span class='role'>{DEVELOPER_ROLE}</span>"
        "<div class='desc'>An end-to-end movie recommendation system. A FastAPI backend serves "
        "TMDB movie data and ML-based recommendations, and this Streamlit app turns them into "
        "a personal movie experience.</div>"
        "<div class='tags'><span>Python</span><span>FastAPI</span><span>Streamlit</span>"
        "<span>TF-IDF</span><span>Recommender Systems</span><span>SQLite</span></div>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    section_title("How the recommendations work")
    steps = [
        ("Movie data", "Movie details, genres and overviews are fetched from the TMDB API."),
        ("TF-IDF model", "The text of each movie is converted into TF-IDF features so similar stories can be compared."),
        ("Similar movies", "The backend returns the closest movies for a title, plus more movies from the same genres."),
        ("Made for you", "This app combines those results for the movies you rated 4★ or higher, and skips what you already saved."),
    ]
    cols = st.columns(4)
    for i, (ttl, txt) in enumerate(steps):
        with cols[i]:
            st.markdown(
                f"<div class='pipe'><span class='num'>{i + 1}</span>"
                f"<div class='ttl'>{escape(ttl)}</div><div class='txt'>{escape(txt)}</div></div>",
                unsafe_allow_html=True,
            )

    section_title("What you can do here")
    st.markdown(
        "- Search by keyword and open any movie for details and similar picks.\n"
        "- Save movies, mark them watched, rate them and add notes.\n"
        "- Get a **Recommended For You** row that improves as you rate more movies.\n"
        "- Check your own stats, and back up your library as CSV or JSON."
    )

    footer()

# VIEW: DETAILS

elif st.session_state.view == "details":
    tmdb_id = st.session_state.selected_tmdb_id
    if not tmdb_id:
        st.warning("No movie selected.")
        if st.button("← Back to Home"):
            goto_home()
        st.stop()

    a, b = st.columns([3, 1])
    with a:
        st.markdown("### 📄 Movie Details")
    with b:
        if st.button("← Back to Home"):
            goto_home()

    with st.spinner("Loading movie..."):
        data, err = api_get_json(f"/movie/id/{tmdb_id}")
    if err or not data:
        st.error(f"Could not load details: {err or 'Unknown error'}")
        st.stop()

    release = data.get("release_date") or "-"
    genre_names = [g["name"] for g in data.get("genres", []) if g.get("name")]
    movie_card = {
        "tmdb_id": int(tmdb_id),
        "title": data.get("title") or "Untitled",
        "poster_url": data.get("poster_url"),
        "genres": ", ".join(genre_names),
    }

    log_key = (me(), int(tmdb_id))
    if st.session_state.get("last_logged") != log_key:
        recent_add(movie_card)
        st.session_state.last_logged = log_key

    left, right = st.columns([1, 2.4], gap="large")

    with left:
        if data.get("poster_url"):
            show_image(data["poster_url"])
        else:
            st.markdown("<div class='no-poster'>No poster</div>", unsafe_allow_html=True)

    with right:
        rating = data.get("vote_average")
        runtime = data.get("runtime")
        tagline = (data.get("tagline") or "").strip()

        chips = ""
        if isinstance(rating, (int, float)) and rating > 0:
            chips += f"<span class='chip gold'>★ {rating:.1f}</span>"
        if isinstance(runtime, int) and runtime > 0:
            chips += f"<span class='chip grey'>⏱ {runtime // 60}h {runtime % 60}m</span>"
        for g in genre_names:
            chips += f"<span class='chip'>{escape(g)}</span>"

        tagline_html = (
            f"<div style='font-style:italic;opacity:0.8;margin-bottom:0.5rem'>“{escape(tagline)}”</div>"
            if tagline
            else ""
        )
        overview = escape(data.get("overview") or "No overview available.")

        st.markdown(
            f"""
<div class='card'>
  <h2 style='margin-top:0'>{escape(movie_card['title'])}</h2>
  {tagline_html}
  <div class='small-muted'>Release: {escape(release)}</div>
  <div class='small-muted' style='margin-bottom:0.6rem'>Genres: {escape(", ".join(genre_names) or "-")}</div>
  <div>{chips}</div>
  <hr style='opacity:0.25'>
  <h4>Overview</h4>
  <div style='line-height:1.7'>{overview}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        # My Library panel 
        st.markdown("#### 📚 My Library")
        if not logged_in():
            st.info("Log in from the sidebar (🔑 Login / Create account) to save this movie, rate it and add notes. As a guest, nothing is saved.")
        else:
            lib = lib_get(tmdb_id)
            rev = lib["rev"] if lib else 0
            status_now = (
                "Not saved"
                if not lib
                else ("Watched" if lib["status"] == "watched" else "To Watch")
            )
            status_options = ["Not saved", "To Watch", "Watched"]
            status_map = {"Not saved": None, "To Watch": "to_watch", "Watched": "watched"}

            def on_status_change(movie, key):
                val = status_map[st.session_state[key]]
                if val is None:
                    lib_delete(movie["tmdb_id"])
                    toast("Removed from library")
                elif lib_get(movie["tmdb_id"]):
                    lib_update(movie["tmdb_id"], status=val)
                    toast("Status updated")
                else:
                    lib_save(movie, val)
                    toast("Saved to library")

            skey = f"status_{tmdb_id}_{rev}_{status_now}"
            st.radio(
                "Status",
                status_options,
                index=status_options.index(status_now),
                horizontal=True,
                key=skey,
                on_change=on_status_change,
                args=(movie_card, skey),
            )

            if lib:

                def on_rating_change(mid, key, current_status):
                    r = int(st.session_state[key])
                    lib_update(mid, rating=r, status="watched" if r > 0 else current_status)
                    toast("Rating saved")

                rkey = f"rate_{tmdb_id}_{rev}"
                st.select_slider(
                    "My rating",
                    options=[0, 1, 2, 3, 4, 5],
                    value=int(lib["rating"]),
                    format_func=lambda x: "No rating" if x == 0 else "★" * x,
                    key=rkey,
                    on_change=on_rating_change,
                    args=(tmdb_id, rkey, lib["status"]),
                )

                nkey = f"note_{tmdb_id}_{rev}"
                note_txt = st.text_area(
                    "My note",
                    value=lib["note"] or "",
                    key=nkey,
                    placeholder="Write what you liked, who to watch it with...",
                    height=90,
                )
                if st.button("💾 Save note", key=f"savenote_{tmdb_id}_{rev}"):
                    lib_update(tmdb_id, note=note_txt)
                    toast("Note saved")
                    st.rerun()
            else:
                st.caption("Save this movie to rate it and add a note.")

        # ---- Links ----
        st.markdown("")
        year = release[:4] if release != "-" else ""
        t = quote_plus(f"{movie_card['title']} {year} official trailer".strip())
        g = quote_plus(f"{movie_card['title']} {year} movie".strip())
        b1, b2 = st.columns(2)
        with b1:
            st.markdown(
                f"<a class='linkbtn' target='_blank' rel='noopener' "
                f"href='https://www.youtube.com/results?search_query={t}'>▶ Watch Trailer</a>",
                unsafe_allow_html=True,
            )
        with b2:
            st.markdown(
                f"<a class='linkbtn' target='_blank' rel='noopener' "
                f"href='https://www.google.com/search?q={g}'>🔍 Search on Google</a>",
                unsafe_allow_html=True,
            )

        with st.expander("🔗 Share this movie"):
            st.code(f"?view=details&id={tmdb_id}")
            st.caption("Add this at the end of your app link to open this movie directly.")

    if data.get("backdrop_url"):
        section_title("Backdrop")
        show_image(data["backdrop_url"])

    st.divider()
    st.markdown("### ✅ Recommendations")

    title = movie_card["title"].strip()
    if title:
        with st.spinner("Finding similar movies..."):
            bundle, err2 = api_get_json(
                "/movie/search",
                params={"query": title, "tfidf_top_n": 12, "genre_limit": 12},
            )

        if not err2 and bundle:
            st.markdown("#### 🔎 Similar Movies (TF-IDF)")
            poster_grid(
                to_cards_from_tfidf_items(bundle.get("tfidf_recommendations")),
                cols=grid_cols,
                key_prefix="details_tfidf",
            )

            st.markdown("#### 🎭 More Like This (Genre)")
            poster_grid(
                bundle.get("genre_recommendations", []),
                cols=grid_cols,
                key_prefix="details_genre",
            )
        else:
            st.info("Showing Genre recommendations (fallback).")
            genre_only, err3 = api_get_json(
                "/recommend/genre", params={"tmdb_id": tmdb_id, "limit": 18}
            )
            if not err3 and genre_only:
                poster_grid(
                    genre_only, cols=grid_cols, key_prefix="details_genre_fallback"
                )
            else:
                st.warning("No recommendations available right now.")
    else:
        st.warning("No title available to compute recommendations.")

    footer()