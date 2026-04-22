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

    cur.execute("DROP TABLE IF EXISTS participants")
    cur.execute("""
    CREATE TABLE participants (
        id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        affiliation TEXT,
        role TEXT,
        lunch TEXT,
        dinner TEXT,
        excursion TEXT,
        checked_in INTEGER DEFAULT 0,
        checkin_time TEXT
    )
    """)

    conn.commit()
    conn.close()


def import_csv():
    conn = get_connection()
    cur = conn.cursor()

    df = pd.read_csv(CSV_PATH).fillna("")

    for _, row in df.iterrows():
        cur.execute("""
            INSERT OR REPLACE INTO participants
            (id, name, email, affiliation, role, lunch, dinner, excursion, checked_in, checkin_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(row["id"]),
            str(row["name"]),
            str(row["email"]),
            str(row["affiliation"]),
            str(row["role"]),
            str(row["lunch"]),
            str(row["dinner"]),
            str(row["excursion"]),
            0,
            None
        ))

    conn.commit()
    conn.close()

def get_participation_category(person):
    dinner = str(person["dinner"]).strip()
    excursion = str(person["excursion"]).strip()

    dinner_yes = dinner in ["参加", "Yes", "yes", "YES"]
    excursion_yes = excursion in ["参加", "Yes", "yes", "YES"]

    if not dinner_yes and not excursion_yes:
        return {
            "label": "SESSION ONLY",
            "label_ja": "セッションのみ",
            "color": "#d9d9d9"
        }
    elif dinner_yes and not excursion_yes:
        return {
            "label": "SESSION + DINNER",
            "label_ja": "セッション＋レセプション",
            "color": "#ffe699"
        }
    elif dinner_yes and excursion_yes:
        return {
            "label": "SESSION + DINNER + EXCURSION",
            "label_ja": "セッション＋レセプション＋エクスカーション",
            "color": "#a9d18e"
        }
    elif not dinner_yes and excursion_yes:
        return {
            "label": "SESSION + EXCURSION",
            "label_ja": "セッション＋エクスカーション",
            "color": "#9dc3e6"
        }

@app.route("/", methods=["GET", "POST"])
def checkin():
    message = None
    person_info = None
    category_info = None
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
            person_info = person
            category_info = get_participation_category(person)

        else:
            from datetime import datetime, timedelta
            checkin_time = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("""
                UPDATE participants
                SET checked_in = 1, checkin_time = ?
                WHERE id = ?
            """, (checkin_time, person["id"]))
            conn.commit()

            cur.execute("SELECT * FROM participants WHERE id = ?", (person["id"],))
            updated_person = cur.fetchone()

            message = {
                "ja": f"{updated_person['name']} さんのチェックインが完了しました。",
                "en": f"Check-in completed for {updated_person['name']}."
            }[language]
            person_info = updated_person
            category_info = get_participation_category(updated_person)

        conn.close()

    return render_template(
    "checkin.html",
    message=message,
    language=language,
    person_info=person_info,
    category_info=category_info
)


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
    import_csv()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
