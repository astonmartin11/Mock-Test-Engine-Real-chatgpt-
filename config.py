from __future__ import annotations
import os
from dotenv import load_dotenv
load_dotenv()

def get_env(name: str, required: bool = True) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st
        secret_value = st.secrets.get(name)
        if secret_value:
            return str(secret_value)
    except Exception:
        pass
    if required:
        raise RuntimeError(f"Missing configuration: {name}")
    return None

def models() -> dict[str, str]:
    return {
        "gemini": get_env("GEMINI_MODEL", False) or "gemini-3.8-flash",
        "groq": get_env("GROQ_REASONING_MODEL", False) or "openai/gpt-oss-120b",
        "embedding": get_env("EMBEDDING_MODEL", False) or "gemini-embedding-2",
    }
