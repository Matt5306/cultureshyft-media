# Mark’s 10-minute Flyer Factory guide

**Order → check details → make invoice → proof → deliver**

Use [Flyer Factory](https://cultureshyftmedia.com/factory/) and share the [order form](https://cultureshyftmedia.com/order/) once this branch has been reviewed and published. These links do not publish the work by themselves. No account or installation is needed.

The 10 minutes cover preparing a straightforward order. Customer approval and payment happen on their own schedule. Prices in `brand/pricing.md` remain draft prices for Mark’s approval.

| Time | What you do | What you should see |
|---|---|---|
| 0–2 min | Open the customer’s brief link from their email. | The headline, details, customer information and requested extras fill in. |
| 2–4 min | Check every detail. Add the supplied photo if needed. | A live Letter preview. Choose a sample only if you want to replace the event copy. |
| 4–6 min | Choose **Make invoice**, confirm the extras and due date, then save the invoice. | The total, 50% deposit and delivery balance, with your payment details. |
| 6–8 min | Download a square proof and send it for approval. | A 1080 × 1080 PNG with the headline, date and place. |
| 8–10 min | After approval, save the final Letter PDF and agreed images. | Files ready to attach to the delivery message. Collect the balance on delivery. |

## 1. Get a usable order

The customer chooses a sample, replaces its made-up details, enters their name and reply email, and checks the draft. **Send to Mark** opens their email app with a readable brief and a link. They must review and press Send there; the website does not send email itself.

If the email app does not open, use **Copy request** and paste into an email to **mark@cultureshyftmedia.com**. If automatic copying is blocked, select the text and use the phone’s Copy command. Long briefs use the same text fallback. Ask customers to attach photos separately; photos are not included in the link. If a link is missing or damaged, use the readable text to fill the brief manually.

Brief links keep customer details in the browser-only `#brief=` part of the address, rather than the server-visible query string. Send them only to the people working on that order. The order page does not autosave: copy the request before leaving it.

## 2. Turn the brief into a flyer

**Sample → replace details → check preview → Save to My flyers**

Choose Sunday service, Youth night, Fundraiser, Concert / worship night, Small-business sale, Grand opening, Community event, or Hiring. A sample replaces the flyer copy, layout and orange setting; customer details and the current photo stay in place.

Check spelling, dates, times, address, public contact and QR destination. Customer reply email and public flyer contact are separate fields. For youth work, confirm ages, adult contact and parent-facing details.

Use a JPG, PNG or WebP photo under 12 MB. Drag it in the preview and adjust zoom. Announcement is a type-only layout. If you see “…” or a shortening warning, shorten the copy and check each downloaded image: the square deliberately has less text than the story.

Choose **Save to My flyers** to keep the job on this device. A received link or demo does not replace your previous autosave until you explicitly save it. **Export brief** makes a JSON backup containing the full brief and photo; **Import brief** restores it on another device. Save a backup with each customer’s delivery files.

## Connect your AI

**AI helper → Gemini → paste key → Test connection → Save → Write it for me → review → Use this**

AI is optional and only available in the factory. Customers see no AI controls on the order page. Start with Gemini on the iPad:

1. Open [Google AI Studio](https://aistudio.google.com/) in Safari on the iPad.
2. Sign in with your Google account.
3. Tap **Get API key**, then **Create API key**. Follow any project-selection prompt and copy the key.
4. Open [Flyer Factory](https://cultureshyftmedia.com/factory/), then tap **AI helper** near **My flyers**.
5. Choose **Gemini**, paste the key, and keep the prefilled model unless you want another available model. **Show/Hide** lets you check the pasted key.
6. Tap **Test connection**. When you see **Connected. Gemini answered.**, tap **Save**.
7. Choose an occasion and fill in the details you know. Tap **Write it for me** near Headline.
8. Compare **Your text** and **Suggested**. Check facts, tone and spelling. Tap **Use this** for the whole set or one field. Nothing changes before that tap. **Undo** restores the values from immediately before your last acceptance; it is one level, not a history.

A free Gemini key does not mean unlimited requests. Limits are per project and visible in AI Studio. A paid upgrade is separate; check its billing terms before enabling it. Google may use free-tier data to improve its products. Do not include private customer details in the flyer text you ask AI about.

| Choice | Setup |
|---|---|
| Gemini (recommended on iPad) | Google AI Studio key; starts with `gemini-3.6-flash`. |
| OpenAI | Your OpenAI API key and API billing; starts with `gpt-6-luna`. A ChatGPT subscription is separate. |
| Claude | Your Anthropic API key and API billing; starts with `claude-haiku-5-5`. |
| OpenRouter | Your OpenRouter key; enter an available `provider/model` identifier and check that model’s costs. |
| Local AI (LM Studio / Ollama) | Enter the model name shown in your server. LM Studio base: `http://localhost:1234/v1`; Ollama: `http://localhost:11434/v1`. No key is required. |

Model names are editable because availability can change. For local AI, in LM Studio **turn on Enable CORS in the Developer tab and Start server**. For Ollama, set `OLLAMA_ORIGINS=https://cultureshyftmedia.com` then restart Ollama. Safari on iPad usually cannot reach a local `http://` server from an https page, so use Gemini on the iPad. `localhost` means the device running the browser, not another computer.

Only tapping **Test connection** or **Write it for me** sends an AI request. Writing sends the selected occasion and headline, subheadline, date, place, body and call to action. It does not send the contact field, customer name/email, QR URL or photo. Anything private typed into an allowed text field would still be sent. Suggestions stay on this page until accepted; accepted copy uses the normal brief save/export flow.

Your key stays in this browser and is only sent to the company you chose. Settings use one localStorage entry, `cultureshyft.factory.ai.v1`, shaped as `{provider, model, baseUrl, keys:{provider:key}}`. Keys are separate from briefs, exports and draft autosave. This is browser storage, not an encrypted password vault; use a trusted device/browser. If storage is blocked or full, the helper warns once and keeps settings in memory for this open session. Re-enter them after closing the page.

To remove a saved key, open **AI helper**, choose its provider, tap **Forget my key**, and confirm. Repeat for other saved providers. This leaves your flyers intact. If storage cannot update, the helper tries removing its one AI settings entry and explains when other saved AI settings were also removed; current session settings remain available. If removal is blocked too, follow the warning and revoke the key with the provider. Revoke a compromised key at the provider as well. Clearing this site’s data removes AI settings along with other saved factory data, so export your work first.

If a request fails, the helper explains the next step and preserves the form. For a rejected key, create a new one and test it. For a quota limit, wait a minute or try another model. For an unavailable model, enter one your account can use. Check your connection for offline errors. **Cancel** stops waiting; requests time out after 30 seconds and never retry automatically. A provider may already have processed a cancelled request. You can keep writing manually at any time.

## 3. Invoice and get paid

**Confirm scope → invoice → deposit → work → balance on delivery**

In the factory, choose **Make invoice**. The customer and requested extras come from the brief. Check the quantities before sending:

| Item | Price |
|---|---:|
| Flyer: Letter PDF, Instagram square, 1 edit round | $20 |
| Additional size | $5 each |
| Additional edit round | $5 each |
| Commercial print preparation | +$10 per flyer |
| Rush, only when you have a slot | +$15 per flyer |

The invoice shows a 50% deposit and the remaining 50% due on delivery. Set the due date to the date you agree with the customer. Confirm extras before doing them. A different event, offer or design is another $20 flyer. Custom writing and illustration need a separate quote.

Open invoice **Settings** once on each device. Replace the deliberately fake `$YourCashtag`, `you@example.com` and `paypal.me/YourName` placeholders with your actual Cash App cashtag, Zelle email/phone and/or PayPal.me link, then save. Check the printed text and payment links before sending. These settings stay in this browser; they are not shared across devices.

Invoice numbers use `CSM-YYYYMMDD-NN`, with a daily counter on this browser. Use one device/browser for issuing invoices to avoid duplicate numbers across devices. Keep exported invoices as your record. If browser storage fails or is cleared, check your last issued number before making another invoice. The page explains when saving fails.

Save the invoice as a Letter PDF or download its **1080 × 1350 PNG** for texting. This image is an invoice/payment request, not proof that money was received. Confirm payment in your payment app before calling it paid. Payment links are shortcuts; the factory does not process or track payments.

## 4. Save a clean PDF

| Print setting | Choose |
|---|---|
| Destination / printer | Save as PDF |
| Paper | US Letter, 8.5 × 11 inches |
| Orientation | Portrait |
| Scale | 100% / actual size |
| Margins | None |
| Headers and footers | Off |
| Background graphics | On |
| Pages | Confirm the preview shows exactly 1 page |

Choose **Save as PDF** for the flyer, or the invoice’s PDF button for the invoice. If your phone does not expose all settings, inspect its PDF preview for the correct single page and colors. The page supplies Letter sizing automatically.

This PDF is for home or office printing. The $10 commercial print add-on still requires the printer’s bleed, crop-mark and color specifications; the factory does not automatically prepare that version.

## 5. Find and send your files

| Device | Where to look |
|---|---|
| iPhone / iPad | Safari downloads normally appear in Files → Browse → iCloud Drive or On My iPhone → Downloads, depending on Safari settings. In the print sheet, open/expand the preview and use Share → Save to Files if no PDF destination is shown. |
| Android | Chrome downloads normally appear in Files / My Files → Downloads. In Print, choose Save as PDF, then choose the folder. |
| Computer | Your browser’s Downloads list or the folder you selected in the save dialog. |

PNG files may land in Files rather than Photos. Open the image and use Share / Save Image if you want a photo-library copy. If a download button seems to do nothing, check the browser download list; keep the brief open and try again. Do not clear browser data while recovering work.

Rename files by customer, event and version, for example `grace-youth-night-proof-v1.png` and `grace-youth-night-final-letter.pdf`. Download names may repeat, so check the newest file before attaching.

Send a proof message like: “Here’s your draft. Please check the wording, date, time, address and contact. Reply with one collected list of edits, or ‘Approved.’” Check the square and Letter PDF separately; send a story proof if the customer ordered that size. After approval, send the final files as attachments so messaging apps do not reduce image quality. Ask the customer to confirm the files open.

## Recovery and safe removal

| Problem | Next safe action |
|---|---|
| Sample list does not load | Your open brief stays intact. Enter the details manually or reload after exporting your work. |
| Brief link is invalid or too long | Ask for the copied request text. Existing saved flyers are preserved. |
| Font, logo, photo or export fails | Keep the page open, export the brief, then reload and try once more. Check the preview before sending. |
| Storage is blocked or full | Export the brief and invoice before closing. Keep payment details separately. Follow the page’s warning; do not rely on autosave. |
| Wrong changes | Import your last exported JSON brief. For an invoice, use your saved PDF/PNG as the record while correcting a new draft. |

There is nothing to uninstall. To stop using the factory, export your briefs, invoices and payment details first, then close the page. Clearing this site’s browser data removes this device’s saved drafts, invoice settings and number counter; it does not remove downloaded files. Avoid clearing other sites’ data. After a website update, your exported JSON briefs remain your recovery copies.
