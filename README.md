<div align="center">

# DuckAI Wrapper

**A production-ready, OpenAI-compatible API wrapper for Duck.ai (DuckDuckGo AI Chat)**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Playwright](https://img.shields.io/badge/Playwright-Stealth-2EAD33.svg?logo=playwright&logoColor=white)](https://playwright.dev)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com)
[![OpenAI Compatible](https://img.shields.io/badge/API-OpenAI%20Compatible-412991.svg?logo=openai&logoColor=white)](https://platform.openai.com/docs/api-reference)

*Seamlessly integrate Duck.ai's free AI models into any OpenAI-compatible client, SDK, or framework (LangChain, LlamaIndex, LiteLLM, LibreChat, NextChat, etc.).*

---

</div>

## Table of Contents

- [Disclaimer & Legal Notice](#-disclaimer--legal-notice)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
  - [Option A: Local Setup (Recommended with `uv` or `pip`)](#option-a-local-setup-recommended-with-uv-or-pip)
  - [Option B: Docker](#option-b-docker)
  - [Option C: Docker Compose](#option-c-docker-compose)
- [Client Integration Examples](#-client-integration-examples)
  - [1. cURL Examples](#1-curl-examples)
  - [2. Python (Official `openai` SDK)](#2-python-official-openai-sdk)
  - [3. Node.js / TypeScript (`openai` npm package)](#3-nodejs--typescript-openai-npm-package)
  - [4. LangChain Integration](#4-langchain-integration)
- [Configuration Reference](#-configuration-reference)
- [Supported Models & Aliases](#-supported-models--aliases)
- [Testing](#-testing)
- [Reverse-Engineering Discoveries](#-reverse-engineering-discoveries)
  - [1. Deprecation of `x-vqd-4` & Introduction of `x-vqd-hash-1`](#1-deprecation-of-x-vqd-4--introduction-of-x-vqd-hash-1)
  - [2. The `ERR_BN_LIMIT` (418 Teapot) Anti-Bot Gate](#2-the-err_bn_limit-418-teapot-anti-bot-gate)
  - [3. Live Models & Setting IDs](#3-live-models--setting-ids)
- [Contributing](#-contributing)
- [License](#-license)

---

## ⚠️ Disclaimer & Legal Notice

> [!IMPORTANT]
> **Please read this disclaimer carefully before using or deploying this software.**

1. **Educational & Research Purpose Only:** This project is developed strictly for educational, security research, and interoperability study purposes. It serves as an exploration of modern web application anti-bot protections, Server-Sent Events (SSE) translation, and reverse-engineering techniques.
2. **No Affiliation:** This repository is an independent open-source project and is **NOT** affiliated with, endorsed by, sponsored by, or connected to DuckDuckGo, Duck.ai, or any of their affiliates or subsidiaries.
3. **Trademarks:** All product names, trademarks, service marks, logos, and brands mentioned in this repository (including "DuckDuckGo" and "Duck.ai") are property of their respective owners.
4. **Terms of Service & Responsible Usage:** Users of this wrapper are solely responsible for ensuring their usage complies with all relevant local laws, regulations, and third-party Terms of Service. Please respect fair use limits, do not abuse public resources, and avoid running excessive automated traffic that could degrade service availability for regular human users.
5. **No Warranty:** This software is provided "as is", without warranty of any kind, express or implied. Under no circumstances shall the authors or copyright holders be held liable for any claim, damages, account limitation, IP restriction, or other liability arising from the use of this software.

---

## 🌟 Key Features

- **Strict OpenAI Compatibility:** Complete drop-in replacement for OpenAI endpoints (`GET /v1/models`, `POST /v1/chat/completions`).
- **Real-Time Streaming (SSE):** Translates Duck.ai's internal chunked SSE feed into standard OpenAI chunk deltas (`data: {"choices": [{"delta": {"content": "..."}}]}`) terminating with `data: [DONE]`.
- **Non-Streaming Aggregation:** Aggregates tokens and returns standard OpenAI JSON completion payloads with token usage estimates when `stream=false`.
- **Bypasses `ERR_BN_LIMIT`:** Employs an anti-detection stealth browser pool with masked `navigator.webdriver`, authentic Client Hints, and native DOM evaluation.
- **Dynamic Token & Challenge Solving:** Automatically computes cryptographic `x-vqd-hash-1` Proof-of-Work challenges and rotates tokens across multi-turn sessions.
- **Broad Model Support:** Exposes live flagship models including **GPT-6 Luna**, **Claude Haiku 5.5**, **GPT-5.4 mini**, **Mistral Small 4**, and confidential enclave models (**gpt-oss 120B**, **Gemma 4 31B**).
- **Intelligent Aliasing:** Automatically maps standard model names (`gpt-4o`, `gpt-4o-mini`, `claude-3-5-sonnet`, `mistral`, etc.) to the closest available Duck.ai counterpart.
- **Production-Ready:** Packaged with `Dockerfile`, `docker-compose.yml`, health checks (`/health`), and automated test suites.

---

## 🏗 Architecture

```
+-------------------------------------------------------------------------+
|                  OpenAI SDKs / Third-Party Clients                      |
|       (Python / Node.js SDK, LangChain, LlamaIndex, NextChat, etc.)     |
+-------------------------------------------------------------------------+
                                     |
                       Standard OpenAI HTTP Requests
                                     v
+-------------------------------------------------------------------------+
|                         FastAPI REST Gateway                            |
|    - GET  /v1/models                                                    |
|    - POST /v1/chat/completions (stream=True / stream=False)             |
|    - GET  /health                                                       |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                       DuckAI Client & Session Pool                      |
|    - Concurrency Semaphore & Warm Browser Context Management            |
|    - Model Setting ID Injection & Dynamic Model Resolution              |
|    - Stealth Anti-Fingerprinting (navigator.webdriver masked)           |
|    - Response Stream Interception & Token Queueing                      |
+-------------------------------------------------------------------------+
                                     |
                        Internal Web Automation
                                     v
+-------------------------------------------------------------------------+
|                           Duck.ai Platform                              |
|    - Handshake & x-vqd-hash-1 Solver (/duckchat/v1/status)              |
|    - Server-Sent Events Chat Stream (/duckchat/v1/chat)                 |
+-------------------------------------------------------------------------+
```

---

## 🚀 Quick Start

### Option A: Local Setup (Recommended with `uv` or `pip`)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/0vj/duckai-wrapper.git
   cd duckai-wrapper
   ```

2. **Set up virtual environment & install dependencies:**
   ```bash
   # Using uv (fastest)
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   playwright install chromium

   # Or using standard python
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Start the API service:**
   ```bash
   python main.py
   ```
   The service will start on `http://0.0.0.0:8000`. Interactive OpenAPI documentation will be available at `http://localhost:8000/docs`.

---

### Option B: Docker

```bash
# Build the Docker image
docker build -t duckai-wrapper .

# Run the container
docker run -d -p 8000:8000 --name duckai duckai-wrapper
```

---

### Option C: Docker Compose

```bash
# Start in background
docker compose up -d

# View logs
docker compose logs -f
```

---

## 💻 Client Integration Examples

### 1. cURL Examples

#### Non-Streaming (`stream: false`)
```bash
curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-6-luna",
    "messages": [
      {"role": "system", "content": "You are a concise science tutor."},
      {"role": "user", "content": "What is the speed of light in vacuum?"}
    ],
    "stream": false
  }' | python3 -m json.tool
```

#### Streaming (`stream: true`)
```bash
curl -N -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet",
    "messages": [
      {"role": "user", "content": "Count from 1 to 5 separated by commas."}
    ],
    "stream": true
  }'
```

---

### 2. Python (Official `openai` SDK)

```python
from openai import OpenAI

# Point client to local wrapper instance
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="duckai-free-tier"  # Any dummy key is accepted
)

# 1. Non-Streaming Example
completion = client.chat.completions.create(
    model="gpt-6-luna",
    messages=[
        {"role": "system", "content": "You are a poetic assistant."},
        {"role": "user", "content": "Write a 2-line poem about the sea."}
    ],
    stream=False
)
print("Assistant:", completion.choices[0].message.content)

# 2. Streaming Example
stream = client.chat.completions.create(
    model="claude-3-5-sonnet",
    messages=[
        {"role": "user", "content": "Explain quantum superposition in two sentences."}
    ],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()
```

---

### 3. Node.js / TypeScript (`openai` npm package)

```typescript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "http://localhost:8000/v1",
  apiKey: "duckai-free-tier",
});

async function main() {
  const stream = await client.chat.completions.create({
    model: "claude-haiku-5-5",
    messages: [{ role: "user", content: "Tell me a fun programming fact." }],
    stream: true,
  });

  for await (const chunk of stream) {
    process.stdout.write(chunk.choices[0]?.delta?.content || "");
  }
  console.log();
}

main();
```

---

### 4. LangChain Integration

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    api_key="duckai-free-tier",
    model="gpt-6-luna"
)

response = llm.invoke("What is the distance to Mars?")
print(response.content)
```

---

## ⚙️ Configuration Reference

All settings can be customized via environment variables or a `.env` file (see [`.env.example`](file:///Users/amirmahdi/w/duckai-wrapper/.env.example)):

| Variable | Default | Description |
| :--- | :--- | :--- |
| `HOST` | `0.0.0.0` | IP address to bind the HTTP server to |
| `PORT` | `8000` | Port to run the HTTP server on |
| `MAX_CONCURRENT_SESSIONS` | `3` | Maximum concurrent browser sessions maintained in the pool |
| `DEFAULT_MODEL` | `gpt-6-luna` | Default model when none or an unknown identifier is requested |
| `BROWSER_HEADLESS` | `true` | Whether to launch Chromium in headless mode (`false` for visual debugging) |
| `SESSION_TIMEOUT_SECONDS` | `180` | Maximum lifetime of an idle session before recycling |
| `USER_AGENT` | Chrome 131 macOS | Custom User-Agent string |
| `SEC_CH_UA` | Chrome 131 | Custom Client Hints header string |

---

## 📋 Supported Models & Aliases

The wrapper dynamically handles both native Duck.ai model names and common industry aliases:

| Incoming Model Name | Resolved Target Model | Provider |
| :--- | :--- | :--- |
| `gpt-6-luna` | `gpt-6-luna` | OpenAI |
| `gpt-5.4-mini` | `gpt-5.4-mini` | OpenAI |
| `claude-haiku-5-5` | `claude-haiku-5-5` | Anthropic |
| `mistral-small-2603` | `mistral-small-2603` | Mistral AI |
| `tinfoil/gpt-oss-120b` | `tinfoil/gpt-oss-120b` | OpenAI (Enclave) |
| `tinfoil/gemma4-31b` | `tinfoil/gemma4-31b` | Google (Enclave) |
| `gpt-4o`, `gpt-4`, `gpt-4-turbo` | `gpt-6-luna` | OpenAI (Mapped) |
| `gpt-4o-mini`, `gpt-3.5-turbo` | `gpt-5.4-mini` | OpenAI (Mapped) |
| `claude-3-5-sonnet`, `claude-3-7-sonnet` | `claude-haiku-5-5` | Anthropic (Mapped) |
| `mistral`, `mixtral`, `llama-3` | `mistral-small-2603` | Mistral AI (Mapped) |
| `gemma`, `gemma-2` | `tinfoil/gemma4-31b` | Google (Mapped) |

---

## 🧪 Testing

The repository includes a comprehensive unit test suite covering model resolution, OpenAI request formatting, and API routes.

```bash
# Run test suite
pytest tests/
```

Expected output:
```text
tests/test_api.py .....                                          [100%]
========================= 5 passed in 0.20s =========================
```

---

## 🔬 Reverse-Engineering Discoveries

During live inspection of `https://duck.ai` and its production JavaScript bundles (`entry.duckai.*.js`), several key internal systems were documented:

### 1. Deprecation of `x-vqd-4` & Introduction of `x-vqd-hash-1`

Legacy reverse-engineered wrappers commonly relied on static `x-vqd-4` UUID tokens. **This mechanism has been deprecated by Duck.ai.** 

The current protocol requires:
1. The client sends `GET https://duck.ai/duckchat/v1/status` with header `x-vqd-accept: 1`.
2. The server responds with `x-vqd-hash-1: <base64-encoded-obfuscated-js>`.
3. The client executes this script in an active browser context. The script inspects DOM prototype chains (`HTMLDivElement`, `HTMLElement`, `NodeList`), DOM modification behaviors, and window properties.
4. The client computes SHA-256 digests over `client_hashes`, attaches execution metadata (`origin`, `duration`, `stack`), and encodes the payload into a signed base64 string.
5. This payload is passed as the `x-vqd-hash-1` request header on `POST /duckchat/v1/chat`.
6. Every successful `/chat` response emits a **new** `x-vqd-hash-1` header for the next conversational turn.

### 2. The `ERR_BN_LIMIT` (418 Teapot) Anti-Bot Gate

Sending requests via raw HTTP clients (`curl`, `requests`, `httpx`) or standard headless browsers triggers:
```http
HTTP/418 I'm a teapot
Content-Type: application/json

{"action":"error","overrideCode":"84f2","status":418,"type":"ERR_BN_LIMIT"}
```
`ERR_BN_LIMIT` stands for **"Botnet Limit"**. It is activated when:
* `HeadlessChrome` appears in `User-Agent` or Client Hints (`sec-ch-ua`).
* `navigator.webdriver` is detected as `true`.
* DOM verification routines fail within the challenge solver.

**How DuckAI Wrapper solves this:** The wrapper maintains a pool of warm Chromium contexts with `--disable-blink-features=AutomationControlled`, patched `navigator.webdriver`, consistent `sec-ch-ua` headers, and native execution.

### 3. Live Models & Setting IDs

Inspected directly from module `63722` in `entry.duckai.*.js`:

| Model ID | Provider | Setting ID | Description |
| :--- | :--- | :--- | :--- |
| `gpt-6-luna` | OpenAI | `291` | Flagship everyday model (**Default for Free Tier**) |
| `gpt-5.4-mini` | OpenAI | `262` | Fast, compact model (Free) |
| `claude-haiku-5-5` | Anthropic | `295` | Claude Haiku 5.5 (Free) |
| `mistral-small-2603` | Mistral AI | `6` | Mistral Small 4 open-weights model (Free) |
| `tinfoil/gpt-oss-120b` | OpenAI | `251` | Confidential enclave open-weights model (Free) |
| `tinfoil/gemma4-31b` | Google | `270` | Confidential enclave Gemma 4 31B model (Free) |

---

## 🤝 Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](file:///Users/amirmahdi/w/duckai-wrapper/CONTRIBUTING.md) for guidelines on reporting issues, suggesting features, and submitting pull requests.

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](file:///Users/amirmahdi/w/duckai-wrapper/LICENSE) for more information.
