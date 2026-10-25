# After-call report: timeline and the AI-written summary

**The report page** (`#/r/<id>`, opened after every live call) shows the verdict, the key times, an interactive risk-over-time graph, a
step-by-step event history (every event has call time `mm:ss.s` and the laptop's clock time), the transcript with the quoted words
highlighted, filters (source, tactic, search words), a replay of the call, print / PDF, JSON export and delete. It works in English,
Hindi and Marathi (the Hindi and Marathi texts are AI drafts: please have a native speaker check them).

Times are **when the app received the words**. The speech-to-text service may deliver them a second or two after they were spoken.
Spoken digits are stored as `•`.

**The AI summary** is optional. An open model hosted online writes the story of the call in the language selected on the report page.
It never changes the verdict, the timeline or the highlighted words, and quotes it returns are checked against the transcript (anything
not really said is dropped). What is sent: the transcript text with every digit hidden, the times and the tactic quotes. **Never audio.**
It is sent only after the person ticks the consent box on the report page.

## Set it up with Groq (free, no card)
1. Create a free account at console.groq.com and make an API key (API Keys page).
2. Put this line in the project's `.env` (never paste it in a chat or commit the file):
```
GROQ_API_KEY=your-key
```
3. Optional: `LLM_MODEL=` a preferred model id (for example `llama-3.3-70b-versatile`), and `LLM_MAX_ATTEMPTS=3` (how many models to try).
4. Restart the server and test: `python -m core.report_ai --lang en` (then `--lang hi` and `--lang mr`). It sends only a fictional sample call
   and prints which models it tried and why any were skipped.

**How the model is chosen.** The app asks Groq which chat models it serves right now and tries up to 3 in order: your preferred model, then
known good multilingual open models (Llama 3.3 70B, GPT-OSS 120B, Qwen3 32B, Llama 4 Scout, GPT-OSS 20B), then any other chat model.
Speech, guard and tool models are never used. A model is skipped if it is unavailable, rate-limited, returns something unusable, or answers
in the wrong language (a Hindi or Marathi summary must be written in Devanagari). The report says which model wrote it and how many others
were tried. A rejected key stops at once.

**Limits.** Free-tier limits are per model and per organisation, and different sources I found disagree on the exact numbers (about 30
requests a minute, roughly 1,000 requests a day for the main models, and a cap on tokens per minute). Check your real limits at
console.groq.com/settings/limits. Each summary uses a few thousand tokens, and every summary is saved per language, so writing it again
only costs something if you press "Write again". Free tiers change: verify the current terms before you rely on them.

**Privacy.** The text goes to Groq, which hosts the open model. Read Groq's data and privacy terms yourself. Only fictional, acted calls
belong in this demo anyway. The consent box on the report page names where the text goes.

## Other services
Cloudflare Workers AI (`CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, optional `LLM_MODEL`) and any OpenAI-compatible service (Google AI Studio's
OpenAI-compatible endpoint, Cerebras, a local server ...) work too:
```
LLM_PROVIDER=openai
LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=your-key
LLM_MODEL=model-name
```
Provider choice: `LLM_PROVIDER` (`groq`, `cloudflare` or `openai`) if set, else Groq when `GROQ_API_KEY` exists, else Cloudflare when its two keys exist.
With `LLM_PROVIDER=openai` and no `LLM_MODEL`, the app lists the service's models and falls back like it does for Groq.

## Privacy note for the write-up
Audio goes only to Gnani (speech-to-text). Text goes to the AI service only when the person asks for the AI summary. The app works fully
without it.
