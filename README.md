# 🚀 Crypto Compass

AI-powered crypto monitoring system with Telegram integration.

## 🌐 Deploy to Render.com

### Prerequisites
1. GitHub repository
2. Telegram Bot Token
3. Telegram Chat ID

## CheapVibeCode API

The integration uses the provider's OpenAI-compatible API:

- base URL: `https://cheapvibecode.ru/v1`
- authorization: `Authorization: Bearer <API key>`
- models endpoint: `GET /models`
- chat endpoint: `POST /chat/completions`

Never paste the API key into chat, Git, command arguments, or logs. To inspect
the provider's public pricing catalog, run:

```powershell
python scripts/configure_cheapvibecode.py --list-models
```

The default model is `qwen3.8-max`: it has the minimum public pricing multiplier
of `0.05` (about `0.16 ₽ / 1M` weighted tokens at the minimum top-up tier) and
is suitable for multilingual text summaries. Configure production with one
hidden key prompt:

```powershell
python scripts/configure_cheapvibecode.py --configure
```

The helper performs a minimal connectivity check, atomically updates the VPS
`.env` with mode `600`, restarts the service, verifies both health endpoints,
and restores the previous environment if the health check fails.

### Step-by-Step Deploy

#### 1. Prepare Files
Ensure these files are in your repo:
- `runtime.txt` → `python-3.12.0`
- `requirements.txt` → Use the optimized version
- `render.yaml` → Full configuration
- `.gitignore` → Exclude sensitive files

#### 2. Connect to Render
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Blueprint"
3. Connect your GitHub repository
4. Select your repo

#### 3. Configure Environment Variables
In Render Dashboard, set these **Secret** variables:
- `TELEGRAM_TOKEN` → Your bot token from @BotFather
- `CHAT_ID` → Your Telegram chat ID
- `COINGECKO_API_KEY` → (Optional) API key
- `ETHERSCAN_API_KEY` → (Optional) API key
- `BSCSCAN_API_KEY` → (Optional) API key

#### 4. Deploy
1. Render will automatically detect `render.yaml`
2. Click "Apply"
3. Wait ~2 minutes for build
4. Check logs for `✅ ALL PACKAGES OK!`

#### 5. Verify
- Bot should send "🚀 System started" message
- Check logs: `python main.py` running
- Test with `/start` command in Telegram

### 🔧 Troubleshooting

#### Build fails with pandas compilation error
**Solution:** Ensure `runtime.txt` exists with `python-3.12.0`

#### Build takes >10 minutes
**Solution:** Check if `--only-binary` flag is used in `buildCommand`

#### Missing environment variables
**Solution:** Set all required vars in Render Dashboard → Environment

#### Bot doesn't respond
**Solution:** 
1. Check logs for errors
2. Verify `TELEGRAM_TOKEN` and `CHAT_ID`
3. Restart service

### 📊 Monitoring

View logs in real-time:
```bash
# In Render Dashboard → Logs
```

Check health:
```bash
curl https://your-app.onrender.com/
```

### 🔄 Updates

Push to GitHub → Auto-deploy on Render:
```bash
git add .
git commit -m "Update config"
git push origin main
```

### 💰 Costs

**Free Plan:**
- 750 hours/month
- Sleeps after 15min inactivity
- 512 MB RAM
- **Perfect for testing!**

**Starter Plan ($7/month):**
- Always on
- 512 MB RAM
- Better for production

### 📚 Resources
- [Render Docs](https://render.com/docs)
- [Python on Render](https://render.com/docs/deploy-python)
- [Environment Variables](https://render.com/docs/environment-variables)