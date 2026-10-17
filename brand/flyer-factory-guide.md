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

**AI helper → Gemini → paste key → Test connection → Save → Write it for me → review → Use this → Write the post → Copy**

AI is optional and only available in the factory. Customers see no AI controls on the order page. Start with Gemini on the iPad:

1. Open [Flyer Factory](https://cultureshyftmedia.com/factory/), then tap **AI helper** near **My flyers**.
2. Choose **Gemini**, then tap **Get a free Gemini key**. The key page opens in a new tab only when you tap the link.
3. Sign in with your Google account. Tap **Create API key**, follow any project-selection prompt, and copy the key.
4. Return to the Flyer Factory tab and paste the key into **API key**.
5. Keep the prefilled model unless you want another available model. **Show/Hide** lets you check the pasted key.
6. Tap **Test connection**. When you see **Connected. Gemini answered.**, tap **Save**.
7. Choose an occasion and fill in the details you know. Tap **Write it for me** near Headline.
8. The page moves to a review panel with **Bold**, **Warm**, and **Short** versions from one request. They sit side by side on wide screens and stack on narrow screens. Compare **Your text** and **Suggested**, checking facts, tone and spelling. Tap **Use this** at the top of your chosen version to apply its headline, subheadline, body and call to action. Tap **Use this** under one field to apply only that field. Nothing changes before that tap.
9. Tap **Undo** to restore the exact values from immediately before your last acceptance. It is one level, not a history. A new AI reply keeps Undo available; your own edits clear it so Undo cannot overwrite your manual work.

When the flyer has both its required headline and contact line, **Write the post** becomes available under the social-image downloads. One tap sends the headline, subheadline, date, place, body and call to action to the provider and returns an Instagram caption, up to 8 cleaned hashtags and a Facebook event description. The contact line only unlocks the button; it is never sent. Check that dates, times and addresses match the flyer exactly. Each result box shows its live character count and can be edited for this open page. Tap the **Copy** button under a box to copy only that box; **Copied** confirms success. If browser copying is blocked, the text stays selected so you can use the device’s Copy command. These post results are temporary: they are not added to saved flyers, autosave or exported brief JSON.

The hook preview shows the first 125 characters of your Instagram caption as you edit. Put the main reason to read there. For Facebook, aim for 1,000 characters or fewer; the hard limit is 5,000. Hashtags containing an API key are dropped.

When a field is too long for the chosen layout, a small message appears beneath it and **Make it fit** appears below Layout. This happens when the preview cuts off text or has to reduce its type size by at least a quarter. Checking the fit happens on your device and sends nothing to AI.

1. Tap **Make it fit** to ask your connected AI for shorter wording. Only the overflowing fields, layout name and suggested character budgets are sent. AI is told to preserve meaning and keep names, dates, times, addresses and prices unchanged.
2. Compare **Your text** and **Shorter** side by side, including their character counts. Check every fact yourself: the AI can change a date or lose meaning even when told not to. If a number in the shorter version differs from yours, the panel says **Numbers changed** under that field. Nothing in your flyer changes when the reply arrives, and a reply with an empty shorter version is rejected without replacing anything.
3. Tap **Use this** below one field to replace only that field, or **Use this** at the top to accept all the shown fields. The factory checks the fit again and tells you if text is still too long. You can edit it manually or tap **Make it fit** again.
4. Tap the shared **Undo** button above the review panels to restore the exact values from before the last acceptance. Asking for another reply does not remove Undo. Your own edits clear it.

While a writing request is running, tap its **Cancel** button to stop waiting. A failed, cancelled or timed-out request leaves your flyer and previous suggestions intact. A post reply with an empty caption or description is rejected without replacing any box. Requests time out after 30 seconds; there is no automatic retry. Shortening previews stay only in the open page until you use them; a reload clears unaccepted suggestions.

Every writing request includes the shared CultureShyft voice rules and the exact tagline, “Media made to move people.” AI can still make mistakes; check the result. If a reply has only 1 or 2 usable versions, the panel tells you and shows those choices. You can use one or tap **Write it for me** again. Failed or cancelled requests preserve your flyer and earlier choices; there is no automatic retry. Unaccepted versions stay only in this open page and disappear on reload.

For another provider, choose it in **AI helper** and tap **Get an OpenAI key**, **Get a Claude key**, or **Get an OpenRouter key**. Sign in on the new tab, create and copy a key, return here, paste it, then tap **Test connection** and **Save**. Choosing **Local AI** shows a no-key note instead of a key link.

A free Gemini key does not mean unlimited requests. Limits are per project and visible in AI Studio. A paid upgrade is separate; check its billing terms before enabling it. Google may use free-tier data to improve its products. Do not include private customer details in the flyer text you ask AI about.

| Choice | Setup |
|---|---|
| Gemini (recommended on iPad) | Google AI Studio key; starts with `gemini-3.6-flash`. |
| OpenAI | Your OpenAI API key and API billing; starts with `gpt-6-luna`. A ChatGPT subscription is separate. |
| Claude | Your Anthropic API key and API billing; starts with `claude-haiku-5-5`. |
| OpenRouter | Your OpenRouter key; enter an available `provider/model` identifier and check that model’s costs. |
| Local AI (LM Studio / Ollama) | Enter the model name shown in your server. LM Studio base: `http://localhost:1234/v1`; Ollama: `http://localhost:11434/v1`. No key is required. |

Model names are editable because availability can change. For local AI, in LM Studio **turn on Enable CORS in the Developer tab and Start server**. For Ollama, set `OLLAMA_ORIGINS=https://cultureshyftmedia.com` then restart Ollama. Safari on iPad usually cannot reach a local `http://` server from an https page, so use Gemini on the iPad. `localhost` means the device running the browser, not another computer.

Only tapping **Test connection**, **Write it for me**, **Write the post**, **Make it fit** or **Spanish version** sends an AI request. **Write it for me** sends the selected occasion and headline, subheadline, date, place, body and call to action. **Write the post** sends those same flyer fields except the occasion. **Make it fit** sends only overflowing fields from that list, with the layout and character budgets. None of these writing actions sends the contact field, customer name/email, QR URL or photo. Anything private typed into an allowed text field would still be sent. Suggestions stay on this page until accepted; accepted flyer copy uses the normal brief save/export flow. Post copy stays only on the open page unless included in a separately saved Spanish draft, as explained below.

Your key stays in this browser and is only sent to the company you chose. Settings use one localStorage entry, `cultureshyft.factory.ai.v1`, shaped as `{provider, model, baseUrl, keys:{provider:key}}`. Keys are separate from briefs, exports and draft autosave. This is browser storage, not an encrypted password vault; use a trusted device/browser. If storage is blocked or full, the helper warns once and keeps settings in memory for this open session. Re-enter them after closing the page.

To remove a saved key, open **AI helper**, choose its provider, tap **Forget my key**, and confirm. Repeat for other saved providers. This leaves your flyers intact. If storage cannot update, the helper tries removing its one AI settings entry and explains when other saved AI settings were also removed; current session settings remain available. If removal is blocked too, follow the warning and revoke the key with the provider. Revoke a compromised key at the provider as well. Clearing this site’s data removes AI settings along with other saved factory data, so export your work first.

If a request fails, the helper explains the next step and preserves the form. For a rejected key, create a new one and test it. For a quota limit, wait a minute or try another model. For an unavailable model, enter one your account can use. Check your connection for offline errors. **Cancel** stops waiting; requests time out after 30 seconds and never retry automatically. A provider may already have processed a cancelled request. You can keep writing manually at any time.

## Make a Spanish draft

**Spanish version → compare English | Spanish → Save as Spanish draft → My flyers**

1. Tap **Spanish version** near **Write it for me**. If AI is not connected, the AI helper opens; connect and save your settings, then tap **Spanish version** again. Only this tap sends the headline, subheadline, body and call to action, plus any Instagram caption and Facebook description currently shown. The date, place and contact fields, customer details, QR link and photo are not sent. Details already written inside the translated text are sent, so check for private information first.
2. Compare **English | Spanish** in the preview. The brand name stays CultureShyft and the tagline stays “Media made to move people.” Dates, place and contact are copied exactly into the new draft. Check proper names and every other fact yourself. Warnings beside a Spanish field flag changed or missing numbers, recognized street addresses, URLs and emails; these checks cannot recognize every kind of address or mistake.
3. Edit Spanish text directly in the preview if needed. **Too long — shorten** means the reply exceeds that field’s limit. The full reply stays visible, and saving waits until you shorten it; no sentence is silently cut. Fact warnings remain visible for review but do not prevent saving a draft.
4. Tap **Save as Spanish draft**. Wait for **Spanish draft saved in My flyers**. A separate entry named with the English headline followed by **(Spanish)** appears. Your English form, saved entry and autosave stay unchanged. The Spanish entry also keeps the translated caption and description when present. The save button disables after success to prevent accidental duplicate saves; editing the preview enables another save.
5. Tap **My flyers**, then **Open** on the Spanish entry to work on it. The review note stays visible on its saved card and above the open flyer. Its saved social text appears in the post boxes. Tap **Export brief** for a JSON backup, including the Spanish text, accents and review note; **Import brief** restores it. As with English post copy, later edits made only in the post boxes are temporary.

**Review before printing. Have someone who speaks Spanish check this translation.** This note always appears on the translation preview and saved Spanish entry. Saving does not print or export a PDF automatically.

Tap the Spanish request’s **Cancel** to stop waiting. Requests time out after 30 seconds without retrying. A failed request keeps the English flyer and any earlier preview. If storage is blocked, full or damaged, a **Spanish draft could not be saved** message appears beside the save button; the preview stays available. Copy its Spanish text before closing, allow storage or free space, then tap **Save as Spanish draft** again. Do not clear saved work to resolve a storage warning without exporting it first. To remove an unwanted Spanish draft, use its existing **Delete** confirmation in My flyers after exporting anything you need; the English entry remains separate.

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
