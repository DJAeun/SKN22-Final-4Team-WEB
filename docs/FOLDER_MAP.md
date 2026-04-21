# Folder Map

Top-level layout of the HARI repository, with the purpose of each entry.

```
SKN22-Final-4Team-WEB/
│
├── .agent/                          Agent role and workflow definitions (PM, backend, devops, etc.)
├── .claude/                         Claude Code configuration (settings.local.json, skills/)
├── .github/                         GitHub Actions workflows (deploy-eb.yml) and issue templates
│
├── backend/                         Django + Channels app — deployment target for AWS EB
│   ├── config/                      Django project settings, URL router, ASGI/WSGI entrypoints
│   ├── chat/                        Core chat app: views, models, consumers, LangChain engine
│   ├── accounts/                    User accounts (allauth + dj-rest-auth)
│   ├── templates/frontend/          Page templates (homepage, mypage, chat, etc.)
│   ├── static/                      Shared static assets (css/, js/, images/, video/)
│   ├── media/                       User-uploaded files (gitignored except .gitkeep)
│   ├── .ebextensions/, .platform/   Elastic Beanstalk deploy hooks
│   ├── Dockerfile, docker-compose.yml, Procfile
│   ├── manage.py, requirements.txt
│   └── ...
│
├── ai-influencer/                   Reserved for SNS automation pipeline (n8n, scrapers, etc.)
│                                    Currently only holds `notion_mcp.json` (Notion MCP server config)
│
├── db/                              One-off database setup scripts
│   ├── setup_db_schema.py           Initial schema setup
│   ├── setup_rds.ps1                AWS RDS provisioning helper
│   ├── ingest_to_pgvector.py        Bulk-ingest documents into pgvector
│   └── insert_hari_sports.py        Persona/topic seed data loader
│
├── docs/                            Project documentation (non-README)
│   ├── FOLDER_MAP.md                This file
│   ├── admin.md                     Django admin customization notes
│   └── BACKEND_REQUEST.md           Backend API request/response spec
│
├── eval/                            Evaluation, load testing, cost analysis
│   ├── README.md, REPORT.md
│   ├── golden_dataset.json          Eval ground-truth Q&A set
│   ├── judge_eval.py                LLM-as-judge runner
│   ├── load_test.py                 Concurrency / latency benchmark
│   ├── cost_calculator.py           Per-request cost calculator
│   └── results/                     Eval run outputs
│
├── heygen_pipeline/                 HeyGen API video generation pipeline
│   ├── generate_video.py            Main entrypoint (audio -> video)
│   ├── input_audio/, input_script/  Inputs (voice WAV/MP3, scripts) — large files gitignored
│   └── output_videos/               Rendered MP4s — gitignored
│
├── img_gen/                         Image generation (Z-Image-turbo + LoRA)
│   ├── hari_lora/                   Trained LoRA weights (`*.safetensors` — gitignored)
│   ├── workflow/                    ComfyUI workflow JSONs (tracked)
│   ├── run_workflow/                Python runners that drive ComfyUI workflows
│   ├── python/                      Helper modules
│   └── wildcard/                    Prompt wildcard text files (mostly gitignored)
│
├── langchain-skills/                LOCAL-ONLY plugin install (gitignored)
├── langsmith-skills/                LOCAL-ONLY plugin install (gitignored)
│                                    These are independent Claude Code plugin repos
│                                    cloned per-developer; not part of project source.
│
├── README.md                        Project overview, setup, team
├── LICENSE
├── .gitignore
├── .env                             Local environment vars (gitignored)
└── hari-key.pem                     AWS SSH key (gitignored)
                                     ⚠ Consider moving outside the repo (e.g. ~/.ssh/)
```

## Conventions

- **Generated artifacts** (images, videos, model weights, build outputs) are gitignored.
  Generated images live under each tool's local working dir, not at repo root.
- **Local scratch** (`klein_img/`, `notebooklm/`, `node_modules/` at root) is gitignored
  and should not be committed.
- **Secrets** (`.env`, `*.pem`) are gitignored. Never commit them; rotate immediately
  if accidentally pushed.
- **Deployment**: only `backend/` is packaged for Elastic Beanstalk
  (see `.github/workflows/deploy-eb.yml`).

## What's deployed vs. what's local-only

| Folder              | Deployed to EB? | Notes                                |
|---------------------|-----------------|--------------------------------------|
| `backend/`          | ✅ yes           | The deploy artifact                  |
| `db/`               | ❌ no            | One-shot setup scripts               |
| `eval/`             | ❌ no            | Run locally / in CI                  |
| `heygen_pipeline/`  | ❌ no            | Runs on GPU instance                 |
| `img_gen/`          | ❌ no            | Runs on GPU instance                 |
| `ai-influencer/`    | ❌ no            | Automation runs on n8n / lambda      |
| `langchain-skills/` | ❌ no            | Local Claude Code plugin (gitignored)|
| `langsmith-skills/` | ❌ no            | Local Claude Code plugin (gitignored)|
