# CFPMonitor

Twice-weekly discovery of conferences, CFPs, fellowships, and speaker opportunities
on AI governance, surveillance, power consolidation, and civil liberties.
Results go to a Google Sheet. New sources are added to `seeds.yaml` automatically.

Built on Anthropic Managed Agents — intentionally annotated as a learning reference
for how agent harnesses work.

## Prerequisites

- Python 3.12+
- An Anthropic API key (console.anthropic.com)
- A Google Sheet (create a blank one)
- A Google Cloud service account with Sheets API access (one-time, ~10 minutes)

## Google Cloud Setup (one-time)

1. Go to console.cloud.google.com → create a project
2. Enable the **Google Sheets API** for that project
3. Go to IAM & Admin → Service Accounts → Create Service Account
4. Download the JSON key file — save it somewhere safe (e.g. `~/.config/cfpmonitor-sa.json`)
5. Open your Google Sheet → Share → paste the service account email → Editor access

## Installation

```bash
git clone <repo>
cd CFPMonitor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
# Edit .env with your API key, Sheet ID, and service account path
```

Run setup once:

```bash
./venv/bin/python setup.py
```

This creates the Managed Agent, cloud Environment, initializes the Sheet, and installs
the pre-commit hook. You won't need to run it again.

## Running

Manually:
```bash
./venv/bin/python run.py
```

Via cron (twice weekly, Mon/Thu 8am) — add to `crontab -e`:
```
0 8 * * 1,4 cd "/home/privacat/Software Projects/CFPMonitor" && ./venv/bin/python run.py >> logs/run.log 2>&1
```

Note: cron only fires while WSL is active. Missing a run is harmless — events are caught next time.

## Customizing

- **Add topics:** edit `topics.yaml`
- **Add/remove seed sites:** edit `seeds.yaml`
- **Change the model:** update `ANTHROPIC_MODEL` in `.env`

## Governance

`GOVERNANCE.md` tracks what data this system touches and where it goes (mini-ROPA).
The pre-commit hook updates it automatically when code changes are ROPA-relevant.
Review any `# VERIFY:` lines before finalizing a commit.

## Tests

```bash
source venv/bin/activate
pytest tests/ -v
```
