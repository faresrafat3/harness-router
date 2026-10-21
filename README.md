# Harness Router

One interface for all your coding agents.

## The problem

You use 5 different coding agents. Each has strengths:

| Harness | Strength |
|---------|----------|
| **kilo** | Fastest cold start, single-file edits |
| **opencode2** | Headless, multi-file refactors |
| **dsh** | Free LLM credits, model sweeps |
| **cline** | Interactive, UI/frontend work |
| **cline-cloud** | Cloud, heavy compute |

Switching between them is manual. Model selection is ad-hoc. Credits are scattered.

## The solution

Harness Router wraps all of them behind one command:

```sh
/harness route "fix the login bug"          → kilo (single-file-edit)
/harness route "refactor the auth module"    → opencode2 (multi-file-refactor)
/harness route "sweep models for best output" → dsh (model-sweep)
/harness run kilo "add error handling to api.py"
```

## Model policy

Only top-10 models are allowed:

1. Claude Sonnet 4 (Anthropic)
2. GPT-4.1 (OpenAI)
3. Gemini 2.5 Pro (Google)
4. DeepSeek V4 Flash (DeepSeek)
5. Qwen 3.6 Plus (Alibaba)
6. GLM 5.3 (Zhipu)
7. Llama 4 Maverick (Meta)
8. Mistral Large (Mistral)
9. Grok 3 (xAI)
10. Kimi K3 (Moonshot)

Weak models are rejected. Free LLM credits are consolidated through dsh.

## Install

As a Hermes Agent plugin:

```sh
cp -r harness-router ~/.hermes/plugins/
```

Or standalone:

```sh
python3 harness_router.py  # run verify
```

## Usage

```python
from harness_router import route, route_task, run, status

# Route by capability
harness = route("single-file-edit")  # → "kilo"

# Route by task description
result = route_task("fix the login bug in the frontend")
# → {"harness": "kilo", "capability": "ui-frontend", "reason": ...}

# Run a task
result = run("kilo", "add error handling to api.py", model="deepseek-v4-flash")
# → HarnessResult(harness="kilo", ok=True, ...)

# Check status
print(status())
```

## Verify

```sh
python3 verify.py
# ALL CHECKS PASSED
```

## License

MIT
