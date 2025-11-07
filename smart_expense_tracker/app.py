from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import pandas as pd
from datetime import datetime

app = Flask(__name__)

# ---------------- CREATE DATABASE + AUTO FIX ----------------
def init_db():
    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        category TEXT,
                        amount REAL,
                        description TEXT
                    )''')

    # ✅ Check if "month" column exists
    cursor.execute("PRAGMA table_info(expenses)")
    columns = [col[1] for col in cursor.fetchall()]
    if "month" not in columns:
        print("🛠 Adding missing column 'month'...")
        cursor.execute("ALTER TABLE expenses ADD COLUMN month TEXT")

    conn.commit()
    conn.close()

init_db()

# ---------------- AI SUGGESTION ----------------
def ai_suggestion(df):
    if df.empty:
        return "No data available for analysis."
    category_data = df.groupby("category")["amount"].sum()
    top_category = category_data.idxmax()
    top_amount = category_data.max()
    total = category_data.sum()
    percent = (top_amount / total) * 100

    if percent > 40:
        return f"⚠️ You are spending {percent:.1f}% of your money on '{top_category}'. Try reducing it next month."
    elif percent > 25:
        return f"💡 '{top_category}' is your major expense. Keep an eye on it!"
    else:
        return "✅ Your spending is well balanced across categories!"

# ---------------- ROUTES ----------------
@app.route('/')
def index():
    conn = sqlite3.connect("expenses.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM expenses ORDER BY date DESC")
    data = cur.fetchall()
    conn.close()
    return render_template("index.html", data=data)

@app.route('/add', methods=['POST'])
def add():
    date = request.form['date']
    category = request.form['category']
    amount = request.form['amount']
    description = request.form['description']

    try:
        month = datetime.strptime(date, "%Y-%m-%d").strftime("%b %Y")
    except:
        month = "Unknown"

    conn = sqlite3.connect("expenses.db")
    conn.execute("INSERT INTO expenses (date, category, amount, description, month) VALUES (?, ?, ?, ?, ?)",
                 (date, category, amount, description, month))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/new_dashboard')
def new_dashboard():
    conn = sqlite3.connect("expenses.db")
    df = pd.read_sql_query("SELECT * FROM expenses", conn)
    conn.close()

    if df.empty:
        monthly_labels = []
        monthly_values = []
        category_labels = []
        category_values = []
        suggestion = "No data available yet!"
    else:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        suggestion = ai_suggestion(df)
        category_data = df.groupby("category")["amount"].sum()
        category_labels = category_data.index.tolist()
        category_values = category_data.values.tolist()
        df['month'] = df['date'].dt.strftime('%b %Y')
        monthly_data = df.groupby("month")["amount"].sum().sort_index()
        monthly_labels = monthly_data.index.tolist()
        monthly_values = monthly_data.values.tolist()

    return render_template("new_dashboard.html",
                           monthly_labels=monthly_labels,
                           monthly_values=monthly_values,
                           category_labels=category_labels,
                           category_values=category_values,
                           suggestion=suggestion)

    if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
