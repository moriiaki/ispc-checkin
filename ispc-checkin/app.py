from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)

DB_PATH = "participants.db"
CSV_PATH = "participants.csv"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        affiliation TEXT,
        role TEXT,
        lunch TEXT,
        dinnerTEXT,
        excursion TEXT,
        checked_in INTEGER DEFAULT 0,
        checkin_time TEXT
    )
    """)

    conn.commit()
    conn.close()

def import_csv_if_needed():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM participants")
    count = cur.fetchone()[0]

    if count == 0 and os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH).fillna("")
        for _, row in df.iterrows():
            cur.execute("""
                INSERT OR REPLACE INTO participants (id, name, email, affiliation, role, lunch, dinner, excursion, checked_in, checkin_time)
                VALUES (?, ?, ?, ?, 0, NULL)
            """, (
                str(row["id"]),
                str(row["name"]),
                str(row["email"]),
                str(row["affiliation"]),
                str(row["role"]),
                str(row["lunch"]),
                str(row["dinner"]),
                str(row["excursion"])
            ))
        conn.commit()

    conn.close()

@app.route("/", methods=["GET", "POST"])
def checkin():
    message = None
    language = request.args.get("lang", "ja")

    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM participants
            WHERE id = ?
               OR email = ?
               OR name LIKE ?
            LIMIT 1
        """, (keyword, keyword, f"%{keyword}%"))

        person = cur.fetchone()

        if person is None:
            message = {
                "ja": "該当する参加者が見つかりませんでした。",
                "en": "Participant not found."
            }[language]
        elif person["checked_in"] == 1:
            message = {
                "ja": f"{person['name']} さんは既にチェックイン済みです。",
                "en": f"{person['name']} has already checked in."
            }[language]
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("""
                UPDATE participants
                SET checked_in = 1, checkin_time = ?
                WHERE id = ?
            """, (now, person["id"]))
            conn.commit()
            message = {
                "ja": f"{person['name']} さんのチェックインが完了しました。",
                "en": f"Check-in completed for {person['name']}."
            }[language]

        conn.close()

    return render_template("checkin.html", message=message, language=language)

@app.route("/admin")
def admin():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM participants")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM participants WHERE checked_in = 1")
    checked = cur.fetchone()[0]

    cur.execute("SELECT * FROM participants ORDER BY checked_in DESC, name ASC")
    participants = cur.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        total=total,
        checked=checked,
        unchecked=total - checked,
        participants=participants
    )

@app.route("/reset")
def reset():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE participants SET checked_in = 0, checkin_time = NULL")
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

if __name__ == "__main__":
    init_db()
    import_csv_if_needed()
    app.run(host="0.0.0.0", port=5000, debug=True)
