# OD WhatsApp Flow — setup (experimental, separate from main bot)

**Does not change** the live OD / visitor / leave / permission chat flows in `Interakt/`.  
This folder is only the Flow **data endpoint** for testing dynamic form fields (e.g. vehicles).

## What this folder is

Separate **Cloud Run service** for the WhatsApp Flow **data endpoint** (`POST /flow`).  
The parent `Interakt/` bot sends **OD - Form** from the menu when `OD_FLOW_TEMPLATE_NAME` is set. Production is unchanged.

## Files

| File | Purpose |
|------|---------|
| `main.py` | Flask `/flow` endpoint (encrypt/decrypt) |
| `od_flow.json` | Import into Meta Flow Builder (OD form layout) |
| `private.pem` | Your RSA private key (do not commit) |
| `vehicles.py` | Reads `vehicles` collection; excludes vehicles already OUT at gate |

## 1. Generate keys (once)

```powershell
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
```

Upload **public.pem** in Meta Flow Builder → Endpoint → Public key.

## 2. Publish flow in Meta / Interakt

1. Create flow → **Import JSON** → paste `od_flow.json` (or rebuild matching screens).
2. Set endpoint URL: `https://YOUR-FLOW-SERVICE.run.app/flow`
3. Run **Ping** test — should return `active`.
4. Publish flow.

## 3. Deploy this service

```powershell
cd "Interakt/Whatsapp Flow"
gcloud run deploy alubee-whatsapp-flow-endpoint `
  --source . `
  --region asia-south1 `
  --project alubee-prod `
  --allow-unauthenticated
```

Grant the Cloud Run service account **Cloud Datastore User** on `whatsapp-approval-system`.

## 4. Test the endpoint only

Use Meta Flow Builder **Ping** and open the form from a test template linked to this endpoint.  
Vehicle dropdown loads when **Company vehicle = Yes**.

Form submit is handled by parent `Interakt/od_request.py` → same JMD → MD approval as chat OD.

**Full walkthrough:** see `../OD_FORM_SETUP.md`.

## 5. Test vehicles

1. Open form from Meta / Interakt test template.
2. Choose **Company vehicle = Yes** → vehicle list loads from Firestore.
3. Submit stays on Meta side until bot integration is added separately.
