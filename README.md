# DocuVerify

DocuVerify is a document-forensics workspace. It analyzes uploaded PDFs and images, collects independent digital evidence, fuses that evidence into a **manipulation risk assessment**, and can explain the completed result in plain language.

It is a decision-support product. It does **not** prove that a document is authentic or forged, does **not** verify that a signature belongs to a named person, and does **not** replace a government registry.

Version 2 can query **configured** PAN and GST verification APIs for Government Bid Compliance. Those results are provider responses, not legal proof or government approval.

## Product boundary

- Forensic **risk assessment** from available digital evidence
- Optional **configured** PAN/GST identifier verification (Government Bid Compliance)
- Not legal proof of authenticity or forgery
- Not signer-identity verification
- Not a substitute for official government registries beyond the APIs you configure
- The AI layer explains completed forensic results only. It cannot change scores, invent findings, override fusion, or decide compliance status.

## Version 2 — two product modules

The home page presents two workspaces:

1. **Document Forensics** (`/forensics`) — the existing multi-layer forensic workflow, unchanged.
2. **Government Bid Compliance** (`/compliance`) — Udyam certificate intake: extract PAN and GSTIN, verify them through configured backend APIs, and run the existing forensic pipeline **in parallel**, then aggregate a deterministic compliance status.

### Government Bid Compliance architecture

Upload certificate → extract identifiers (existing OCR/text stack) → **parallel** PAN API + GSTIN API + local forensic analysis → deterministic aggregation → PDF report.

PAN/GST outcomes mean “did the configured verification source validate this identifier?” Forensic integrity means “does the certificate show digital manipulation evidence?” Those domains are not averaged.

**COMPLIANT** only if PAN passed, GSTIN passed, and integrity is no meaningful / low risk. **HIGH_RISK** for high forensic risk or combined identifier failures — never solely because an API is down. **INCONCLUSIVE** when identifiers are missing or services/coverage cannot support a conclusion. Otherwise **REVIEW_REQUIRED**.

## Version 3 — Certificate Analyzer

A third workspace (`/signatures`) analyzes the **full certificate** for digital manipulation, suspicious content/layout evidence, and signature-region integrity. Optional reference-signature comparison remains available and is **not required**.

The three evidence streams stay independent: document content integrity, signature integrity, and reference similarity. The product does not claim legal authenticity, legal forgery, or signer identity. Manual signature confirmation is requested only when automatic detection is uncertain; full-document findings still complete first.

Reference images are stored under the backend upload directory and are not public URLs. There is no multi-user access control; this is a local workspace.

No additional environment variables are required.



## Architecture overview

```
frontend (Next.js App Router)
  └─ /api/v1  →  FastAPI
                  ├─ upload validation + SHA-256
                  ├─ preprocessing (PyMuPDF / Pillow / OpenCV)
                  ├─ metadata forensics
                  ├─ visual forensics (ELA, copy-move)
                  ├─ document intelligence (native text / Tesseract OCR)
                  ├─ deterministic evidence fusion
                  ├─ optional AI explanation (OpenAI-compatible API)
                  ├─ government bid compliance (PAN/GST adapters + parallel forensics)
                  ├─ forensic / compliance PDF reports
                  └─ SQLite via SQLAlchemy + Alembic
```

### Analysis stages

1. Preprocessing + metadata
2. Visual forensics (ELA and copy-move)
3. Document intelligence (OCR/text, fields, logical checks)
4. Deterministic evidence fusion and risk assessment
5. AI explanation of existing evidence (or a deterministic fallback)

### Tech stack mapping

| Capability | Implementation |
|---|---|
| Computer vision | OpenCV ELA heatmaps and copy-move geometric verification |
| OCR | Tesseract on scans/images; native PDF text via PyMuPDF |
| Document intelligence | Field extraction and internal logical consistency checks |
| Anomaly detection | Metadata signals, localized ELA residuals, cloned-region clusters |
| Explainable scoring | Rule-based fusion with reliability, coverage, and corroboration |
| NLP / AI explanation | Optional server-side OpenAI-compatible chat JSON, grounded in stored results |

## Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer (20+ recommended)
- npm
- Optional: Tesseract OCR for scanned documents
- Optional: an OpenAI-compatible API key for AI explanations (the product works without it)

## Backend setup

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

On macOS/Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Environment configuration

`backend/.env` (see `backend/.env.example`):

| Variable | Purpose |
|---|---|
| `APP_ENV` | Environment name (`development`, `test`, …). OpenAPI `/docs` is enabled only for `development` and `test`. |
| `DEMO_API_TOKEN` | Shared secret for `X-Demo-Token` (required on document, compliance, and certificate routes) |
| `DATABASE_URL` | SQLAlchemy URL. Default: `sqlite:///./docuverify.db` |
| `UPLOAD_DIR` | Directory for original uploads |
| `PROCESSED_DIR` | Directory for rendered processing images |
| `MAX_UPLOAD_SIZE_MB` | Maximum upload size in megabytes |
| `CORS_ORIGINS` | Comma-separated browser origins (include the Next.js origin) |
| `LOG_LEVEL` | Logging level (`INFO`, `DEBUG`, …) |
| `TESSERACT_CMD` | Optional full path to `tesseract.exe` if it is not on PATH |
| `AI_PROVIDER` | `openai` (OpenAI-compatible Chat Completions). Use `none` to force fallback |
| `AI_API_KEY` | Server-side API key. Never sent to the browser |
| `AI_MODEL` | Model name (default `gpt-4o-mini`) |
| `AI_BASE_URL` | Chat Completions base URL (default `https://api.openai.com/v1`) |
| `PAN_API_KEY` | Sandbox.co.in API key (`x-api-key`) |
| `PAN_API_SECRET` | Sandbox.co.in API secret (`x-api-secret`) |
| `PAN_SANDBOX_ENV` | `test` (default) or `live` |
| `GST_IN_CHECK` | GSTIN Check API key from gstincheck.co.in (the only GST credential) |

`frontend/.env.local` (see `frontend/.env.local.example`):

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_DEMO_TOKEN=change-me-local-demo-token
```

`NEXT_PUBLIC_DEMO_TOKEN` must match `DEMO_API_TOKEN`. The browser sends it as `X-Demo-Token` (and as `token` on image/report URLs).

### PAN and GST API configuration

Set these in `backend/.env` only.

**PAN (Sandbox.co.in)**

1. `PAN_API_KEY` — Sandbox API key.
2. `PAN_API_SECRET` — Sandbox API secret.
3. `PAN_SANDBOX_ENV` — `test` uses `https://test-api.sandbox.co.in`; `live` uses `https://api.sandbox.co.in`. Keys starting with `key_live` also use live.

The adapter authenticates with `POST /authenticate` (`x-api-key`, `x-api-secret`), then calls `POST /kyc/pan/verify`. Sandbox requires a name and a date of birth/incorporation; those are taken from the certificate when present. They are not invented.

**GSTIN (gstincheck.co.in)**

1. `GST_IN_CHECK` — the single API key from GSTIN Check. No other GST variables are used.

The adapter calls `GET https://sheet.gstincheck.co.in/check/<GSTIN>` and sends the key in the `x-api-key` header.

If either credential is empty, that check is recorded as `unavailable` and the rest of the workflow still runs. Keys never go to the frontend.


## Database migration

From `backend/` with the virtualenv active:

```bash
alembic upgrade head
```

The API also creates missing tables on startup (`create_all`) so a first run works even before migrations. Use Alembic for schema evolution.

## Backend startup

From `backend/`:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check: `GET http://127.0.0.1:8000/api/v1/health`

## Frontend setup

```powershell
cd frontend
copy .env.local.example .env.local
npm install
```

## Frontend startup

```bash
npm run dev
```

Open `http://localhost:3000`. Keep the backend running on port 8000.

## API endpoint examples

Health:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Analyze a PDF:

```bash
curl -H "X-Demo-Token: YOUR_DEMO_TOKEN" -F "file=@./sample.pdf" http://127.0.0.1:8000/api/v1/documents/analyze
```

Analyze an image:

```bash
curl -H "X-Demo-Token: YOUR_DEMO_TOKEN" -F "file=@./sample.png" http://127.0.0.1:8000/api/v1/documents/analyze
```

Retrieve an analysis (replace the id):

```bash
curl -H "X-Demo-Token: YOUR_DEMO_TOKEN" http://127.0.0.1:8000/api/v1/documents/ANALYSIS_ID
```

Successful analyses return status `COMPLETE` after evidence fusion. Internal filesystem paths are stored server-side and are not included in API responses.

## How to upload and test a PDF

1. Start backend and frontend.
2. Open the workspace at `http://localhost:3000`.
3. Drop a `.pdf` onto the upload panel (or browse).
4. Click **Analyze document**.
5. Confirm the overview shows filename, `native_pdf` or `scanned_pdf`, page count, shortened SHA-256, and `COMPLETE`.
6. Confirm the metadata panel shows the real `suspicion_score`, `confidence`, signals, and summary from the API.
7. Open the analysis ID link to `/analysis/[id]` and confirm GET-by-id loads the same record.

A PDF with substantial selectable text is classified `native_pdf`. A PDF with little or no extractable text is classified `scanned_pdf`. Classification does not treat a few stray characters as native text.

## How to upload and test an image

1. Upload a `.jpg`, `.jpeg`, or `.png`.
2. Confirm `document_type` is `image`, page count is `1`, and width/height match the processing copy.
3. Metadata forensics should reflect EXIF when present. Missing EXIF is a low-weight signal, not a high suspicion score.

## Implementation notes

- `app/services/orchestration.py` stores the upload, then runs the pipeline in a background thread with real `pipeline_stage` values.
- `app/services/fusion/` remains the source of truth for scores and risk level.
- `app/services/ai/` builds a path-free context and optionally calls an OpenAI-compatible provider. Failures fall back to the fusion summary.
- `app/services/report/` builds a PDF from stored results and existing evidence images only.
- Evidence images live under `processed/{analysis_id}/forensics/` and are served only through the artifact endpoint.
- Public schemas strip internal processing paths. API keys never appear in responses.

## What Phase 1 implements

- Secure upload of PDF, JPG, JPEG, PNG
- SHA-256 of original bytes
- PDF vs image detection
- `native_pdf` / `scanned_pdf` classification from extractable text
- ~300 DPI page rendering for PDFs; RGB processing copies for images
- Metadata forensics for PDFs and images
- Persistence and `GET /api/v1/documents/{id}`
- Analysis workspace UI and `/analysis/[id]`

## What Phase 2 implements

- Error Level Analysis on Phase 1 processing page images
- Copy-move / cloned-region detection (ORB + geometric verification)
- Page-level and document-level scores, independent per module
- Real ELA heatmaps and copy-move overlays
- `GET /api/v1/documents/{analysis_id}/artifacts/{artifact_id}` for safe evidence access
- Visual forensics UI with an evidence viewer (zoom / fit / reset)

ELA recompresses each processing image as JPEG and measures residual error. Scoring prefers localized, high-contrast residual clusters over a high global mean. JPEG inputs receive higher analysis quality; PNG and PDF-raster pages are marked `limited`.

Copy-move uses ORB descriptors, Lowe-ratio matching, a minimum spatial distance, and RANSAC affine/homography verification. Compact cloned blocks can raise suspicion; scattered letter/template matches are filtered.

These techniques produce forensic **signals**, not proof. The product never labels a file authentic, fake, or forged in Phase 2.

### How to test visual forensics

1. Run backend and frontend, upload a JPEG or PNG.
2. Confirm the Visual Forensics section shows real ELA suspicion/confidence/quality and a heatmap loaded from the artifact API.
3. Upload an image that contains an obvious copied-and-pasted patch. Confirm copy-move metrics and, when verified, source/match boxes plus an overlay.
4. Confirm the UI states that analysis is incomplete and does not show AUTHENTIC/FAKE/FORGED.

Fetch an evidence image:

```bash
curl -O http://127.0.0.1:8000/api/v1/documents/ANALYSIS_ID/artifacts/p001_ela
```

Artifact IDs come from the analysis JSON (`ela.pages[].evidence[].artifact_id`). Internal filesystem paths are not returned.

### Phase 2 migration

From `backend/`:

```bash
alembic upgrade head
```

This applies `0002_visual_forensics` (JSON columns for ELA, copy-move, and combined visual results). No new Python packages are required beyond Phase 1 (`opencv-python-headless`, NumPy, Pillow).

## What Phase 3 implements

- Native PDF text extraction (PyMuPDF blocks/spans/bboxes) without OCR when the file is a native PDF
- Tesseract OCR for scanned PDFs and images, on **copies** of processing images only
- Structured field extraction (regex/labels) when values are actually present
- Lightweight document class: `invoice`, `certificate`, or `generic_document`
- Deterministic logical checks: DOB/age, date order, invoice arithmetic, duplicate fields, identifier format, optional QR vs printed identifier
- Independent document-intelligence suspicion score (not a final fusion verdict)
- UI section for extraction, fields, and consistency results

Text extraction uses native PDF text first. OCR runs only for images and scanned PDFs. Missing Tesseract is recorded as failed extraction, not as tampering.

Logical checks look for **internal** contradictions (for example quantity × price ≠ line total). They do **not** look up government or university registries.

### Tesseract setup (Windows)

1. Install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (this environment used v5.5).
2. Confirm `tesseract` is on PATH, or set `TESSERACT_CMD` in `backend/.env` to the full `tesseract.exe` path.
3. `pip install -r requirements.txt` includes `pytesseract`.

No cloud OCR and no LLM are used.

### Phase 3 migration

```bash
alembic upgrade head
```

Adds `document_intelligence_result_json`.

### How to test document intelligence

- **Invoice:** a PDF with labeled Invoice Number, Quantity, Unit Price, Line Total, Subtotal, Tax, Total. Matching arithmetic should `pass`; a wrong total should `fail`.
- **Certificate:** labeled Date of Birth, Age, and Issue Date. Matching age should `pass`; a clearly wrong age should `fail`.
- **Generic document:** ordinary prose. Checks should be `insufficient_data` / `not_applicable`, not fabricated failures.

### Known limitations of Phase 3

- Field extraction is pattern-based and will miss unlabeled or unusual layouts
- OCR quality depends on Tesseract and image clarity
- Birthday-aware age uses the issue date when present; otherwise today's date is a limited fallback
- QR comparison uses OpenCV's QR detector only and fails gracefully
- No fusion-stage authenticity verdict (Phase 4 adds risk assessment, not legal proof)

## What Phase 4 implements

Evidence fusion and explainable risk assessment. After metadata, ELA, copy-move, and document intelligence finish (or are recorded as failed/limited), a dedicated fusion module reads those **actual** results and produces:

- `overall_risk_score` (0–100)
- `risk_level` (`LOW` | `MODERATE` | `ELEVATED` | `HIGH` | `INCONCLUSIVE`)
- `assessment_confidence` and `analysis_coverage` (0.0–1.0)
- layer contributions, corroboration, ranked top findings, limitations, and a recommended action

This is **deterministic rule-based fusion**, not a trained machine-learning model and not an LLM. Scores are never generated by averaging the four layer scores.

### Why scores are not averaged

A naive mean hides both problems the product must show:

- One strong layer (metadata 90, others 0) would be washed down to a mild average.
- Several independent moderate layers would look no stronger than a single moderate layer.

Fusion instead uses **reliability-weighted effective scores** (`raw_score × reliability`) and lets the strongest effective layer dominate:

`base = 0.70 × max + 0.20 × second + 0.10 × mean(rest)`

### Reliability weighting

Each layer’s influence is scaled by analysis quality, not by the raw suspicion number alone.

- Metadata: lower reliability when evidence is only missing/stripped fields. Missing metadata is **not** treated as proof of manipulation.
- ELA: scaled by `analysis_quality` (high / medium / limited). Limited source formats contribute less.
- Copy-move: high reliability requires geometrically verified matches or suspicious clusters. Raw ORB matches alone do not.
- Document intelligence: scaled by extraction quality. A high-confidence arithmetic contradiction on clean native text is more reliable than a contradiction from poor OCR.

A score of 80 with reliability 0.90 influences the result more than 80 with reliability 0.20.

### Independent corroboration

If two or more **independent** layers each show meaningful evidence (not noise-level scores), a capped bonus is added (10 / 16 / 20 for 2 / 3 / 4 layers). One isolated layer gets **no** bonus. Related signals inside a single layer are grouped so five similar timestamp notes cannot count as five independent discoveries.

Isolated strong evidence is still preserved: a high-reliability copy-move result can produce elevated risk even when other layers are clean. The explanation states that independent corroboration was not found.

### Analysis coverage and assessment confidence

- **Coverage** measures how much of the intended four-layer analysis completed with usable quality. Failed and unavailable layers add no coverage. Limited layers add less.
- **Confidence** measures trust in the *assessment itself*. It rises with coverage, reliability, and corroboration, and falls when few layers completed.

Coverage is not risk. A clean file with almost no successful analysis is `INCONCLUSIVE`, not automatically `LOW`.

### Risk-level definitions

| Level | Meaning |
|---|---|
| `LOW` | Little or no meaningful manipulation evidence, with sufficient coverage |
| `MODERATE` | Some signals; evidence is limited, weak, or insufficiently corroborated |
| `ELEVATED` | Meaningful evidence and/or multiple independent layers indicate potential manipulation |
| `HIGH` | Strong, high-reliability evidence, especially with independent corroboration |
| `INCONCLUSIVE` | Coverage or quality is too limited for a meaningful risk assessment |

Recommended actions are decision-support only: no additional action, manual review, priority manual review, or reanalyze with a higher-quality source. The system does **not** approve or reject documents.

### What Phase 4 does not claim

- Not legal proof of forgery or authenticity
- Does not verify that a signature belongs to the claimed person
- Does not confirm records against external registries
- Does not use an LLM for scoring or forensic reasoning

Language in the API and UI is restricted to manipulation **risk** (low / moderate / elevated / high) or an inconclusive assessment.

### Phase 4 migration

```bash
alembic upgrade head
```

Adds `fusion_result_json`, `overall_risk_score`, `risk_level`, `assessment_confidence`, and `analysis_coverage`.

## What Phase 5 implements

Final productization on top of Phases 1–4:

- Evidence-grounded AI explanation (`GET /api/v1/documents/{id}/explanation`)
- Contextual Q&A (`POST /api/v1/documents/{id}/ask`) restricted to the opened analysis
- Analysis history (`GET /api/v1/documents`) and `/history` UI
- Live pipeline stages on the analysis page
- Downloadable forensic PDF (`GET /api/v1/documents/{id}/report`)
- Deterministic fallback when no API key or the provider fails

AI never recalculates `overall_risk_score` or `risk_level`.

### Phase 5 migration

```bash
alembic upgrade head
```

Adds `pipeline_stage`, `ai_explanation_json`, and `ai_explanation_created_at`.

### How to run a full end-to-end analysis

1. Start backend and frontend.
2. Open the home page and choose **Document Forensics** (`/forensics`) or **Government Bid Compliance** (`/compliance`).
3. For forensics: upload a supported file; the app opens `/analysis/{id}`.
4. For compliance: upload an Udyam certificate; the app opens `/compliance/{id}` and runs PAN, GSTIN, and integrity checks in parallel.
4. Confirm risk assessment, technical evidence, and either an AI explanation or the deterministic fallback.
5. Ask a question in the analysis assistant.
6. Open **Analysis History** and reopen the same record.
7. Download the forensic report.

### How to generate the report

From the completed analysis page, use **Download report**, or:

```bash
curl -O -J http://127.0.0.1:8000/api/v1/documents/ANALYSIS_ID/report
curl -O -J http://127.0.0.1:8000/api/v1/compliance/COMPLIANCE_ID/report
```

### Demo sample files

These are real files, not mocked results:

```powershell
cd demo
python generate_samples.py
```

Then analyze:

1. `01-normal.pdf` — ordinary native PDF
2. `02-scanned-like.png` — image/OCR path
3. `03-edited-metadata.pdf` — editor metadata tags
4. `04-copy-move.png` — cloned visual region
5. `05-arithmetic-inconsistency.pdf` — invoice totals that do not add up

### Known limitations of the final product

- Prototype-level security (local workspace, no multi-tenant auth)
- AI explanations depend on provider quality; fallback is used when the API is missing or invalid
- OCR quality depends on Tesseract and scan clarity
- Field extraction is pattern-based
- ELA is limited for PNG and PDF raster pages
- Copy-move can miss subtle clones or over-flag repetitive templates
- No signer identity verification
- PAN/GST checks only hit the APIs you configure; they are not official government legal confirmation
- Risk assessment is not legal proof

## Tests

Backend (from `backend/` with venv active):

```bash
pytest
```

Frontend (from `frontend/`):

```bash
npm run typecheck
npm run build
```

## Troubleshooting common startup issues

**Frontend cannot reach the API.** Confirm uvicorn is on port 8000 and `NEXT_PUBLIC_API_BASE_URL` matches. Restart `next dev` after changing env files.

**CORS errors in the browser.** Add the exact frontend origin to `CORS_ORIGINS` in `backend/.env` (default `http://localhost:3000`). Restart the API.

**`no such table: document_analyses`.** Run `alembic upgrade head` from `backend/`, or restart the API so startup can create tables. Confirm `DATABASE_URL` points at the file you expect.

**Upload rejected.** Only PDF/JPG/JPEG/PNG are accepted. Content signatures must match the extension. Check `MAX_UPLOAD_SIZE_MB`.

**Visual forensics is slow.** ELA and copy-move run on every page. Large 300 DPI PDFs take longer; wait for the request to finish.

**`no such column: ela_result_json`, `document_intelligence_result_json`, or `fusion_result_json`.** Run `alembic upgrade head` from `backend/` and restart the API.

**OCR missing / Tesseract not found.** Install Tesseract, add it to PATH, or set `TESSERACT_CMD`. The API will still complete metadata and visual layers; document intelligence will record failed extraction instead of crashing.

**Port already in use.** Change `--port` for uvicorn or the Next.js port, and update CORS / `NEXT_PUBLIC_API_BASE_URL` accordingly.

**Windows SQLite path issues.** Prefer the default relative URL `sqlite:///./docuverify.db` and start the process from `backend/`.
