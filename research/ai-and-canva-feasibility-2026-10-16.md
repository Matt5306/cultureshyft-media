# AI helper and Canva feasibility (researched 2026-10-16)

Legend: **V** = verified today (official page or my own test), **S** = secondary source, **U** = could not verify.

## A. Calling AI from a static browser page

| Question | Answer | Source / status |
|---|---|---|
| Gemini key cost, card? | Free key from Google AI Studio. Google's billing page says new accounts start on the Free Tier; a card/prepaid credit is only described for upgrading to paid. Nothing on those pages says a card is needed for free. | [billing](https://ai.google.dev/gemini-api/docs/billing) (updated 2026-09-28) V; "no card" itself: S ([puter guide](https://developer.puter.com/tutorials/how-to-get-gemini-api-key/)) |
| Free-tier limits | Google no longer publishes numbers; they are shown per project in the AI Studio rate-limit page. Older/third-party figures (5-10 requests/min) vary. Free-tier data may be used to improve Google products. | [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) (2026-10-15) V; [pricing](https://ai.google.dev/gemini-api/docs/pricing) (2026-10-15) V |
| Gemini CORS, `x-goog-api-key` | **Works.** I sent a real preflight from Origin `https://cultureshyftmedia.com`: HTTP 200, `Access-Control-Allow-Origin` echoed, `Allow-Headers: content-type,x-goog-api-key`. A bad-key GET returned a readable 400 with CORS headers. | My curl test 2026-10-16 V (real POST with a live key not run) |
| Gemini model ids | `gemini-3.6-flash` (default, free tier), `gemini-3.8-flash` (newest), `gemini-3.5-flash-lite` (cheapest/fastest). 2.5 models are restricted to prior users; 2.0 shut down. `gemini-flash-latest` alias target is undocumented, so pin ids. | [models](https://ai.google.dev/gemini-api/docs/models) (2026-10-13) V |
| Gemini OpenAI-compatible | Base `https://generativelanguage.googleapis.com/v1beta/openai/`, Bearer key. Preflight with `authorization` header also passes CORS. Docs do not mention browsers. | [docs](https://ai.google.dev/gemini-api/docs/openai) V; CORS by my test V |
| OpenAI | Preflight OK (origin echoed, `authorization` allowed). Fast model: `gpt-6-luna`; flagship `gpt-6-astra`. Pay-as-you-go prepaid key, no free tier (U). Key in a browser is allowed but OpenAI discourages it. | My test V; [models](https://developers.openai.com/api/docs/models) (undated) |
| Anthropic | Needs header `anthropic-dangerous-direct-browser-access: true`; preflight allows it (`allow-origin: *`). Cheap model `claude-haiku-5-5`, balanced `claude-sonnet-5-5`. Paid API key only. | My test V; [models](https://platform.claude.com/docs/en/about-claude/models/overview) V |
| OpenRouter | Preflight OK (`allow-origin: *`, `Authorization` allowed). Has some free models (U: which today). | My test V |
| Ollama | Default allows only 127.0.0.1/0.0.0.0 origins. Page on cultureshyftmedia.com needs `OLLAMA_ORIGINS=https://cultureshyftmedia.com` (Windows: env var then restart Ollama). OpenAI-compatible path is `http://localhost:11434/v1` (from memory, U today). | [FAQ](https://docs.ollama.com/faq) V |
| LM Studio | Developer tab has an **Enable CORS** switch and port setting; "Serve on Local Network" for other devices. Default port 1234, `/v1` base (memory, U today). | [docs](https://lmstudio.ai/docs/developer/core/server/settings) V (partial) |
| https page to `http://localhost` | Chrome: allowed, but newer versions show a "local network" permission prompt. Safari/iPad: WebKit blocks it as mixed content (reports conflict on current status). **Treat local AI as desktop-Chrome only; on the iPad the realistic route is a cloud provider.** A Mac/PC on the LAN over http will also be blocked from https. | [Chrome LNA](https://developer.chrome.com/blog/local-network-access) (2025-06-09) S; [WebKit bug](https://bugs.webkit.org/show_bug.cgi?id=279249) S, status U |

**Verdict:** Gemini direct from the browser is feasible with no backend. The key sits in that browser's storage, so it must be a free, low-stakes key that Mark can revoke.

## B. Canva options, least to most work

| # | Option | Effort | Findings |
|---|---|---|---|
| 1 | Download PDF/PNG, upload to Canva | None; works today | Canva's PDF import turns pages into editable text, images and shapes; fonts may be swapped, layout can shift, scans do not convert. Same on Free. iPad steps (+ > Upload) are inferred from phone-app guidance: U. ([outilstice 2026-03](https://outilstice.com/en/2026/03/transformer-un-pdf-en-document-modifiable-avec-canva/) S) |
| 2 | Canva Connect API | Needs a backend | Token exchange requires client id + secret and "can't be made from a web-browser client" ([auth docs](https://www.canva.dev/docs/connect/authentication/) V), plus PKCE. So a tiny Cloudflare Worker is required. Design Import (`POST /v1/imports`, scope `design:content:write`, 20 req/min, returns `edit_url` valid 30 days) fits our need ([ref](https://www.canva.dev/docs/connect/api-reference/design-imports/create-design-import-job/) V; PDF support not stated on that page, U). Autofill and Brand Templates need Canva Enterprise for developer and users ([S](https://www.canva.dev/docs/connect/reference-apps/nourish/)). Private integrations are Enterprise-only ([creating](https://www.canva.dev/docs/connect/creating-integrations/) V, that page covers apps); public ones need Canva review. Whether a Draft integration can serve one non-Enterprise account: U. |
| 3 | Canva Apps SDK app | Highest | Real app bundle; public apps go through Canva review, team apps need Enterprise and admin approval ([submit docs](https://www.canva.dev/docs/extensions/platform-concepts/apps/public-apps/submit-public-app/) S). Not worth it for one user. |
| 4 | Canva Button / share link | Dead | Button API ended outside China on 2025-12-30 ([Canva help](https://www.canva.com/help/canva-button/) S). No equivalent share-to-Canva link found. |

**Recommendation for Mark:** Use option 1 now (add a clear "Open in Canva" guide: Save PDF, Canva app > + > Upload, edit). It costs nothing and needs no accounts beyond the Canva login he has. Only consider option 2 (Worker plus a Canva developer integration) if Mark asks for one-tap import; Matt would create a Canva developer app and a free Cloudflare Worker holding the client secret, and Canva's rules for a non-Enterprise single user must be re-checked first.

## C. Multi-provider AI client: adopt, wrap or build

- Exists: Vercel AI SDK, LiteLLM, LangChain.js, `openai` and `@google/genai` SDKs; all assume a bundler or are heavy, and none is no-build.
- Small BYOK pieces exist (chat UIs such as Open WebUI / LibreChat), but they are apps, not embeddable libraries; license and fit not reviewed.
- All target providers expose one of three simple JSON shapes, and I confirmed CORS for each.
- **Recommendation: build** about 120 lines of `fetch` adapters (Gemini native, OpenAI-compatible, Anthropic Messages). No dependency, no build step, easy to mock in tests.
- Revisit libraries only if more providers or streaming are added.
