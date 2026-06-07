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
    gender VARCHAR(1), 
    password VARCHAR(255) NOT NULL
);

CREATE TABLE friends (
    user1_id INT NOT NULL,
    user2_id INT NOT NULL,
    PRIMARY KEY (user1_id, user2_id),
    FOREIGN KEY (user1_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (user2_id) REFERENCES users(user_id) ON DELETE CASCADE
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
    user_id INT,
    guest_name VARCHAR(100),
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

CREATE OR REPLACE FUNCTION check_comment_not_own_photo()
RETURNS TRIGGER AS $$
DECLARE
    photo_owner_id INT;
BEGIN
    --βρες τον ιδιοκτήτη της φωτογραφίας μέσω του album
    SELECT a.user_id
    INTO photo_owner_id
    FROM photos p
    JOIN albums a ON p.album_id = a.album_id
    WHERE p.photo_id = NEW.photo_id;
 
    IF photo_owner_id IS NULL THEN
        RAISE EXCEPTION 'Photo with id % does not exist.', NEW.photo_id;
    END IF;
 
    --ανν ο commenter είναι ιδιοκτήτης της φωτο, απόρριψη
    IF NEW.user_id = photo_owner_id THEN
        RAISE EXCEPTION
            'User % cannot comment on their own photo (photo_id=%).',
            NEW.user_id, NEW.photo_id;
    END IF;
 
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_no_self_comment
    BEFORE INSERT ON comments
    FOR EACH ROW
    EXECUTE FUNCTION check_comment_not_own_photo();

CREATE OR REPLACE FUNCTION check_like_not_own_photo()
RETURNS TRIGGER AS $$
DECLARE
    photo_owner_id INT;
BEGIN
    SELECT a.user_id
    INTO photo_owner_id
    FROM photos p
    JOIN albums a ON p.album_id = a.album_id
    WHERE p.photo_id = NEW.photo_id;
 
    IF photo_owner_id IS NULL THEN
        RAISE EXCEPTION 'Photo with id % does not exist.', NEW.photo_id;
    END IF;
 
    IF NEW.user_id = photo_owner_id THEN
        RAISE EXCEPTION
            'User % cannot like their own photo (photo_id=%).',
            NEW.user_id, NEW.photo_id;
    END IF;
 
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
 
CREATE OR REPLACE TRIGGER trg_no_self_like
    BEFORE INSERT ON likes
    FOR EACH ROW
    EXECUTE FUNCTION check_like_not_own_photo();

CREATE OR REPLACE FUNCTION normalize_friendship_order()
RETURNS TRIGGER AS $$
DECLARE
    lo INT;
    hi INT;
BEGIN
    -- Αποτροπή self-friendship
    IF NEW.user1_id = NEW.user2_id THEN
        RAISE EXCEPTION 'A user cannot be friends with themselves (user_id=%).', NEW.user1_id;
    END IF;
 
    -- Κανονικοποίηση ώστε user1_id < user2_id πάντα
    IF NEW.user1_id > NEW.user2_id THEN
        lo := NEW.user2_id;
        hi := NEW.user1_id;
        NEW.user1_id := lo;
        NEW.user2_id := hi;
    END IF;
 
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
 
CREATE OR REPLACE TRIGGER trg_normalize_friends
    BEFORE INSERT OR UPDATE ON friends
    FOR EACH ROW
    EXECUTE FUNCTION normalize_friendship_order();