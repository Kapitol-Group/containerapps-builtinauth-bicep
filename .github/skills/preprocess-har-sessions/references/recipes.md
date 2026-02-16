# HAR Preprocessing Recipes

## 1) Extract Azure OpenAI Responses API calls
```bash
python3 scripts/preprocess_har.py ./session.har \
  --url-contains /openai/responses \
  --method POST \
  --summary
```

## 2) Keep only one session_state
```bash
python3 scripts/preprocess_har.py ./session.har \
  --url-contains /openai/responses \
  --session-state 679ef52f-83da-4a21-b268-e98ca31fec7b \
  --summary
```

## 3) Produce a shareable compact file
```bash
python3 scripts/preprocess_har.py ./session.har \
  --url-contains /openai/responses \
  --max-body-chars 20000 \
  --summary
```

## 4) Filter by host, method, and time window
```bash
python3 scripts/preprocess_har.py ./session.har \
  --host kap-openai.openai.azure.com \
  --method POST \
  --from-time 2026-01-22T23:00:00+00:00 \
  --to-time 2026-01-22T23:30:00+00:00 \
  --summary
```

## 5) Process an already normalized session JSON file
`preprocess_har.py` accepts normalized JSON arrays as input too. This is useful when re-filtering existing output without the original HAR.
