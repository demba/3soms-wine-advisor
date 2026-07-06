# 3 SOMS - Greek Wine Advisor

AI-powered wine advisor chatbot specializing in Greek wines. Built with Flask + Claude API.

## Quick Deploy to Railway

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
gh repo create 3soms-wine-advisor --public --push
```

### 2. Deploy on Railway
1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your `3soms-wine-advisor` repo
4. Add environment variable:
   - `ANTHROPIC_API_KEY` = your Claude API key

### 3. Connect Your Domain (3soms.com)
1. In Railway, go to your project → Settings → Domains
2. Click "Add Custom Domain"
3. Enter `3soms.com` (or `www.3soms.com`)
4. Railway will give you a CNAME target (e.g., `xxx.up.railway.app`)
5. In your domain registrar (GoDaddy/Namecheap/etc):
   - Add a CNAME record: `www` → `xxx.up.railway.app`
   - For root domain: use ALIAS/ANAME record, or redirect to www

### 4. Done!
Your wine advisor will be live at https://3soms.com

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY=your_key_here

# Run
python app.py

# Open http://localhost:5000
```

## Files
- `app.py` - Flask backend with Claude API integration
- `templates/index.html` - Chat interface
- `3soms_winery_dataset.json` - Wine knowledge base (19 wineries, 1500+ lines)
- `requirements.txt` - Python dependencies
- `Procfile` - Railway/Heroku deployment config

## Features
- RAG-style retrieval from wine database
- Conversational memory (last 10 messages)
- Personalized wine recommendations
- Mobile-friendly responsive design

## The 3 SOMS Thesis
Greek wines of world-class quality sell at 50-70% cheaper than Burgundy/Napa/Tuscany equivalents. We help people discover these wines before the world catches on.

---
Built with 🍷 by the 3 Sommelier Collective
