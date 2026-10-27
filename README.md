# 🎬 Movie Recommender

An end-to-end movie recommendation web app. A **Streamlit** frontend talks to a **FastAPI** backend that serves TMDB movie data and **TF-IDF based recommendations**. Users can search movies, save them to a personal library, rate them, and get a personalised **"Recommended For You"** row.

> Developed by **Ravi Shankar Kumar** (AI/ML Engineer)

---

## ✨ Features

- 🔍 **Keyword search** with suggestions, sorting (relevance, top rated, newest, A-Z) and release-year filter
- 🏠 **Home feed** with 5 categories: trending, popular, top rated, now playing, upcoming (with "Load more")
- 📄 **Movie details**: poster, tagline, overview, genres, runtime, rating, backdrop, trailer and Google links
- 🔎 **Similar Movies (TF-IDF)** and 🎭 **More Like This (Genre)** on every details page
- ✨ **Recommended For You**: personalised from the movies you rated highly
- 📚 **My Library**: To Watch / Watched, 1-5 star rating, personal notes
- 📊 **My Stats**: saved/watched counts, average rating, favourite genres, rating chart
- 🕘 Recently viewed movies and recent search history
- 🎲 **Surprise Me** random movie button
- 💾 **Backup & restore** library as CSV / JSON
- 🔐 Account login with **name + date of birth** (guest mode also available)
- 🌗 Auto / Dark appearance, shareable links like `?view=details&id=123`

---

## 🧱 Tech Stack

| Part | Technology |
|------|------------|
| Frontend | Python, Streamlit, pandas, requests |
| Backend | FastAPI (hosted separately, e.g. on Render) |
| Movie data | TMDB API (through the backend) |
| ML | TF-IDF + cosine similarity (scikit-learn, NLTK), built in `main.ipynb` |
| Local storage | SQLite (`movie_app.db`) |

---

## 🏗️ Architecture

```
User (Browser)
      |
Streamlit Frontend (this repo)  <---->  SQLite (accounts, library, history)
      |
      |  HTTP GET (requests)
      v
FastAPI Backend (API_BASE)
      |
      +--> TMDB API (movie data)
      +--> TF-IDF model files (.pkl) made by main.ipynb
```

The **Streamlit frontend** (`app.py`) only calls the backend API and shows the results. The ML model is trained in **`main.ipynb`**, which saves the `.pkl` files used by the backend.

---

## 🔌 Backend APIs used

All endpoints are `GET`.

| Endpoint | Params | Used for |
|----------|--------|----------|
| `/home` | `category`, `limit` | Home feed, Surprise Me |
| `/tmdb/search` | `query` | Search box suggestions and results |
| `/movie/id/{tmdb_id}` | - | Movie details page |
| `/movie/search` | `query`, `tfidf_top_n`, `genre_limit` | TF-IDF + genre recommendations (details page and For You) |
| `/recommend/genre` | `tmdb_id`, `limit` | Genre-only fallback recommendations |

The app retries failed requests 3 times (to handle cold starts on free hosting) and caches responses for 60 seconds.

---

## 🧠 How recommendations work

1. Movie data (details, genres, overview) comes from TMDB.
2. The movie text (overview + genres + tagline) is cleaned and converted into **TF-IDF** features in `main.ipynb` (see the next section), so similar stories can be compared with cosine similarity.
3. For a title, the backend returns the closest movies (`tfidf_recommendations`) plus more movies from the same genres (`genre_recommendations`).
4. **Recommended For You** (in this app): takes up to 3 of your top-rated movies (4★ and above, else watched, else saved), calls `/movie/search` for each, gives TF-IDF results weight 2 and genre results weight 1, adds up the scores, removes movies you already saved, and shows the top results.

---

## 🤖 ML Model (`main.ipynb`)

The notebook builds the content-based recommender and saves the model files as `.pkl`. It was written to run in **Google Colab** (the CSV is read from Google Drive; change the path if you run it elsewhere).

### Dataset

`movies_metadata.csv` (45,466 rows, 24 columns). Only these columns are kept: `title`, `overview`, `genres`, `tagline`, `vote_average`, `popularity`.

### Steps

1. **Load and clean**: remove duplicates, drop rows with no title, fill empty `overview` and `tagline` with empty text. After cleaning: **45,447 movies**.
2. **Genres**: the genres column is a text list like `[{'id': 16, 'name': 'Animation'}, ...]`. `ast.literal_eval` converts it, and only the names are kept (for example `Animation Comedy Family`).
3. **Make `tags`**: `tags = overview + genres + tagline`.
4. **Preprocess text** (`preprocess_text`): lowercase, remove punctuation and numbers, remove English stopwords (NLTK), lemmatize (WordNet).
5. **Title index**: `indices` is a pandas Series that maps a movie title to its row number.
6. **TF-IDF**: `TfidfVectorizer(max_features=50000, ngram_range=(1, 2), stop_words='english')` is fitted on `tags`. Result: a sparse matrix of shape **(45447, 50000)**.
7. **Recommend**: for a title, find its row, compute **cosine similarity** between that row and all other rows, sort high to low, and return the top N (default 20), skipping the movie itself.
8. **Save**: the four `.pkl` files below.

```python
def recommend(title, n=20):
    if title not in indices:
        return ["movie not found"]
    idx = indices[title]
    sim_score = cosine_similarity(tfidf_matrix[idx], tfidf_matrix).flatten()
    similar_idx = sim_score.argsort()[::-1][1:n+1]
    return df['title'].iloc[similar_idx]
```

Similarity is calculated on demand for one movie at a time. A full 45k x 45k similarity matrix is not stored, which keeps the files small.

### Saved `.pkl` files

| File | What it stores | Why it is needed |
|------|----------------|------------------|
| `tfidf_matrix.pkl` | Sparse TF-IDF matrix of all movies (45447 x 50000) | Used to compute cosine similarity |
| `indices.pkl` | Series: movie title -> row number | Quickly finds the row of a given title |
| `df.pkl` | Cleaned DataFrame (title, overview, genres, tagline, vote_average, popularity, tags) | Converts row numbers back to movie titles and details |
| `tfidf.pkl` | The fitted `TfidfVectorizer` | Transforms new text into the same TF-IDF space |

### Re-create the model files

1. Open `main.ipynb` in Google Colab (or Jupyter).
2. Set the CSV path in the second cell.
3. Run all cells. The four `.pkl` files are created at the end.
4. Place the `.pkl` files where the backend loads them from.

**Notebook libraries:** numpy, pandas, scikit-learn, nltk, seaborn, matplotlib.

---

## 🗄️ Database

SQLite file `movie_app.db` is created automatically on first run.

| Table | Purpose |
|-------|---------|
| `accounts` | Account id (hash), display name, created / last login |
| `library` | Saved movies with status, rating, note |
| `recent` | Recently viewed movies (max 12) |
| `searches` | Recent search terms (max 8) |

**Login:** the account id is a PBKDF2-HMAC-SHA256 hash of name + date of birth. The date of birth itself is never stored. After 5 wrong attempts login is locked for 60 seconds.

> ⚠️ Name + date of birth is a simple login meant for a personal/demo project. For a real production app use proper passwords or OAuth.

---

## 🚀 Run locally

**Requirements:** Python 3.10 or newer.

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd <your-repo-folder>

# 2. (Optional) create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

### Environment variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `API_BASE` | `https://movie-rec-466x.onrender.com` | Backend URL. For a local backend use `http://127.0.0.1:8000` |
| `DB_PATH` | `movie_app.db` | SQLite file path |
| `APP_SALT` | built-in demo value | Secret used when hashing logins. **Set your own long random value in production.** |

Example:

```bash
export API_BASE=http://127.0.0.1:8000
export APP_SALT=some-long-random-text
streamlit run app.py
```

> The free Render backend may take a few seconds to wake up on the first request.

---

## 📁 Project structure

```
.
├── app.py              # Streamlit frontend (all pages, DB, login)
├── main.ipynb          # ML notebook: data cleaning, TF-IDF, saves .pkl files
├── requirements.txt    # Python dependencies
├── README.md
└── movie_app.db        # created automatically at runtime (do not commit)
```

Tip: add `movie_app.db` to your `.gitignore` so user data is not uploaded.

---

## 👤 Author

**Ravi Shankar Kumar** - AI/ML Engineer
