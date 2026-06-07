from flask import Flask, render_template, request, flash, redirect, url_for, session
import base64
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


@app.route("/albums")
def view_albums():
    cursor = conn.cursor()
    cursor.execute("select album_id, album_name from albums")
    albums = cursor.fetchall()
    cursor.close()
    return render_template("albums.html", albums = albums)

##TODO: if logged in a user should be able to view his albums
@app.route('/albums/<int:album_id>')
def view_album(album_id):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT album_name, user_id
        FROM albums
        WHERE album_id = %s
        """, (album_id,))
    album = cursor.fetchone()

    if not album:
        cursor.close()
        return redirect(url_for("view_albums"))
    
    album_name = album[0]

    album_owner_id = album[1]
    current_user_id = session.get("user_id")
    is_owner = (int(current_user_id) == int(album_owner_id)) if current_user_id else False

    cursor.execute("""
                   SELECT p.photo_id, p.caption, p.data
                   FROM photos p
                   WHERE p.album_id = %s
                   """, (album_id,))
    photos = cursor.fetchall()

    photos_list = []

    for photo in photos:
        photo_id, photo_caption, photo_data = photo
        encoded_photo = base64.b64encode(photo_data).decode('utf-8')
        photo_src = f"data:image/jpeg;base64,{encoded_photo}"
        photos_list.append({
            'photo_id': photo_id,
            'caption': photo_caption,
            'data': photo_src
        })

    cursor.close()
    return render_template("album.html", photos=photos_list, album_id=album_id, album_name=album_name, is_owner=is_owner)

#TODO: πρέπει να μπορούν να διαγράφουν albums
@app.route("/create-album", methods = ["GET", "POST"])
def create_album():
    current_user_id = session.get("user_id")

    if not current_user_id:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        album_name = request.form["album_name"]

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO albums (user_id, album_name)
            VALUES (%s, %s)
        """, (current_user_id, album_name))

        conn.commit()
        cursor.close()

        return redirect(url_for("view_albums"))
    
    return render_template("create-album.html")

@app.route("/albums/<int:album_id>/upload-photo/", methods=["GET", "POST"])
def upload_photo(album_id):
    current_user_id = session.get("user_id")

    if not current_user_id:
        return redirect(url_for("login"))
    
    #ο καθε χρησητης μπορει να προσθέσει φωτο μονο στα δικα του album
    cursor = conn.cursor()
    cursor.execute("select user_id from albums where album_id = %s", (album_id,))
    user = cursor.fetchone()

    if int(user[0]) != int(current_user_id):
        flash("This album is created from another user. You cannot add a photo here", "error")
        cursor.close()
        return redirect(url_for("view_albums"))
        
    if request.method == "POST":
        caption = request.form["caption"]
        photo_file = request.files["photo"]

        #αν ο χρήστης δεν βαλει τίποτα μπαίνει αυτόματα κενό
        #επίσης αν ο χρήστης βάλει "Kalokairi    " μετατρέπεται σε "kalokairi"
        tags_input = request.form.get("tags", "").strip().lower() 

        photo_data = photo_file.read()

        cursor = conn.cursor()

        cursor.execute("""
                       INSERT INTO photos (album_id, caption, data)
                       VALUES (%s, %s, %s) RETURNING photo_id 
                       """, (album_id, caption, psycopg2.Binary(photo_data))) # Xρειαζόμαστε το photo_id για την συσχέτιση photo_tag
        
        photo_id = cursor.fetchone()[0]

        if tags_input:
            tags_list = tags_input.split()
            for tag_name in tags_list:
                # Εισαγωγή του tag αν δεν υπάρχει ήδη (λόγω UNIQUE constraint), για α΄το χρειαζόμαστε το ON CONFLICT DO NOTHING
                cursor.execute("""
                    INSERT INTO tags (tag_name) 
                    VALUES (%s) 
                    ON CONFLICT (tag_name) DO NOTHING 
                    RETURNING tag_id
                """, (tag_name,))
                
                # Παίρνουμε το tag_id (είτε μπήκε τώρα είτε υπήρχε ήδη)
                cursor.execute("SELECT tag_id FROM tags WHERE tag_name = %s", (tag_name,))
                tag_id = cursor.fetchone()[0]

                # Δημιουργία συσχέτισης photo_tags. Δεν μπορεί να προσθέσει την ίδια photo με την ίδια ετικέτα
                cursor.execute("""
                    INSERT INTO photo_tags (photo_id, tag_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (photo_id, tag_id))

        conn.commit()
        cursor.close()

        return redirect(url_for("view_album", album_id=album_id))
    
    return render_template("upload-photo.html", album_id=album_id)

@app.route("/albums/<int:album_id>/delete", methods=["POST"])
def delete_album(album_id):
    current_user_id = session.get("user_id")

    if not current_user_id:
        return redirect(url_for("login"))
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id
        FROM albums
        WHERE album_id = %s
    """, (album_id,))

    album = cursor.fetchone()

    if not album:
        cursor.close()
        return redirect(url_for("view_albums"))
    
    owner_id = album[0]

    if int(owner_id) != int(current_user_id):
        cursor.close()
        flash("You cannot delete an album that belongs to another user!", "error")
        return redirect(url_for("view_albums"))
    
    cursor.execute("""
        DELETE FROM albums
        WHERE album_id = %s
    """, (album_id,))

    conn.commit()
    cursor.close()

    return redirect(url_for("view_albums"))

@app.route("/photos/<int:photo_id>/delete", methods=["POST"])
def delete_photo(photo_id):
    current_user_id = session.get("user_id")

    if not current_user_id:
        return redirect(url_for("login"))
    
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.album_id, a.user_id
        FROM photos p
        JOIN albums a ON p.album_id = a.album_id
        WHERE p.photo_id = %s
    """, (photo_id,))

    photo_info = cursor.fetchone()

    if not photo_info:
        cursor.close()
        return redirect(url_for("view_albums"))
    
    album_id = photo_info[0]
    owner_id = photo_info[1]

    if int(owner_id) != int(current_user_id):
        cursor.close()
        flash("You cannot delete a photo that belongs to another user!", "error")
        return redirect(url_for("view_album", album_id=album_id))
    
    cursor.execute("""
        DELETE FROM photos
        WHERE photo_id = %s
    """, (photo_id,))

    conn.commit()
    cursor.close()

    return redirect(url_for("view_album", album_id=album_id))

@app.route("/photos/<int:photo_id>/likes")
def view_likes(photo_id):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.first_name, u.last_name, u.email
        FROM likes l
        JOIN users u ON l.user_id = u.user_id
        WHERE l.photo_id = %s
        ORDER BY u.first_name, u.last_name
    """, (photo_id,))

    users = cursor.fetchall()
    cursor.close()

    return render_template("likes.html", users=users, photo_id=photo_id)

@app.route("/popular-tags")
def popular_tags():
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT t.tag_name, COUNT(pt.photo_id) AS photo_count
                   FROM tags t
                   JOIN photo_tags pt ON t.tag_id = pt.tag_id
                   GROUP BY t.tag_id, t.tag_name
                   ORDER BY photo_count DESC
                   """)
    tags = cursor.fetchall()
    cursor.close()
    
    return render_template("popular-tags.html", tags=tags)

@app.route("/tags/<tag_name>")
def view_photos_by_tag(tag_name):
    view_filter = request.args.get('filter', 'all') # Διαβάζει αν πατήθηκε το "Οι δικές μου"
    current_user_id = session.get("user_id")

    cursor = conn.cursor()

    # Αν θέλει μόνο τις δικές του
    if view_filter == 'mine' and not current_user_id:
        return redirect(url_for("login"))
    elif view_filter == 'mine':
        cursor.execute("""
                    SELECT p.photo_id, p.caption, p.data
                    FROM photos p
                    JOIN photo_tags pt ON p.photo_id = pt.photo_id
                    JOIN tags t ON pt.tag_id = t.tag_id
                    JOIN albums a ON p.album_id = a.album_id
                    WHERE t.tag_name = %s AND a.user_id = %s
                    """, (tag_name, current_user_id,))
    else:
        cursor.execute("""
                    SELECT p.photo_id, p.caption, p.data
                    FROM photos p
                    JOIN photo_tags pt ON p.photo_id = pt.photo_id
                    JOIN tags t ON pt.tag_id = t.tag_id
                    JOIN albums a ON p.album_id = a.album_id
                    WHERE t.tag_name = %s
                    """, (tag_name,))


    photos = cursor.fetchall()

    photos_list = []
    for photo in photos:
        encoded_photo = base64.b64encode(photo[2]).decode('utf-8')
        photos_list.append({
            'photo_id': photo[0],
            'caption': photo[1],
            'data': f"data:image/jpeg;base64,{encoded_photo}"
        })

    cursor.close()
    return render_template("view-tag.html", photos=photos_list, tag_name=tag_name, filter=view_filter)


@app.route("/search", methods=["GET", "POST"])
def search_photos():
    if request.method == "POST":
        search_query = request.form.get("query", "").strip().lower()
        if not search_query:
            return render_template("search.html", photos=[])

        tags_list = search_query.split() # Χωρίζει το "ήλιος θάλασσα" σε λίστα: ["ήλιος", "θάλασσα"]

        cursor = conn.cursor()
        
        # Βρες τις φωτογραφίες που έχουν ΑΚΡΙΒΩΣ όλες τις λέξεις που δώσαμε
        query = """
            SELECT p.photo_id, p.caption, p.data
            FROM photos p
            JOIN photo_tags pt ON p.photo_id = pt.photo_id
            JOIN tags t ON pt.tag_id = t.tag_id
            WHERE t.tag_name = ANY(%s)
            GROUP BY p.photo_id, p.caption, p.data
            HAVING COUNT(DISTINCT t.tag_id) = %s
        """
        cursor.execute(query, (tags_list, len(tags_list)))
        photos = cursor.fetchall()

        photos_list = []
        for photo in photos:
            encoded_photo = base64.b64encode(photo[2]).decode('utf-8')
            photos_list.append({
                'photo_id': photo[0], 'caption': photo[1], 'data': f"data:image/jpeg;base64,{encoded_photo}"
            })
            
        cursor.close()
        return render_template("search.html", photos=photos_list, query=search_query)

    return render_template("search.html")

@app.route("/photos/<int:photo_id>")
def view_photo(photo_id):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM likes
        WHERE photo_id = %s
    """, (photo_id,))

    likes_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT c.comment_text, c.comment_date, u.first_name, u.last_name
        FROM comments c
        JOIN users u ON c.user_id = u.user_id
        WHERE c.photo_id = %s
    """, (photo_id,))

    comments = cursor.fetchall()

    cursor.execute("""
        SELECT p.photo_id, p.caption, p.data, a.user_id
        FROM photos p
        JOIN albums a ON p.album_id = a.album_id
        WHERE p.photo_id = %s
    """, (photo_id,))

    photo = cursor.fetchone()
    cursor.close()

    if not photo:
        return redirect(url_for("view_albums"))

    photo_id, caption, photo_data, owner_id = photo

    current_user_id = session.get("user_id")
    is_owner = (int(current_user_id) == int(owner_id)) if current_user_id else False

    encoded_photo = base64.b64encode(photo_data).decode('utf-8')
    photo_src = f"data:image/jpeg;base64,{encoded_photo}"

    return render_template(
        "photo.html",
        photo={
            "photo_id": photo_id,
            "caption": caption,
            "data": photo_src
        },
        likes_count=likes_count,
        comments=comments,
        is_owner=is_owner
    )

@app.route("/photos/<int:photo_id>/comment", methods=["POST"])
def add_comment(photo_id):
    current_user_id = session.get("user_id")

    if not current_user_id:
        return redirect(url_for("login"))
    
    comment_text = request.form["comment_text"]

    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.user_id
        FROM photos p
        JOIN albums a ON p.album_id = a.album_id
        WHERE p.photo_id = %s
    """, (photo_id,))

    owner = cursor.fetchone()

    if not owner:
        cursor.close()
        return redirect(url_for("view_albums"))
    
    owner_id = owner[0]

    if int(owner_id) != int(current_user_id):
        cursor.close()
        flash("You cannot comment on your own photo!", "error")
        return redirect(url_for("view_photo", photo_id=photo_id))

    cursor.execute("""
    INSERT INTO comments (photo_id, user_id, comment_text)
    VALUES (%s, %s, %s)
    """, (photo_id, current_user_id, comment_text))

    conn.commit()
    cursor.close()

    return redirect(url_for("view_photo", photo_id=photo_id))

@app.route("/photos/<int:photo_id>/like", methods=["POST"])
def like_photo(photo_id):
    current_user_id = session.get("user_id")

    if not current_user_id:
        return redirect(url_for("login"))
    
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO likes (user_id, photo_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """, (current_user_id, photo_id))

    conn.commit()
    cursor.close()

    return redirect(url_for("view_photo", photo_id=photo_id))

@app.route("/comment-search", methods=["GET", "POST"])
def comment_search():
    results = []
    query = "" 
    
    if request.method == "POST":
        query = request.form.get("query", "").strip().lower()
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.user_id, u.first_name, u.last_name, c.photo_id, c.comment_text, c.comment_date
            FROM comments c
            JOIN users u ON c.user_id = u.user_id
            WHERE LOWER(c.comment_text) = LOWER(%s)
            ORDER BY c.comment_date DESC
        """, (query,))

        results = cursor.fetchall()
        cursor.close()

    return render_template("comment-search.html", results=results, query=query)

if __name__ == "__main__":
    app.run(debug=True)