#!/usr/bin/env python3
"""Flask web server for the Stroop Task."""
import csv
import datetime as dt
import os
import random
import re
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)
DATA_DIR = Path(__file__).resolve().parent / "data"

COLORS = ["red", "green", "blue", "yellow"]


def sanitize(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s).strip("_") or "anon"


def build_trials(n, seed=None):
    rng = random.Random(seed)
    n_cong = n // 2
    n_inc = n - n_cong
    trials = []
    for _ in range(n_cong):
        c = rng.choice(COLORS)
        trials.append({"word": c, "ink": c, "congruent": True})
    for _ in range(n_inc):
        word = rng.choice(COLORS)
        ink = rng.choice([c for c in COLORS if c != word])
        trials.append({"word": word, "ink": ink, "congruent": False})
    rng.shuffle(trials)
    return trials


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/trials", methods=["POST"])
def get_trials():
    data = request.get_json()
    n = int(data.get("n_trials", 30))
    if n <= 0:
        n = 30
    if n % 2 != 0:
        n += 1
    trials = build_trials(n)
    return jsonify({"trials": trials, "n_trials": n})


@app.route("/api/save", methods=["POST"])
def save_results():
    data = request.get_json()
    pid = sanitize(str(data.get("pid", "anon")))
    name = sanitize(str(data.get("name", "anon")))
    results = data.get("results", [])

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{pid}_{name}_{stamp}.csv"
    path = DATA_DIR / filename

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["participant_id", "participant_name", "timestamp",
                    "trial", "word", "ink", "congruent",
                    "response", "correct", "rt_ms"])
        for r in results:
            w.writerow([
                pid, name, r.get("timestamp", ""),
                r.get("trial", ""), r.get("word", ""), r.get("ink", ""),
                "yes" if r.get("congruent") else "no",
                r.get("response", ""),
                "yes" if r.get("correct") else "no",
                round(float(r.get("rt_ms", 0)), 1),
            ])

    try:
        os.chmod(path, 0o644)
        os.chmod(DATA_DIR, 0o755)
    except OSError:
        pass

    return jsonify({"success": True, "filename": filename})


@app.route("/data/<path:filename>")
def download_data(filename):
    return send_from_directory(DATA_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5111, debug=False)
