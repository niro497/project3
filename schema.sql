DROP TABLE IF EXISTS likes;
DROP TABLE IF EXISTS comments;
DROP TABLE IF EXISTS photo_tags;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS photos;
DROP TABLE IF EXISTS albums;
DROP TABLE IF EXISTS friends;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    birthdate DATE,
    hometown VARCHAR(100),
    gender VARCHAR(10), --TODO: CHECK an einai M, F
    password VARCHAR(255) NOT NULL
);

CREATE TABLE friends (
    user1_id INT NOT NULL,
    user2_id INT NOT NULL,
    PRIMARY KEY (user1_id, user2_id),
    FOREIGN KEY (user1_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (user2_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CHECK (user1_id < user2_id) -- δεν το καταλαβαίνω
);

CREATE TABLE albums (
    album_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    album_name VARCHAR(100) NOT NULL,
    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE (user_id, album_name)
);

CREATE TABLE photos (
    photo_id SERIAL PRIMARY KEY,
    album_id INT NOT NULL,
    caption TEXT,
    data BYTEA NOT NULL,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (album_id) REFERENCES albums(album_id) ON DELETE CASCADE
);

CREATE TABLE tags (
    tag_id SERIAL PRIMARY KEY,
    tag_name VARCHAR(50) UNIQUE NOT NULL,
    CHECK (tag_name = LOWER(tag_name)),
    CHECK (tag_name NOT LIKE '% %')
);

CREATE TABLE photo_tags (
    photo_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (photo_id, tag_id),
    FOREIGN KEY (photo_id) REFERENCES photos(photo_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
);

CREATE TABLE comments (
    comment_id SERIAL PRIMARY KEY,
    photo_id INT NOT NULL,
    user_id INT NOT NULL,
    comment_text TEXT NOT NULL,
    comment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (photo_id) REFERENCES photos(photo_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE likes (
    user_id INT NOT NULL,
    photo_id INT NOT NULL,
    liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, photo_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (photo_id) REFERENCES photos(photo_id) ON DELETE CASCADE
);

---- R1: Χρήστης δεν μπορεί να σχολιάσει τη δική του φωτογραφία.
---- Υλοποιείται ως TRIGGER (δεν μπορεί να εκφραστεί με απλό CHECK
---- γιατί χρειάζεται join με Albums).
--CREATE OR REPLACE FUNCTION fn_no_self_comment()
--RETURNS TRIGGER LANGUAGE plpgsql AS $$
--DECLARE
--    v_photo_owner INT;
--BEGIN
--    SELECT u.user_id INTO v_photo_owner
--    FROM   Photos p
--    JOIN   Albums a ON a.album_id = p.album_id
--    JOIN   Users  u ON u.user_id  = a.owner_id
--    WHERE  p.photo_id = NEW.photo_id;
--
--    IF NEW.user_id IS NOT NULL AND NEW.user_id = v_photo_owner THEN
--        RAISE EXCEPTION 'Ο χρήστης δεν μπορεί να σχολιάσει τη δική του φωτογραφία.';
--    END IF;
--    RETURN NEW;
--END;
--$$;
--
--CREATE TRIGGER trg_no_self_comment
--BEFORE INSERT ON Comments
--FOR EACH ROW EXECUTE FUNCTION fn_no_self_comment();
--
--
---- R3: Ένας χρήστης δεν μπορεί να κάνει like στη δική του φωτογραφία.
--CREATE OR REPLACE FUNCTION fn_no_self_like()
--RETURNS TRIGGER LANGUAGE plpgsql AS $$
--DECLARE
--    v_photo_owner INT;
--BEGIN
--    SELECT a.owner_id INTO v_photo_owner
--    FROM   Photos p
--    JOIN   Albums a ON a.album_id = p.album_id
--    WHERE  p.photo_id = NEW.photo_id;
--
--    IF NEW.user_id = v_photo_owner THEN
--        RAISE EXCEPTION 'Ο χρήστης δεν μπορεί να κάνει like στη δική του φωτογραφία.';
--    END IF;
--    RETURN NEW;
--END;
--$$;
--
--CREATE TRIGGER trg_no_self_like
--BEFORE INSERT ON Likes
--FOR EACH ROW EXECUTE FUNCTION fn_no_self_like();
----