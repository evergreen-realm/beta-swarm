"""API provider configuration for the Beta Swarm free-tier stack."""

import os
from typing import Dict, Any

# Ensure .env is loaded regardless of entry point
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
except ImportError:
    pass

API_CONFIG: Dict[str, Dict[str, Any]] = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "models": ["openai/gpt-3.5-turbo", "meta-llama/llama-3.1-8b-instruct"],
        "limits": {"rpm": 20, "rpd": 200},
        "use_for": ["general_chat", "fallback", "coding"],
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "models": ["llama3-8b-8192", "mixtral-8x7b-32768"],
        "limits": {"rpm": 100, "rpd": 14400},
        "use_for": ["speed_critical", "streaming", "coding"],
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "key_env": "CEREBRAS_API_KEY",
        "models": ["llama3.1-8b"],
        "limits": {"rpm": 60, "rpd": 60000},
        "use_for": ["high_throughput", "batch_processing"],
    },
    "sambanova": {
        "base_url": "https://api.sambanova.ai/v1",
        "key_env": "SAMBANOVA_API_KEY",
        "models": ["Meta-Llama-3.1-8B-Instruct"],
        "limits": {"rpm": 60, "rpd": 60000},
        "use_for": ["reasoning", "complex_tasks"],
    },
    "google_ai_studio": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "key_env": "GOOGLE_API_KEY",
        "models": ["gemini-1.5-flash", "gemini-2.5-flash"],
        "limits": {"rpm": 60, "rpd": 1500},
        "use_for": ["general_chat", "research", "summarization"],
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "key_env": "MISTRAL_API_KEY",
        "models": ["mistral-small-latest", "mistral-tiny"],
        "limits": {"rpm": 60, "rpd": 1000000},
        "use_for": ["general_chat", "classification"],
    },
    "cloudflare": {
        "base_url": "https://api.cloudflare.com/client/v4/ai",
        "key_env": "CLOUDFLARE_API_KEY",
        "models": ["@cf/meta/llama-3.1-8b-instruct"],
        "limits": {"rpm": 60, "rpd": 10000},
        "use_for": ["edge_inference", "fast_classification"],
    },
    "huggingface": {
        "base_url": "https://api-inference.huggingface.co/models",
        "key_env": "HUGGINGFACE_API_KEY",
        "models": ["meta-llama/Llama-3.1-8B-Instruct"],
        "limits": {"rpm": 50, "rpd": 300},
        "use_for": ["experimentation", "model_testing"],
    },
    "github": {
        "base_url": "https://models.inference.ai.azure.com",
        "key_env": "GITHUB_TOKEN",
        "models": ["Meta-Llama-3.1-8B-Instruct"],
        "limits": {"rpm": 10, "rpd": 150},
        "use_for": ["coding", "codex_tasks"],
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "key_env": "DEEPSEEK_API_KEY",
        "models": ["deepseek-chat", "deepseek-coder"],
        "limits": {"rpm": 60, "rpd": 5000000},
        "use_for": ["reasoning", "coding", "math"],
    },
}

def get_available_keys() -> Dict[str, str]:
    keys = {}
    for provider, config in API_CONFIG.items():
        key = os.getenv(config["key_env"])
        if key:
            keys[provider] = key
    return keys

def get_provider_for_task(task_type: str) -> list:
    suitable = []
    for provider, config in API_CONFIG.items():
        if task_type in config.get("use_for", []):
            suitable.append(provider)
    return suitable
