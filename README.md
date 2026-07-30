# Multi-Agent AI Reply Email

A production-oriented Python worker that monitors a Gmail inbox through IMAP,
runs each unread customer message through the existing LangGraph workflow, and
sends the reviewed reply through SMTP.

The email provider layer is intentionally separate from the AI workflow:

```text
Customer → Gmail Inbox → IMAP → LangGraph → SMTP → Customer
                               │
       Analyzer → Sentiment → Context (Mock RAG) → Drafter → Reviewer
```

## What this migration changes

- Removes the Gmail API and Google Cloud project dependency.
- Reads unread emails from Gmail over IMAP using stable IMAP UIDs.
- Parses the sender address, decoded subject, plain-text/HTML body, and
  `Message-ID`.
- Sends threaded SMTP replies with `In-Reply-To` and `References` headers.
- Marks an email as read only after a reply has been accepted by SMTP.
- Persists processed message IDs, preventing a second reply if the application
  stops after SMTP succeeds but before Gmail records the email as read.
- Retries IMAP, SMTP, and Groq LLM requests; a failed email does not stop the
  next one from being processed.

## Project structure

```text
project/
├── agents/
│   ├── analyzer.py
│   ├── sentiment.py
│   ├── context.py
│   ├── drafter.py
│   ├── reviewer.py
│   └── llm.py
├── services/
│   ├── email_service.py
│   └── rag_service.py
├── graph/
│   ├── state.py
│   └── workflow.py
├── utils/
│   └── logger.py
├── outputs/                   # generated replies and processed-ID state
├── logs/                      # created at runtime
├── config.py
├── main.py
├── requirements.txt
└── .env.example
```

## Local setup

1. Install Python 3.10 or later.

2. Create and activate a virtual environment.

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies.

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. Create your local configuration file.

   ```powershell
   Copy-Item .env.example .env
   ```

5. Fill in `.env`.

   ```dotenv
   EMAIL_ADDRESS=your-address@gmail.com
   EMAIL_APP_PASSWORD=your-16-character-app-password
   GROQ_API_KEY=your-groq-api-key
   LLM_MODEL=llama-3.3-70b-versatile
   CHECK_INTERVAL=30
   ```

6. Start the worker.

   ```powershell
   python main.py
   ```

Stop it safely with `Ctrl+C`. Connections are closed cleanly and logs are
written to `logs/app.log`.

## Gmail configuration

Use an **App Password**, never your normal Google password. Google requires
2-Step Verification before an App Password can be created; some work/school or
Advanced Protection accounts do not expose the option. See Google's [App
Password guidance](https://support.google.com/mail/answer/185833?hl=en) and
[Gmail IMAP guidance](https://support.google.com/mail/answer/7126229?hl=en).

The service is configured for Gmail's encrypted IMAP endpoint
`imap.gmail.com:993` and SSL SMTP endpoint `smtp.gmail.com:465`. These values
are deliberately kept in `config.py` because this is a Gmail-only migration.

## Preserving an existing AI workflow

`services/email_service.py` and `main.py` are the only files concerned with
email transport. The compiled graph remains exactly linear:

```text
START → analyzer → sentiment → context → drafter → reviewer → END
```

To retain a pre-existing project verbatim, copy each existing agent's internal
logic into its matching `build_*_agent` function and retain the state keys it
already returns (`analysis`, `sentiment`, `context`, `draft_reply`, and
`final_reply`). Do not import `EmailService` into any agent. The new transport
passes only `sender`, `subject`, `body`, and `message_id` into the graph.

`services/rag_service.py` is the deliberate home for the current Mock RAG
boundary. Replace its sample `MockRAGService` corpus with the existing mock-RAG
implementation; no graph or email code needs to change.

## Runtime behavior

For every unread email:

1. IMAP fetches and normalizes the message.
2. LangGraph invokes the five unchanged stages in sequence.
3. The reviewed reply is saved as `outputs/reply_<hash>.txt`.
4. SMTP sends a reply in the same email thread.
5. The message ID is atomically saved in `outputs/processed_message_ids.json`.
6. IMAP marks the original email as read.

If step 6 temporarily fails, the message can remain unread, but the persisted
message ID prevents SMTP from sending a duplicate reply. The next poll only
marks it read.

## Operational notes

- Keep `.env`, `logs/`, and `outputs/processed_message_ids.json` private. They
  can contain credentials, customer metadata, or message identifiers.
- Generated reply artifacts include sender and subject metadata. Use a secure,
  access-controlled disk and define a retention policy before handling real
  customer email.
- Run one worker per Gmail inbox unless you add a shared datastore/lock for
  duplicate prevention across multiple machines.
- The Groq model name must be available to the API key you supply.

## Basic validation

Before supplying real credentials, check the source compiles:

```powershell
python -m compileall agents services graph utils config.py main.py
```
## Features

- IMAP/SMTP with automatic reconnect, health checks, and retries.
- Structured logging with rotating files.
- Atomic JSON storage of processed messages (by Message-ID or hash).
- Configurable relevance filtering (keywords, ignore senders/domains).
- Fallback reply template.
- Graceful shutdown handling.
- FastAPI endpoint for manual reply generation.
- Ready for Railway deployment.

## Setup

1. Install Python 3.13+.
2. Create virtual environment and install dependencies:

