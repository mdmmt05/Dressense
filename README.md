# 👔 Dressense

**A smart, adaptive outfit generator that learns your personal style.**

Dressense is a Python CLI application that suggests daily outfits from your wardrobe. It uses a multi-criteria scoring engine to find the best combinations — and gets smarter over time by learning from your feedback.

---

## 💡 Why Dressense?

I've never been great at putting together outfits. For most of my life I relied on my mum when I was younger, and later on my brother — who has a much better eye for style than I do — to tell me what to wear.

At some point, I got tired of that dependency. So I did what any self-respecting developer would do: I turned one of my strengths into a solution for one of my weaknesses. Dressense is the result — a personal project built out of genuine need, not just to have something to show.

---

## ✨ Features

- **Smart outfit generation** — Combines hard constraints (valid layering, category uniqueness, active garments only, formality coherence) with soft scoring (color harmony, pattern coherence, formality alignment, simplicity bias) to surface the best possible outfit from your wardrobe.
- **Adaptive Preference Engine** — When you dislike an outfit, Dressense doesn't just move on. It adjusts its internal scoring weights and applies penalties to specific garment combinations so it won't make the same mistake twice. Positive ratings gradually heal those penalties over time.
- **Outfit history tracking** — Mark outfits as worn. Dressense tracks how recently each garment was used and penalizes recently-worn items to promote variety.
- **CIELab color science** — Colors are evaluated in perceptual color space (CIELab), not just by name, making harmony scoring more accurate and nuanced.
- **Full wardrobe management** — Add, remove, activate, deactivate, and inspect garments with detailed metadata (warmth, formality, pattern, season tags, occasion tags, and more).
- **SQLite persistence** — Your wardrobe and all learned preferences are stored locally in a lightweight SQLite database.

---

## 🛠️ Tech Stack

- **Python 3.9+**
- [`colorspacious`](https://pypi.org/project/colorspacious/) — CIELab color space conversion
- [`webcolors`](https://pypi.org/project/webcolors/) — CSS color name resolution
- `sqlite3` — built-in Python database

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/mdmmt05/dressense.git
cd dressense
```

### 2. Install dependencies

```bash
pip install colorspacious webcolors
```

### 3. Run

```bash
python main.py
```

---

## 🧠 How It Works

### Outfit Generation

The `OutfitGenerator` evaluates all valid garment combinations using a two-pass system:

**Hard constraints** eliminate invalid outfits entirely:
- Correct layering (base → mid → outer)
- One garment per category
- Active garments only
- Formality coherence across the full outfit

**Soft constraints** score the remaining candidates:
- Color harmony (via CIELab distance)
- Pattern coherence (based on visible garments only — what's covered doesn't count)
- Formality alignment to a learned target
- Neutral color balance (penalty for all-neutral outfits, bonus for color diversity)
- Simplicity bias (penalizes unnecessary layers)
- Recently-worn penalty (promotes wardrobe variety)
- Learned pair penalties (discourages disliked combinations)

The top candidates are pooled and one is selected at random, so you're not always shown the exact same outfit.

### Adaptive Preference Engine

Every time you rate an outfit negatively, Dressense adjusts its behavior based on the specific reason you provide:

| Reason | Effect |
|---|---|
| Too formal | Shifts `target_formality` down |
| Too casual | Shifts `target_formality` up |
| Too many neutrals | Lowers the neutral saturation threshold |
| Boring | Increases color weight |
| Too flashy | Decreases color weight |
| Bad layering | Adjusts pattern weight |
| Colors clash | Applies heavy pair penalties to all garment pairs in the outfit |
| Don't like the combination | Applies medium pair penalties to all garment pairs |

Positive ratings gradually reduce existing pair penalties, giving previously-penalized combinations a second chance over time.

All weights and penalties are persisted to SQLite and reloaded at startup — so the system remembers your preferences across sessions.

### Database Schema

Dressense uses five tables:

- `garment` — your wardrobe items with full metadata
- `feedback` — history of all ratings with reasons
- `weights` — adaptive scoring parameters (with min/max bounds and defaults)
- `pair_penalties` — learned penalties for specific garment combinations
- `outfit_history` — log of outfits marked as worn, used for recency scoring

---

## 🗂️ Project Structure

```
dressense/
├── main.py             # CLI interface and main loop
├── db_manager.py       # SQLite abstraction, garment CRUD, weights & penalties management
├── outfit_engine.py    # Outfit generation, scoring, and debug tools
├── feedback_engine.py  # Adaptive Preference Engine
└── color_utils.py      # Color conversion utilities (CSS → RGB → CIELab)
```

---

## 🗺️ Roadmap

Dressense is under active development. Here's where we're headed:

| Phase | Status | Description |
|---|---|---|
| **Phase 1** — Core engine | ✅ Complete | Wardrobe management, outfit generation, scoring |
| **Phase 2** — Adaptive Preference Engine | ✅ Complete | Feedback-driven weight adjustment and pair penalties |
| **Phase 3** — Context awareness | 🔜 Planned | Season and occasion filtering (no summer outfits in winter, no casual outfits for formal events) |
| **Phase 4** — Quality of life | 🔜 Planned | "Swap only one item", generate multiple outfits at once, garment usage reports |
| **Phase 5** — Machine learning | 🔜 Planned | Convert accumulated feedback into a training dataset; lightweight ML model for scoring |

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests. Since the project is still in active early development, it's a good idea to open an issue first to discuss what you'd like to change.