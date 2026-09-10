# Project Material Intelligence - Streamlit Pilot

## What this pilot does
- Uses a Primavera-derived material/procurement baseline.
- Lets you enter vendor forecast dates.
- Calculates Green / Yellow / Red schedule risk.
- Links each material to a downstream fabrication/assembly activity.
- Produces notification drafts.
- Includes a simple what-if delivery-date simulation.
- Exports the calculated risk register as CSV.

## Run locally
1. Install Python 3.10+.
2. Open Command Prompt in this folder.
3. Run:
   pip install -r requirements.txt
4. Start:
   streamlit run app.py
5. Your browser will open the local app.

## Important
This first version is a rule-based proof of concept, not machine learning.
Use anonymized/dummy data unless your company IT policy permits project data in the environment.
