# Deploy to Hugging Face Spaces (free)

This app’s Streamlit UI runs as a **Docker** Space on free CPU hardware
(~16 GB RAM), which is enough for the Instacart CSVs.

Hosting is free. **Anthropic API usage is billed separately** to your Anthropic account.

## 1. Create the Space

1. Sign up at [huggingface.co](https://huggingface.co/join).
2. Click **New Space**.
3. Settings:
   - **Space SDK:** Docker
   - **Space hardware:** CPU basic (free)
   - Visibility: public or private
4. Create the Space and note its git URL, e.g.  
   `https://huggingface.co/spaces/YOUR_USER/agentic-data-explorer`

## 2. Add the Anthropic secret

In the Space: **Settings → Variables and secrets → New secret**

| Name | Value |
|------|--------|
| `ANTHROPIC_API_KEY` | your Anthropic API key |

Do **not** commit `shared/.env`. If that file was ever shared or committed, rotate the key in the [Anthropic console](https://console.anthropic.com/) first.

## 3. Push this folder to the Space

From `Agentic_data_explorer/` (this directory):

```powershell
# One-time: install Git LFS if needed
git lfs install

# Point a remote at your Space (example name)
git init   # skip if this folder is already a git repo
git remote add space https://huggingface.co/spaces/YOUR_USER/YOUR_SPACE_NAME

# Track CSVs with LFS (see .gitattributes), then force-add despite .gitignore
git add Dockerfile .dockerignore .gitattributes README.md DEPLOY_HF_SPACES.md
git add shared streamlit
Get-ChildItem "shared\archive (3)\*.csv" | ForEach-Object { git add -f -- $_.FullName }

git commit -m "Deploy Streamlit Agentic Data Explorer to HF Spaces"
git push space HEAD:main
```

If Hugging Face asks you to authenticate, use a [user access token](https://huggingface.co/settings/tokens) with **Write** access (HTTPS password = token).

First push of ~680 MB of CSVs can take several minutes. The Space will build the Docker image automatically.

## 4. Verify

1. Open the Space page and wait until the build status is **Running**.
2. Ask something simple, e.g. “Bar chart of top 10 departments by product count”.
3. If the app errors on missing data, confirm the six CSVs landed under `shared/archive (3)/` in the Space Files tab.
4. If auth fails, confirm `ANTHROPIC_API_KEY` is set as a **secret** (not only a variable) and rebuild.

## Files used by the Space

| File | Role |
|------|------|
| `Dockerfile` | Installs deps, runs Streamlit on port **7860** |
| `.dockerignore` | Skips `.venv`, `nextjs/`, secrets, notebooks |
| `.gitattributes` | Sends `*.csv` through Git LFS |
| `README.md` | Space card (`sdk: docker`, `app_port: 7860`) |
| `shared/` | Agent core + dataset |
| `streamlit/` | UI |

## Local Docker smoke test (optional)

With CSVs present and `ANTHROPIC_API_KEY` in the environment:

```powershell
cd Agentic_data_explorer
docker build -t agentic-data-explorer .
docker run --rm -p 7860:7860 -e ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY% agentic-data-explorer
```

Open http://localhost:7860
