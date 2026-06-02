from flask import Flask, render_template, request, flash, redirect, url_for, session
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

@app.route("/top-users") #method = "Get"
def top_users():
    cursor = conn.cursor()

    #υποθέτουμε οτι κανένας δεν έχει κανει comment στην φωτογραφία
    #του αφού το έχουμε τσεκάρει μέσω trigger
    #αν ολοι οι χρήστες εχουν βαθμολογία = 0 φαίνονται 10 τυχαίοι
    cursor.execute("""SELECT u.user_id, u.first_name, u.last_name, 
                          COALESCE(photo_counts.num_photos, 0) + COALESCE(comment_counts.num_comments, 0) AS contribution_score
                      FROM users u

                      LEFT JOIN (
                          SELECT a.user_id, COUNT(p.photo_id) AS num_photos
                          FROM albums a
                          JOIN photos p ON a.album_id = p.album_id
                          GROUP BY a.user_id
                      ) AS photo_counts ON u.user_id = photo_counts.user_id

                      LEFT JOIN (
                          SELECT c.user_id, COUNT(c.comment_id) AS num_comments
                          FROM comments c
                          JOIN photos p ON c.photo_id = p.photo_id
                          JOIN albums a ON p.album_id = a.album_id
                          WHERE c.user_id != a.user_id  -- Εξασφαλίζει ότι η φωτογραφία ανήκει σε άλλον
                          GROUP BY c.user_id
                      ) AS comment_counts ON u.user_id = comment_counts.user_id
                      ORDER BY contribution_score DESC
                      LIMIT 10;
                    """)

    top_ten_users = cursor.fetchall()

    cursor.close()
    return render_template("top-users.html", top_users=top_ten_users)

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        cursor = conn.cursor()

        cursor.execute("SELECT user_id, password FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        #Τσεκάρουμε αν υπαρχει ο χρήστης και ο κωδικός του
        if user and user[1] == password:

            session["user_id"] = user[0]
            
            return redirect(url_for("login_success"))
        else:
            flash("Wrong email or password. Try again", "error")
    return render_template("login.html")

@app.route("/login-success")
def login_success():
    return render_template("login-success.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/friends")
def friends():
    current_user_id = session.get("user_id")
    
    #Αν δεν είναι συνδεδεμένος τον βάζουμε να συνδεθεί
    if not current_user_id:
        return redirect(url_for("login"))
    
    cursor = conn.cursor()

    #υποθέτουμε οτι ένας φίλος x είναι φίλος με τον φίλο y αν και μονο αν ο y είναι φιλος με τον x
    friends_query = """
        SELECT user_id, first_name, last_name, email 
        FROM users 
        WHERE user_id IN (
            SELECT user2_id FROM friends WHERE user1_id = %s
            UNION
            SELECT user1_id FROM friends WHERE user2_id = %s
        );
    """
    cursor.execute(friends_query, (current_user_id, current_user_id))
    my_friends = cursor.fetchall()


    return render_template("friends.html", friends=my_friends)

if __name__ == "__main__":
    app.run()