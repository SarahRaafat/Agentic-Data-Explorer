# Deploy on Streamlit Community Cloud (shareable *.streamlit.app link)

## What you need

- This GitHub repo: https://github.com/SarahRaafat/Agentic-Data-Explorer
- Free signup at https://share.streamlit.io with **Continue with GitHub**
- Your `ANTHROPIC_API_KEY` (add as a Streamlit secret — never commit it)
- Instacart CSVs in `shared/archive (3)/` **on GitHub** (via Git LFS)

## Deploy (about 2 minutes in the browser)

1. Open https://share.streamlit.io and sign in with GitHub.
2. Click **Create app**.
3. Choose:
   - **Repository:** `SarahRaafat/Agentic-Data-Explorer`
   - **Branch:** `main`
   - **Main file path:** `streamlit/app.py`
4. Open **Advanced settings**:
   - **Python version:** 3.11 (if offered)
   - **Secrets** — paste:

```toml
ANTHROPIC_API_KEY = "your_key_here"
```

5. Click **Deploy**.
6. When the app is running, copy the URL (looks like `https://….streamlit.app`) and share it.

## After deploy

- Anyone with the link can use the app; they do **not** need your code.
- Hosting is free; Anthropic API usage is still billed to you.
- Free Cloud apps sleep when idle and have ~1 GB RAM — very large queries on `order_products__prior.csv` may run out of memory.

## Local check

```powershell
cd Agentic_data_explorer
.\.venv\Scripts\activate
cd streamlit
streamlit run app.py
```
