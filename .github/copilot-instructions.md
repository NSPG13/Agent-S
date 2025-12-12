# Agent-S Copilot Instructions

## Project Overview
Agent-S is a GUI automation framework for enabling autonomous computer interaction through Agent-Computer Interface (ACI). The package `gui-agents` provides multiple agent versions (S1→S3) with progressively improved architectures.

## Architecture

### Agent Versions (`gui_agents/`)
- **s1**: Original hierarchical agent with Manager+Worker pattern using knowledge base retrieval
- **s2**: Improved version with same hierarchy, better grounding, and episodic memory
- **s2_5**: Simplified architecture, performance improvements
- **s3**: Current SOTA - flat architecture (no hierarchy), supports code agent for data tasks

### Core Components (per version)
```
agents/
├── agent_s.py      # Main agent class (AgentS3 extends UIAgent)
├── worker.py       # Generates actions from screenshots + instructions
├── grounding.py    # ACI classes for UI coordinate grounding (OSWorldACI)
└── code_agent.py   # (s3) Python/Bash execution for data manipulation

core/
├── engine.py       # LMM backends (OpenAI, Anthropic, Gemini, Azure, vLLM, HuggingFace)
├── mllm.py         # LMMAgent wrapper for message handling
└── module.py       # BaseModule for agent components

memory/
└── procedural_memory.py  # System prompts and action API documentation
```

### ACI (Agent-Computer Interface)
Platform-specific UI interaction in `s1/aci/`:
- `MacOSACI.py`: Uses AppKit/ApplicationServices for accessibility tree
- `WindowsOSACI.py`: Uses pywinauto/win32gui
- `LinuxOSACI.py`: Uses pyatspi

Actions are decorated with `@agent_action` and include: `click`, `type`, `hotkey`, `scroll`, `done`, `fail`, `call_code_agent`.

## Key Patterns

### Engine Configuration
```python
engine_params = {
    "engine_type": "openai",  # openai|anthropic|gemini|azure|vllm|huggingface|open_router
    "model": "gpt-5-2025-08-07",
    "temperature": 0.0,  # Force to 1.0 for o3 models
}
```

### Grounding Model Setup
UI-TARS models require width/height matching their output resolution:
- UI-TARS-1.5-7B: 1920×1080
- UI-TARS-72B: 1000×1000

### LLM Calls
Use `call_llm_safe()` for retries, `call_llm_formatted()` for format validation with feedback loop. See `utils/common_utils.py`.

### Procedural Memory
System prompts are dynamically constructed in `PROCEDURAL_MEMORY.construct_simple_worker_procedural_memory()` by introspecting the ACI class's `@agent_action` methods.

## CLI Entry Point
`agent_s` command (defined in `setup.py`) runs `gui_agents/s3/cli_app.py:main`.

Required args: `--ground_provider`, `--ground_url`, `--ground_model`, `--grounding_width`, `--grounding_height`

## Development Commands
```bash
# Install in editable mode
pip install -e .

# Required external dependency (for pytesseract)
# Windows: choco install tesseract  OR  winget install UB-Mannheim.TesseractOCR
# Mac: brew install tesseract
# Linux: apt install tesseract-ocr

# Run agent
agent_s --provider openai --model gpt-5-2025-08-07 --ground_provider huggingface --ground_url <url> --ground_model ui-tars-1.5-7b --grounding_width 1920 --grounding_height 1080
```

## OSWorld Evaluation
Evaluation scripts are in `osworld_setup/s{1,2,2_5,3}/`. The `run.py` files integrate with OSWorld's `DesktopEnv` VM infrastructure.

## Code Conventions
- Logger name: `"desktopenv.agent"` for agent-related logging
- Response parsing: Use `split_thinking_response()` for `<thoughts>/<answer>` tags
- Code extraction: Use `parse_code_from_string()` for triple-backtick code blocks
- Formatter: `black` (in dev dependencies)

## Environment Variables
See `models.md` for full list. Key ones:
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`
- `AZURE_OPENAI_API_BASE`, `AZURE_OPENAI_API_KEY`
- `OCR_SERVER_ADDRESS` (for s1 OCR grounding)

## bBoN (Behavior Best-of-N)
S3 includes `bbon/` for trajectory evaluation:
- `behavior_narrator.py`: Generates captions from action screenshots
- `comparative_judge.py`: Compares multiple rollouts to select best trajectory
