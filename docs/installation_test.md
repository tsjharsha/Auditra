# Installation Test

These commands are the final clean-environment reproduction path.

```powershell
git clone https://github.com/tsjharsha/Auditra.git
cd Auditra
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
python -m unittest discover -s tests -v
```

Run the backend:

```powershell
py -3.13 -m uvicorn backend.auditra.api:app --host 127.0.0.1 --port 8002
```

Run the frontend in a second terminal:

```powershell
cd frontend
$env:VITE_AUDITRA_API_BASE="http://127.0.0.1:8002"
npx vite --host 127.0.0.1 --port 5174
```

Open:

```text
http://127.0.0.1:5174/
```

Optional database path:

1. Create a PostgreSQL database.
2. Apply `migrations/001_initial_postgres.sql`.
3. Set `AUDITRA_DATABASE_URL`.
4. Restart the API.

If `AUDITRA_DATABASE_URL` is not set, Auditra uses in-memory storage.
