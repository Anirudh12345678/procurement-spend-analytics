# Complete Instructions to Run ProcureSight

This guide is for a teammate who has a new laptop, does not have the source code yet, and wants to run the complete project locally.

The project consists of three running parts:

1. PostgreSQL database, automatically provided through Docker
2. FastAPI Python backend
3. React frontend dashboard

You do **not** need to install PostgreSQL directly on the laptop. Docker downloads and runs PostgreSQL for you.

## 1. Get access to the repository

The GitHub repository is private:

<https://github.com/Anirudh12345678/procurement-spend-analytics>

Before continuing:

1. Create a GitHub account if you do not have one.
2. Ask the repository owner to invite your GitHub username as a collaborator.
3. Accept the invitation sent by GitHub.

You will not be able to clone the private repository until the invitation is accepted.

## 2. Install the prerequisites

Install all of the following:

- Git: <https://git-scm.com/downloads>
- Docker Desktop: <https://www.docker.com/products/docker-desktop/>
- Python 3.11 or newer: <https://www.python.org/downloads/>
- Node.js 20 or newer, including npm: <https://nodejs.org/>

After installation, open Terminal on macOS/Linux or PowerShell on Windows and verify:

```bash
git --version
docker --version
docker compose version
python3 --version
node --version
npm --version
```

On Windows, use this if `python3` is not recognized:

```powershell
py --version
```

Start Docker Desktop and wait until it reports that the Docker engine is running.

## 3. Clone the repository

Choose a folder where you want the project, then run:

```bash
git clone https://github.com/Anirudh12345678/procurement-spend-analytics.git
cd procurement-spend-analytics
```

GitHub may open a browser or ask for authentication because the repository is private.

Confirm that these important files exist:

```text
.env.example
compose.yaml
purchase_orders.csv
backend/
frontend/
```

All commands in the next sections assume your terminal is inside the `procurement-spend-analytics` folder unless stated otherwise.

## 4. Create the local environment configuration

The real `.env` file is intentionally not stored on GitHub. Every teammate creates their own local file and chooses their own local database password.

macOS/Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Open `.env` in a text editor. Set the database section like this, replacing `ChooseYourOwnPassword2026` in both places with the same password:

```env
POSTGRES_DB=procurement
POSTGRES_USER=procurement
POSTGRES_PASSWORD=ChooseYourOwnPassword2026
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://procurement:ChooseYourOwnPassword2026@localhost:5432/procurement
```

Important database-password rules:

- This is a new local password chosen by the person setting up the project.
- It is not their GitHub, computer, Docker, or OpenAI password.
- `POSTGRES_PASSWORD` and the password inside `DATABASE_URL` must be identical.
- Prefer letters and numbers. Characters such as `@`, `:`, `/`, `#`, and `?` require URL encoding and can cause connection problems.
- Never commit or send the `.env` file to another person.

The remaining settings can stay at their example values for a normal local demonstration.

### Optional OpenAI configuration

The application works without an OpenAI key by producing a clearly labeled deterministic fallback recommendation.

To enable live AI-generated narratives, add an authorized key to the local `.env`:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
OPENAI_TIMEOUT_SECONDS=30
```

Put the key after `OPENAI_API_KEY=` only if you are authorized to use that OpenAI project. Never put an API key in `frontend/.env`, a `VITE_` variable, GitHub, screenshots, or chat messages.

## 5. Start the PostgreSQL database

Make sure Docker Desktop is running, then execute from the project root:

```bash
docker compose up -d database
```

Docker will automatically:

- download the PostgreSQL 16 image if it is not already installed;
- create a PostgreSQL container;
- create the `procurement` user;
- create the `procurement` database;
- use the password from `.env`;
- store the database in a persistent Docker volume.

Check its status:

```bash
docker compose ps
```

Wait until the database is shown as `healthy`. If it is still starting, wait several seconds and run the status command again.

## 6. Create the Python environment

From the project root, create a virtual environment.

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

After activation, the terminal normally shows `(.venv)` before the prompt.

Install backend dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e "./backend[dev]"
```

The virtual environment only needs to be created once. Activate it again whenever you open a new backend terminal.

## 7. Create the tables and import the dataset

Keep the Python virtual environment activated, then run:

```bash
cd backend
alembic upgrade head
python -m app.scripts.import_data --csv ../purchase_orders.csv
python -m app.scripts.verify_data
python -m app.scripts.calculate_opportunities
cd ..
```

The first import should report approximately:

```text
47,128 purchase orders
106 suppliers
10 categories
50 items
5 business units
$411,183,335.24 total spend
0 duplicate PO IDs
0 orphan relationships
```

The opportunity calculation should report:

```text
50 item benchmarks
254 active opportunities
107 price optimization opportunities
144 contract leakage opportunities
1 supplier consolidation opportunity
2 supplier performance opportunities
```

If the import is run again, it safely updates the existing PO identifiers instead of creating duplicates.

## 8. Install frontend dependencies

From the project root:

```bash
cd frontend
npm ci
cd ..
```

Use `npm ci` for a clean, reproducible installation from `package-lock.json`.

At this point, the one-time setup is complete.

## 9. Start the application for normal use

Use three separate Terminal or PowerShell windows.

### Terminal 1: database

From the project root:

```bash
docker compose up -d database
```

This command returns after starting the database. You can keep this terminal open or reuse it.

### Terminal 2: backend API

macOS/Linux:

```bash
cd procurement-spend-analytics
source .venv/bin/activate
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Windows PowerShell:

```powershell
cd procurement-spend-analytics
.\.venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Keep this terminal running.

### Terminal 3: frontend dashboard

```bash
cd procurement-spend-analytics/frontend
npm run dev
```

Keep this terminal running.

If the terminals were opened directly inside the project folder, omit the first `cd procurement-spend-analytics` command.

## 10. Open and verify the application

Open these addresses in a browser:

- Dashboard: <http://127.0.0.1:5173>
- API documentation: <http://127.0.0.1:8000/docs>
- API health check: <http://127.0.0.1:8000/health>

The health check should show:

```json
{"status":"ok"}
```

On the dashboard, confirm:

- Total Spend shows approximately `$411.2M`.
- Total Orders shows `47,128`.
- Suppliers shows `106`.
- Cost Opportunities shows approximately `$12.5M` and `254 active findings`.

Then verify the main demonstration flow:

1. Open **Spend Analysis** and apply a supplier-country or category filter.
2. Open **Cost Optimization** and select an opportunity to see its detail panel.
3. Open **AI Advisor** and view or generate a recommendation.
4. Remember that estimated opportunities are not guaranteed savings.

## 11. Stop the application safely

In the backend and frontend terminals, press `Ctrl+C`.

Stop the database container while keeping its data:

```bash
docker compose stop database
```

Alternatively, stop and remove the container while preserving the database volume:

```bash
docker compose down
```

Do **not** add `-v` during normal shutdown. The `-v` option deletes the database volume.

## 12. Start it again on another day

You do not need to reinstall dependencies, migrate, or import the CSV every time.

Normally, just:

1. Start Docker Desktop.
2. Run `docker compose up -d database`.
3. Start the backend in an activated Python environment.
4. Run `npm run dev` inside `frontend`.
5. Open <http://127.0.0.1:5173>.

## 13. Pull future project updates

Stop the running backend and frontend, then from the repository root:

```bash
git pull
```

Apply possible backend database and dependency updates:

```bash
source .venv/bin/activate
python -m pip install -e "./backend[dev]"
cd backend
alembic upgrade head
cd ..
```

On Windows, activate with `.\.venv\Scripts\Activate.ps1` instead.

Apply frontend dependency updates:

```bash
cd frontend
npm ci
cd ..
```

Only rerun the CSV importer or opportunity calculation if the data or optimization implementation changed.

## 14. Run tests and the production build

Backend:

```bash
source .venv/bin/activate
cd backend
pytest -q
ruff check .
cd ..
```

Frontend:

```bash
cd frontend
npm test
npm run typecheck
npm run build
cd ..
```

## 15. Troubleshooting

### Docker command is unavailable

Install and start Docker Desktop. Closing the Docker Desktop application also stops access to the database container.

### Database does not become healthy

Check the logs:

```bash
docker compose logs database
```

Also check whether another PostgreSQL installation is already using port 5432.

### Password authentication failed

Confirm that `POSTGRES_PASSWORD` and the password inside `DATABASE_URL` are identical.

The PostgreSQL password is set when the Docker volume is created for the first time. Changing `.env` later does not automatically change the password stored in an existing database.

For a brand-new setup with no data worth keeping, you can reset the local database:

```bash
docker compose down -v
docker compose up -d database
```

Warning: `docker compose down -v` permanently deletes that laptop's local database. After resetting, rerun the migrations, CSV import, verification, and opportunity calculation from Section 7.

### Port 5432 is already in use

Change both the exposed port and connection URL in `.env`, for example:

```env
POSTGRES_PORT=5433
DATABASE_URL=postgresql+psycopg://procurement:YourPassword@localhost:5433/procurement
```

Then restart the database container.

### Port 8000 or 5173 is already in use

Stop the process using the port. Using different ports also requires updating the frontend API URL or backend CORS configuration, so using the documented ports is recommended for the local demonstration.

### `python3` is not recognized on Windows

Use `py` to create the environment, then activate it. Once activated, use `python` for the remaining commands.

### PowerShell blocks virtual-environment activation

In a PowerShell window opened for the current user, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Review the change before accepting it, then retry `.\.venv\Scripts\Activate.ps1`.

### Frontend cannot connect to the API

Confirm the backend terminal is still running and <http://127.0.0.1:8000/health> works. Then confirm `CORS_ORIGINS` in the root `.env` includes `http://127.0.0.1:5173`.

### AI generation uses the deterministic fallback

This is expected if no OpenAI key is configured, the account has no available API quota, a rate limit occurs, or the provider returns invalid output. Analytics and opportunity calculations continue to work because the LLM is never the source of truth.

## 16. Important security rules

- Never commit `.env`.
- Never send database or OpenAI credentials in chat or screenshots.
- Never put the OpenAI key in browser-side configuration.
- Every teammate should use their own local database password.
- Do not make the repository public without reviewing the dataset and project requirements.
- Do not use `docker compose down -v` unless you intentionally want to delete the local database.

## Quick daily-start summary

After the one-time setup, the normal start process is:

```bash
# Project root
docker compose up -d database
```

```bash
# Separate backend terminal
source .venv/bin/activate
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
# Separate frontend terminal
cd frontend
npm run dev
```

Open <http://127.0.0.1:5173>.

