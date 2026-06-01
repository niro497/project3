from flask import Flask, render_template
import psycopg2
import psycopg2.extras

app = Flask(__name__)

def get_db_connection():
    return psycopg2.connect(
        dbname="k29photo",
        user="postgres",
        password="than252",
        host="localhost",
        port="5432",
        cursor_factory=psycopg2.extras.RealDictCursor
    )

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/users")
def users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, first_name, last_name, email FROM users;")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("users.html", users=rows)

if __name__ == "__main__":
    app.run(debug=True, port = 5001)