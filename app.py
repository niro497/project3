from flask import Flask, render_template
import psycopg2
import os

DB_PASS = os.environ.get("PGPASSWORD")
DB_NAME="k29photo"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"

conn = psycopg2.connect(
                        dbname=DB_NAME,
                        user=DB_USER,
                        password=DB_PASS,
                        host=DB_HOST,
                        port=DB_PORT,
                        )

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/users")
def users():

    return render_template("users.html")

if __name__ == "__main__":
    app.run()