DB_NAME="k29photo"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"
APP_FILE="app.py"

read -s -p "Enter postgres user password: " DB_PASS
echo

echo ">>> Creating Python virtual environment..."
python3 -m venv .venv 

echo ">>> Activating virtual environment..."
source .venv/bin/activate

echo ">>> Installing Python libraries from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

echo ">>> Prepering PostgreSQL database..."

export PGPASSWORD="$DB_PASS"

if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"
    echo ">>> Database '$DB_NAME' created."
fi

echo ">>> Applying database schema from schema.sql..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f schema.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f insert_data.sql

echo ">>> Starting Python application..."
python3 "$APP_FILE"