# DCI Reporting Dashboard

A Streamlit web app that connects to the DCI Airtable database and lets Dr. Bullock
run reports (unique attendees by year, demographic breakdowns, person history,
event attendance) without writing SQL or scrolling through 20,000 rows.

Built for the Davidson database final project, Spring 2026.
Team: Cillian Hallinan, Mary Devine, Yurdanur Yolcu.

## Run it locally

```bash
# 1. Create a Python virtual environment (sandbox for our packages)
python3 -m venv venv

# 2. Activate it (Mac / Linux)
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app opens in your browser at http://localhost:8501.

## Connecting to Airtable

This app reads from the DCI Airtable base via the Airtable API.
You need a personal access token with read access to the base.

1. Generate a token at: https://airtable.com/create/tokens
   - Scope: `data.records:read`, `schema.bases:read`
   - Access: the DCI Final base only
2. Create the file `.streamlit/secrets.toml` with this content:

   ```toml
   AIRTABLE_TOKEN = "your_token_here"
   AIRTABLE_BASE_ID = "appRj4cX0c3HavR64"
   ```

3. The `.gitignore` keeps this file out of GitHub. Never commit your token.
