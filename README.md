# WhatsApp Flow endpoint (OD + Visitor forms)

**Does not change** the live chat flows in `Interakt/Production/` unless you enable form menu options.  
This folder is the shared Flow **data endpoint** (`POST /flow`) for OD and Visitor forms.

## What this folder is

Separate **Cloud Run service** for the WhatsApp Flow **data endpoint** (`POST /flow`).  
The parent `Interakt/` bot sends **OD - Form** from the menu when `OD_FLOW_TEMPLATE_NAME` is set. Production is unchanged.

## Files

| File | Purpose |
|------|---------|
| `main.py` | Flask `/flow` endpoint (encrypt/decrypt) |
| `od_flow.json` | Import into Meta Flow Builder (OD form) |
| `visitor_flow.json` | Visitor form |
| `leave_flow.json` | Leave form |
| `permission_flow.json` | Permission form |
| `flow_dispatch.py` | Routes screen id to the right handler |
| `private.pem` | Your RSA private key (do not commit) |
| `vehicles.py` | Reads `vehicles` collection; excludes vehicles already OUT at gate |

## 1. Generate keys (once)

```powershell
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
```

Upload **public.pem** in Meta Flow Builder → Endpoint → Public key.

## 2. Publish flow in Meta / Interakt

1. Create a flow per form in Meta → **Import JSON** (`od_flow.json`, `visitor_flow.json`, `leave_flow.json`, `permission_flow.json`).
2. Set the **same** endpoint URL on both: `https://YOUR-FLOW-SERVICE.run.app/flow`
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

- OD submit → `od_request.py` → same JMD → MD approval as chat OD.
- Visitor submit → `visitor_request.py` → same JMD → MD → OTP as chat visitor.
- Leave submit → `leave_request.py` → same JMD → MD as chat leave.
- Permission submit → `permission_request.py` → JMD/MD or PPC/HR as chat permission.

**OD walkthrough:** see `../OD_FORM_SETUP.md`.

## 5. Test vehicles

1. Open form from Meta / Interakt test template.
2. Choose **Company vehicle = Yes** → vehicle list loads from Firestore.
3. Submit stays on Meta side until bot integration is added separately.
