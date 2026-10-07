# Bulk Certificate Generator API

[![CI](https://github.com/Midhun-M-git/bulk-certificate-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/Midhun-M-git/bulk-certificate-generator/actions/workflows/ci.yml)

A backend REST API built with FastAPI, SQLAlchemy, and ReportLab that processes bulk certificate generation requests for participant lists, validates recipient records, renders vector-grade PDF certificates from a predefined template, tracks generation lifecycle progress, and provides retrieval via individual downloads or consolidated ZIP archives.

---

## Overview

When events, bootcamps, or corporate training programs conclude, organizations frequently need to generate certificates for hundreds or thousands of participants simultaneously. 

Making individual API requests per participant introduces network overhead, rate-limiting hurdles, and poor client ergonomics. This service solves that problem by providing:

1. **A Single Bulk Submission Endpoint**: Clients submit event details and an arbitrary list of recipients in one request.
2. **Non-Blocking Background Processing**: The API validates input, persists the job and recipient records, and immediately returns a `202 Accepted` response with a tracking identifier, executing rendering in the background.
3. **Resilient Failure Isolation**: Invalid recipient records (such as malformed email addresses or blank names) or runtime rendering exceptions on an individual certificate do not abort the job. Valid certificates in the batch are still generated, and the job transitions to a `PARTIAL_SUCCESS` state with granular error reasons recorded per failed recipient.
4. **Vector-Quality PDF Rendering**: Certificates are rendered directly using ReportLab, ensuring sharp vector typography, borders, and seal graphics at any resolution without headless browser overhead.
5. **Flexible Retrieval**: Clients can fetch individual certificates (attachment download or inline preview) or download the entire batch as a single ZIP archive.

---

## Architecture and Technical Design

### Processing Pipeline

```
+-------------------------------------------------------------------------+
|                               API Client                                |
+-------------------------------------------------------------------------+
       |                                                 ^
       | 1. POST /api/v1/jobs                            | 4. GET /api/v1/jobs/{id}
       v                                                 |    (Polling status)
+------------------------------------+                   |
|          FastAPI Router            |                   |
+------------------------------------+                   |
       |                                                 |
       | 2. Synchronous Validation & Ingestion           |
       v                                                 |
+------------------------------------+                   |
|            Job Service             |                   |
+------------------------------------+                   |
       |                                                 |
       |-- Ingest recipients, pre-validate fields        |
       |-- Persist Job (PENDING) and Certificates        |
       |-- Dispatch background worker task               |
       |                                                 |
       | 3. Returns 202 Accepted (job_id, status_url)    |
       v                                                 |
+--------------------------------------------------------+----------------+
|                        Background Worker Task                           |
+-------------------------------------------------------------------------+
       |
       | Transitions Job -> PROCESSING
       |
       | Loop through PENDING certificates:
       |   +--> ReportLab Generator -> Generates PDF to storage
       |   +--> Updates Certificate -> SUCCESS (or FAILED on error)
       |   +--> Commits progress counters (total, processed, success, failed)
       |
       | If success_count > 0:
       |   +--> Storage Service -> Packages all PDFs into a ZIP archive
       |
       | Transitions Job -> COMPLETED / PARTIAL_SUCCESS / FAILED
       v
+------------------------------------+       +----------------------------+
|         SQLite Database            |       |    Local File Storage      |
|  - jobs table                      |       |  - storage/certificates/   |
|  - certificates table              |       |      {job_id}/{cert_id}.pdf|
+------------------------------------+       |      {job_id}/*.zip        |
                                             +----------------------------+
```

### Relational Schema

The data model consists of two primary entities:

#### `jobs`
- `id` (VARCHAR 36, PK): Unique UUID identifying the generation job.
- `title` (VARCHAR 255): Title of the event or course.
- `issuer_name` (VARCHAR 255): Organization issuing the certificate.
- `issue_date` (VARCHAR 50): Date string rendered on the certificate.
- `description` (TEXT, Nullable): Subtitle or achievement description.
- `status` (ENUM): Current execution state (`PENDING`, `PROCESSING`, `COMPLETED`, `PARTIAL_SUCCESS`, `FAILED`).
- `total_count` (INTEGER): Total number of recipients submitted.
- `processed_count` (INTEGER): Total recipients processed so far.
- `success_count` (INTEGER): Count of certificates successfully generated.
- `failed_count` (INTEGER): Count of failed recipient generations.
- `zip_path` (VARCHAR 500, Nullable): Filesystem path to the generated ZIP archive.
- `error_message` (TEXT, Nullable): Job-level error description if applicable.
- `created_at`, `started_at`, `completed_at` (DATETIME): Lifecycle timestamps.

#### `certificates`
- `id` (VARCHAR 36, PK): Unique UUID identifying the certificate.
- `job_id` (VARCHAR 36, FK -> jobs.id): Associated job.
- `certificate_number` (VARCHAR 50, UNIQUE): Formatted unique verification code (e.g. `CERT-20261007-8F2A91`).
- `recipient_name` (VARCHAR 255): Full name of the recipient.
- `recipient_email` (VARCHAR 255, Nullable): Recipient email address.
- `metadata_json` (TEXT, Nullable): JSON-serialized key-value attributes (e.g. grade, honors).
- `status` (ENUM): Status of this specific certificate (`PENDING`, `PROCESSING`, `SUCCESS`, `FAILED`).
- `file_path` (VARCHAR 500, Nullable): Path to the generated PDF.
- `file_size_bytes` (INTEGER, Nullable): File size on disk.
- `failure_reason` (TEXT, Nullable): Detailed message describing why generation failed.
- `created_at`, `generated_at` (DATETIME): Timestamps.

---

## Technology Stack

- **Language**: Python 3.9+
- **Web Framework**: FastAPI (high performance, asynchronous request handling, native OpenAPI docs)
- **Data Validation**: Pydantic v2 (strict type enforcement and payload validation)
- **ORM & Database**: SQLAlchemy 2.0 with SQLite (configurable to PostgreSQL via environment variable)
- **PDF Generation**: ReportLab (pure-Python vector PDF engine; zero headless browser or OS-level C library dependencies)
- **Testing**: PyTest with HTTPX / FastAPI TestClient

---

## Setup and Installation

### 1. Prerequisites
- Python 3.9 or higher
- `pip` package manager

### 2. Environment Configuration

Clone or navigate to the project directory:

```bash
cd "Bulk Certificate generator"
```

Create and activate a virtual environment:

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Environment Variables (Optional)

The application works out of the box with default values. You can override settings via environment variables if needed:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./certificate_generator.db` | SQLAlchemy connection string (e.g. PostgreSQL) |
| `STORAGE_DIR` | `./storage/certificates` | Base directory where PDF files and ZIPs are saved |
| `MAX_RECIPIENTS_PER_BATCH` | `5000` | Maximum recipients accepted in a single request |
| `BASE_URL` | `http://localhost:8000` | Host URL used when constructing resource links |

---

## Running the Application

### Using the Startup Script

```bash
./run.sh
```

### Using Uvicorn Directly

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Once started:
- **Interactive Web Studio**: http://localhost:8000
- **Interactive Swagger Documentation**: http://localhost:8000/docs
- **ReDoc Technical Reference**: http://localhost:8000/redoc

---

## Running the Test Suite

The test suite covers job creation, validation boundaries, PDF rendering correctness, lifecycle tracking, error isolation, and file retrieval.

Run all tests:

```bash
pytest -v
```

### Test Coverage Breakdown

- `tests/test_job_creation.py`: Validates job creation, response structure, HTTP 202 Accepted status, and rejection of incomplete payloads.
- `tests/test_validation.py`: Verifies empty recipient list handling (HTTP 422), whitespace field checks, email format validation, and batch size limit enforcement.
- `tests/test_generation.py`: Verifies ReportLab engine output, checks `%PDF-` binary magic headers, non-zero file sizes, dynamic text scaling for long recipient names, and custom metadata.
- `tests/test_status_progress.py`: Tests the progression from `PENDING` through `COMPLETED`, verifies counter accuracy (`total`, `processed`, `success`, `failed`), and tests job listing with pagination.
- `tests/test_failure_handling.py`: Tests mixed batches containing invalid names and emails alongside valid recipients. Confirms that valid recipients succeed while invalid items are recorded as `FAILED` with explicit failure reasons, bringing the job to `PARTIAL_SUCCESS`. Also tests isolation when runtime exceptions occur during rendering.
- `tests/test_retrieval.py`: Tests single PDF file download (with attachment headers), inline browser previewing, bulk ZIP archive download and integrity, and 400/404 error cases.

---

## API Reference and Usage

### 1. Submit a Certificate Generation Job

`POST /api/v1/jobs`

Submits an event certificate generation job with a list of recipients.

#### Request Body
```json
{
  "title": "Distributed Systems Engineering",
  "issuer_name": "Institute of Software Systems",
  "issue_date": "October 7, 2026",
  "description": "for successfully completing 60 hours of technical curriculum",
  "recipients": [
    {
      "name": "Eleanor Vance",
      "email": "eleanor.vance@example.com",
      "metadata": { "grade": "Distinction" }
    },
    {
      "name": "Marcus Holloway",
      "email": "marcus.h@example.com",
      "metadata": { "grade": "A+" }
    },
    {
      "name": "   ",
      "email": "invalid_entry@example.com"
    }
  ]
}
```

#### cURL Example
```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Distributed Systems Engineering",
    "issuer_name": "Institute of Software Systems",
    "issue_date": "October 7, 2026",
    "description": "for successfully completing 60 hours of technical curriculum",
    "recipients": [
      {
        "name": "Eleanor Vance",
        "email": "eleanor.vance@example.com",
        "metadata": { "grade": "Distinction" }
      },
      {
        "name": "Marcus Holloway",
        "email": "marcus.h@example.com",
        "metadata": { "grade": "A+" }
      },
      {
        "name": "   ",
        "email": "invalid_entry@example.com"
      }
    ]
  }'
```

#### Response (`202 Accepted`)
```json
{
  "job_id": "8f395f26-8806-444a-85d8-4f1be7ad7125",
  "status": "PENDING",
  "message": "Bulk certificate generation job accepted and scheduled for background processing.",
  "total_recipients": 3,
  "status_url": "/api/v1/jobs/8f395f26-8806-444a-85d8-4f1be7ad7125"
}
```

---

### 2. Check Job Status and Progress

`GET /api/v1/jobs/{job_id}`

Polls the status and progress metrics of a submitted job.

#### cURL Example
```bash
curl "http://localhost:8000/api/v1/jobs/8f395f26-8806-444a-85d8-4f1be7ad7125"
```

#### Response
```json
{
  "id": "8f395f26-8806-444a-85d8-4f1be7ad7125",
  "title": "Distributed Systems Engineering",
  "issuer_name": "Institute of Software Systems",
  "issue_date": "October 7, 2026",
  "description": "for successfully completing 60 hours of technical curriculum",
  "status": "PARTIAL_SUCCESS",
  "total_count": 3,
  "processed_count": 3,
  "success_count": 2,
  "failed_count": 1,
  "progress_percentage": 100.0,
  "has_zip": true,
  "zip_download_url": "/api/v1/jobs/8f395f26-8806-444a-85d8-4f1be7ad7125/download-zip",
  "created_at": "2026-10-07T06:45:00.123456",
  "started_at": "2026-10-07T06:45:00.234567",
  "completed_at": "2026-10-07T06:45:01.345678",
  "certificates": [
    {
      "id": "1c7a2e88-3490-4c31-9b1b-7e61a86b3df5",
      "job_id": "8f395f26-8806-444a-85d8-4f1be7ad7125",
      "certificate_number": "CERT-20261007-B72F41",
      "recipient_name": "Eleanor Vance",
      "recipient_email": "eleanor.vance@example.com",
      "status": "SUCCESS",
      "download_url": "/api/v1/certificates/1c7a2e88-3490-4c31-9b1b-7e61a86b3df5/download",
      "preview_url": "/api/v1/certificates/1c7a2e88-3490-4c31-9b1b-7e61a86b3df5/preview",
      "file_size_bytes": 3942,
      "failure_reason": null,
      "created_at": "2026-10-07T06:45:00.123456",
      "generated_at": "2026-10-07T06:45:00.891234"
    },
    {
      "id": "2b8c3d99-4501-5d42-0c2c-8f72b97c4eg6",
      "job_id": "8f395f26-8806-444a-85d8-4f1be7ad7125",
      "certificate_number": "CERT-20261007-C83A52",
      "recipient_name": "<Invalid Name>",
      "recipient_email": "invalid_entry@example.com",
      "status": "FAILED",
      "download_url": null,
      "preview_url": null,
      "file_size_bytes": null,
      "failure_reason": "Recipient name cannot be empty or whitespace only",
      "created_at": "2026-10-07T06:45:00.123456",
      "generated_at": null
    }
  ]
}
```

---

### 3. List Recent Jobs

`GET /api/v1/jobs?limit=50&offset=0`

Returns a paginated list of recent bulk generation jobs and their execution summaries.

---

### 4. Retrieve Individual Certificate PDF

`GET /api/v1/certificates/{certificate_id}/download`

Downloads the generated PDF file as an attachment.

```bash
curl -O -J "http://localhost:8000/api/v1/certificates/1c7a2e88-3490-4c31-9b1b-7e61a86b3df5/download"
```

Response Headers:
- `Content-Type: application/pdf`
- `Content-Disposition: attachment; filename="Eleanor_Vance_CERT-20261007-B72F41.pdf"`

To view inline in a browser or modal without triggering a download:

`GET /api/v1/certificates/{certificate_id}/preview`

---

### 5. Download All Generated Certificates as a ZIP Archive

`GET /api/v1/jobs/{job_id}/download-zip`

Downloads a single compressed `.zip` archive containing all successfully generated PDF certificates for the job.

```bash
curl -O -J "http://localhost:8000/api/v1/jobs/8f395f26-8806-444a-85d8-4f1be7ad7125/download-zip"
```

Response Headers:
- `Content-Type: application/zip`
- `Content-Disposition: attachment; filename="Distributed_Systems_Engineering_certificates.zip"`

---

## Design Decisions and Justifications

### 1. Framework: FastAPI
- **Choice**: FastAPI rather than Django + DRF or Flask.
- **Justification**:
  - Native asynchronous concurrency allows high throughput for I/O-bound API operations.
  - Built-in `BackgroundTasks` support offloading generation work without requiring external message brokers for standard deployments.
  - Native Pydantic v2 schemas provide automatic validation, descriptive error responses, and up-to-date OpenAPI documentation.

### 2. PDF Rendering Engine: ReportLab
- **Choice**: ReportLab vector PDF rendering rather than browser automation (Puppeteer/Playwright) or HTML-to-PDF engines (WeasyPrint).
- **Justification**:
  - **Zero External Binary Dependencies**: WeasyPrint requires complex system libraries (`pango`, `cairo`, `gobject`) that often break across operating systems. Headless Chromium tools require 300MB+ browser binaries and significant RAM per page. ReportLab installs cleanly with `pip install reportlab` and runs anywhere.
  - **Performance & Throughput**: Generates certificates at 20-50 pages per second with minimal memory footprint.
  - **Vector Output Quality**: Certificates maintain crisp lines, typography, and rosette graphics at any print or screen resolution.

### 3. Background Processing Strategy
- **Choice**: FastAPI `BackgroundTasks` with thread-safe SQLite/PostgreSQL sessions.
- **Justification**:
  - For standalone deployment and testing, avoiding a required Redis or RabbitMQ dependency makes local execution trivial.
  - The API immediately acknowledges requests with `202 Accepted` and offloads generation to the worker.
  - Progress counters are committed after each recipient, giving clients accurate live progress during polling.
  - *Extensibility*: In a distributed multi-worker cluster, the call in `job_service.process_job` can be swapped for a Celery task or AWS SQS worker without modifying the API contract.

### 4. Fault Tolerance and Failure Isolation
- **Choice**: Per-recipient error tracking with `PARTIAL_SUCCESS` job status.
- **Justification**:
  - In real-world bulk generation (e.g. 500 attendees), one invalid email or missing name should not prevent the remaining 499 valid certificates from being created.
  - Pre-validation isolates faulty rows upfront as `FAILED` with explicit error descriptions.
  - Runtime exceptions during PDF rendering are wrapped per recipient, ensuring one failed render does not terminate the loop.

---

## Project Structure

```
Bulk Certificate generator/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── certificates.py    # Download, preview, and certificate metadata
│   │       ├── jobs.py            # Job submission, status, listing, ZIP archive
│   │       └── router.py          # API v1 aggregation
│   ├── models/
│   │   ├── certificate.py         # Certificate ORM model
│   │   └── job.py                 # Job ORM model
│   ├── schemas/
│   │   ├── certificate.py         # Certificate response schemas
│   │   ├── job.py                 # Job request and response schemas
│   │   └── recipient.py           # Recipient input schemas
│   ├── services/
│   │   ├── certificate_generator.py # ReportLab PDF rendering engine
│   │   ├── job_service.py         # Batch orchestration & validation
│   │   └── storage_service.py     # File storage & ZIP bundling
│   ├── static/
│   │   ├── app.js                 # Web console reactive logic
│   │   └── index.html             # Web console user interface
│   ├── config.py                  # Application settings
│   ├── database.py                # Database engine and session setup
│   └── main.py                    # Application entry point, CORS, static mounts
├── storage/                       # Storage directory for PDFs and ZIPs
├── tests/
│   ├── conftest.py                # Pytest fixtures and test DB setup
│   ├── test_failure_handling.py   # Failure tolerance and error isolation tests
│   ├── test_generation.py         # PDF rendering engine tests
│   ├── test_job_creation.py       # Job creation API tests
│   ├── test_retrieval.py          # File and ZIP retrieval tests
│   ├── test_status_progress.py    # Progress tracking and lifecycle tests
│   └── test_validation.py         # Recipient data validation tests
├── requirements.txt               # Dependencies
├── run.sh                         # Application startup script
└── README.md                      # Documentation
```

---

## License

This project is licensed under the MIT License.
