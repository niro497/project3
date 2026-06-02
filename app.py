from flask import Flask, render_template, request, flash, redirect, url_for
import psycopg2
import os

app = Flask(__name__)
app.secret_key = "dev-secret-key" # for flashes

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

@app.route("/register", methods=["GET", "POST"]) 
def register():
    
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        dob = request.form['dob']
        password = request.form['password'] #TODO: HASH THIS
        
        cursor = conn.cursor()


        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,));
        if cursor.fetchone():
            flash("This email is being used! Try another one.", "error")
            cursor.close()
            return render_template("register.html")
        
        else:
            insertcomm = """ 
                        INSERT INTO users (first_name, last_name, email, birthdate, password)
                        VALUES (%s, %s, %s, %s, %s)
                        """
            insertdata = (first_name, last_name, email, dob if dob else None, password,)
            cursor.execute(insertcomm, insertdata)
            conn.commit()
            cursor.close()
            return redirect(url_for("register_success"))

    return render_template("register.html")

@app.route("/register-success")
def register_success():
    return render_template("register-success.html")

@app.route("/users")
def users():
    
    return render_template("users.html")

if __name__ == "__main__":
    app.run()