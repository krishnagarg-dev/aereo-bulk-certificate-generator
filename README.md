# AEREO Bulk Certificate Generator

A FastAPI backend for bulk certificate generation. The API accepts a single generation request containing multiple recipients, validates the input, creates certificates independently, tracks job progress, records individual failures, and exposes generated PDF certificates for download.

## Features

- Bulk certificate generation from a single API request
- Request and business-rule validation
- Background processing with FastAPI `BackgroundTasks`
- Individual recipient processing and failure isolation
- Job-level progress tracking
- Per-recipient success/failure status
- PDF certificate generation using ReportLab
- Certificate retrieval through an API endpoint
- SQLite for local development
- PostgreSQL-compatible database configuration
- Automated tests with pytest
- Interactive API documentation through Swagger UI and ReDoc

## Architecture

```text
                         POST /api/jobs
Client ------------------------------------------+
                                                  |
                                                  v
                                        +------------------+
                                        |    FastAPI API   |
                                        +------------------+
                                                  |
                                      Pydantic + business
                                         rule validation
                                                  |
                                                  v
                                      +------------------+
                                      |   SQLAlchemy DB  |
                                      +------------------+
                                         |           |
                                  GenerationJob    Recipient
                                         |
                                         v
                                Background Processor
                                         |
                              +----------+----------+
                              |                     |
                              v                     v
                       Generate PDF          Update status
                              |                     |
                              +----------+----------+
                                         |
                                         v
                                  Update job progress
                                         |
                                         v
                                GET /api/jobs/{id}
                                         |
                                         v
                              GET /api/certificates/{id}
                                         |
                                         v
                                      PDF file
```

## Data Model

The application separates the bulk generation job from individual recipients.

```text
GenerationJob
├── id
├── event_name
├── certificate_title
├── total_recipients
├── successful_count
├── failed_count
├── status
├── created_at
└── updated_at

Recipient
├── id
├── job_id
├── name
├── email
├── status
├── certificate_path
└── error_message
```

This separation makes it possible to track both aggregate job progress and the result of every individual certificate.

## Requirements

- Python 3.12+
- FastAPI
- SQLAlchemy
- ReportLab
- SQLite for local development or PostgreSQL for deployment

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

### Windows

```powershell
.venv\Scripts\Activate.ps1
```

### macOS/Linux

```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env`.

Example:

```env
APP_NAME=AEREO Bulk Certificate Generator
DATABASE_URL=sqlite:///./certificate_generator.db
CERTIFICATE_OUTPUT_DIR=generated_certificates
```

For PostgreSQL deployment, `DATABASE_URL` can be changed to the appropriate PostgreSQL connection string.

## Run the API

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

### API documentation

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- Health check: `/health`

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/jobs` | Create a bulk certificate generation job |
| `GET` | `/api/jobs/{job_id}` | Get job status, progress and recipient results |
| `GET` | `/api/certificates/{recipient_id}` | Download a successfully generated certificate |
| `GET` | `/health` | Health check |

## API Workflow

The normal workflow is:

```text
POST /api/jobs
      |
      | 202 Accepted
      v
   job_id
      |
      v
GET /api/jobs/{job_id}
      |
      +--> PROCESSING
      |
      +--> COMPLETED
      |
      +--> COMPLETED_WITH_ERRORS
      |
      v
recipient_id
      |
      v
GET /api/certificates/{recipient_id}
      |
      v
PDF certificate
```

## Create a Generation Job

### Request

```http
POST /api/jobs
Content-Type: application/json
```

Example:

```json
{
  "event_name": "AEREO Engineering Workshop",
  "certificate_title": "Certificate of Participation",
  "recipients": [
    {
      "name": "Alice",
      "email": "alice@example.com"
    },
    {
      "name": "Bob",
      "email": "bob@example.com"
    }
  ]
}
```

The API validates:

- Required event name
- Certificate title
- Recipient list size
- Recipient name
- Optional recipient email format
- Duplicate recipients

### Response

The API returns `202 Accepted` because certificate generation is performed as background work.

Example:

```json
{
  "id": "job-uuid",
  "event_name": "AEREO Engineering Workshop",
  "certificate_title": "Certificate of Participation",
  "total_recipients": 2,
  "successful_count": 0,
  "failed_count": 0,
  "status": "PROCESSING",
  "progress_percent": 0.0,
  "recipients": []
}
```

## Check Job Status

```http
GET /api/jobs/{job_id}
```

The response contains:

- Total recipients
- Successful count
- Failed count
- Overall job status
- Percentage progress
- Individual recipient status
- Individual error messages
- Certificate URLs for successful recipients

Example completed response:

```json
{
  "id": "job-uuid",
  "event_name": "AEREO Engineering Workshop",
  "certificate_title": "Certificate of Participation",
  "total_recipients": 2,
  "successful_count": 2,
  "failed_count": 0,
  "status": "COMPLETED",
  "progress_percent": 100.0,
  "recipients": [
    {
      "id": "recipient-uuid-1",
      "name": "Alice",
      "email": "alice@example.com",
      "status": "SUCCESS",
      "certificate_url": "/api/certificates/recipient-uuid-1",
      "error_message": null
    },
    {
      "id": "recipient-uuid-2",
      "name": "Bob",
      "email": "bob@example.com",
      "status": "SUCCESS",
      "certificate_url": "/api/certificates/recipient-uuid-2",
      "error_message": null
    }
  ]
}
```

## Retrieve a Certificate

```http
GET /api/certificates/{recipient_id}
```

If certificate generation was successful, the endpoint returns the generated PDF.

Example:

```text
Content-Type: application/pdf
```

If the recipient does not exist or does not have a successfully generated certificate, the API returns an appropriate error response.

## Failure Isolation

Each recipient is processed independently.

For example:

```text
Alice       → SUCCESS
Broken User → FAILED
Bob         → SUCCESS
```

The failure of `Broken User` does not terminate the complete generation job.

The final job state becomes:

```text
COMPLETED_WITH_ERRORS
```

while the successful certificates remain available.

This design ensures that one bad recipient or certificate-generation error does not unnecessarily discard successful work.

## Progress Tracking

Progress is calculated from the number of recipients that have finished processing.

```text
progress = completed_recipients / total_recipients × 100
```

For example:

```text
Total recipients:       100
Successfully processed: 95
Failed:                   5
Completed:              100

Progress:               100%
Status:                 COMPLETED_WITH_ERRORS
```

## Testing

Run the complete test suite with:

```bash
python -m pytest -q
```

Current test coverage includes:

- Successful bulk job creation
- Certificate generation
- Certificate retrieval
- Input validation
- Duplicate recipient rejection
- Blank field rejection
- Unknown job handling
- Unknown certificate handling
- Individual certificate failure isolation
- Job progress and final status

Expected result:

```text
7 passed
```

## Design Decisions

### FastAPI

FastAPI provides:

- Request validation
- Automatic OpenAPI documentation
- Dependency injection
- Clean API routing
- Good performance with minimal boilerplate

### Pydantic

Pydantic is used to validate incoming requests before they reach the processing layer.

The API validates recipient names, email addresses, required text fields, and recipient list limits.

### SQLAlchemy

SQLAlchemy provides the relational persistence layer.

The aggregate `GenerationJob` and individual `Recipient` records are kept separate so the application can efficiently track both job-level and recipient-level state.

The database configuration supports SQLite for local development and can be configured for PostgreSQL deployment.

### Background Processing

Certificate generation is performed using FastAPI `BackgroundTasks`.

This keeps certificate generation outside the initial request-response path and allows the API to return `202 Accepted` immediately.

For very large production workloads, the processing service could be moved behind a durable task queue such as Celery or RQ with Redis.

### Failure Isolation

Each recipient is processed inside its own error boundary.

A failed certificate:

1. Is marked as `FAILED`
2. Stores the error message
3. Does not stop processing of other recipients
4. Contributes to the final `COMPLETED_WITH_ERRORS` job state

### Certificate Generation

ReportLab is used to generate PDF certificates from a predefined template.

The certificate template remains fixed while recipient-specific information such as:

- Recipient name
- Certificate title
- Event name

is injected into the generated document.

## Project Structure

```text
aereo-bulk-certificate-generator/
│
├── app/
│   ├── api/
│   │   └── routes.py
│   ├── core/
│   │   └── config.py
│   ├── db/
│   │   └── session.py
│   ├── models/
│   │   └── job.py
│   ├── schemas/
│   │   └── job.py
│   ├── services/
│   │   ├── certificate.py
│   │   └── job_processor.py
│   └── main.py
│
├── tests/
│   ├── conftest.py
│   └── test_jobs.py
│
├── generated_certificates/
├── .env.example
├── .gitignore
├── Dockerfile
├── requirements.txt
└── README.md
```

## Future Production Improvements

For a larger production workload, the system could evolve with:

- Durable background queues using Celery/RQ + Redis
- PostgreSQL with Alembic migrations
- Object storage such as Amazon S3
- Authentication and authorization
- Certificate regeneration/retry
- Job cancellation
- Expiring download URLs
- Structured logging
- Metrics and monitoring
- Rate limiting
- Request and batch-size controls

## Interview Talking Points

Important design questions to be prepared for:

### Why separate Job and Recipient?

A job represents the bulk operation, while each recipient represents an independently processable unit of work. This allows aggregate progress and individual failures to be tracked simultaneously.

### Why background processing?

Certificate generation can take longer as the batch grows. Returning `202 Accepted` avoids making the client wait for the entire batch.

### Why isolate failures?

One invalid or problematic certificate should not discard certificates that were generated successfully.

### How is progress calculated?

Progress is based on the number of recipients whose processing has completed relative to the total number of recipients.

### How would this scale to millions of certificates?

For very large workloads, FastAPI `BackgroundTasks` would be replaced or supplemented with a durable queue and worker architecture. Generated files would also move from local disk to object storage, while PostgreSQL would provide durable production persistence.

## License

This project was developed as a technical assignment for AEREO.