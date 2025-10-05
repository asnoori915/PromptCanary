"""
LLM SERVICE - OpenAI integration for prompt evaluation and optimization

This service handles all interactions with OpenAI's API for:
1. Evaluating prompts and responses (judge_prompt)
2. Optimizing/rewriting prompts (optimize_prompt)

Key features:
- Graceful fallbacks when API is unavailable
- Structured JSON responses for evaluation
- Lazy client initialization to avoid startup failures
- Timeout protection and error handling
"""

import os, json, logging
from typing import Optional

# Default fallback scores when LLM evaluation fails
DEFAULT_FALLBACK = {
    "clarity_score": 0.7,
    "specificity_score": 0.6,
    "risk_of_hallucination": 0.4,
    "overall_score": 0.65,
    "notes": "Tighten wording; add explicit constraints and success criteria."
}

def _fallback(reason: str):
    """Log warning and return default scores when LLM evaluation fails."""
    logging.warning(f"[judge_prompt] Falling back to default: {reason}")
    return DEFAULT_FALLBACK.copy()

# Lazy import so app can run even if openai package/key is not ready
_client = None
def _get_client():
    """
    Get OpenAI client with lazy initialization.
    
    This allows the app to start even without OpenAI API key configured.
    Returns None if no API key is available.
    """
    global _client
    if _client is not None:
        return _client
    from openai import OpenAI  # import inside so missing pkg won't break startup
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    _client = OpenAI(api_key=api_key)
    return _client


def judge_prompt(prompt: str, response: Optional[str] = None) -> dict:
    """
    Evaluate a prompt (and optional response) using GPT-4o-mini.
    
    This is the core evaluation function that:
    1. Sends prompt/response to GPT-4o-mini for analysis
    2. Gets back structured scores (clarity, specificity, risk, overall)
    3. Returns fallback scores if API fails
    
    Input: prompt text, optional response text
    Output: dict with scores (0-1) and improvement notes
    
    Never raises exceptions - always returns usable data.
    """
    client = _get_client()
    if client is None:
        return _fallback("no OPENAI_API_KEY")

    # STEP 1: Build the evaluation prompt
    system = "You are a strict evaluator of LLM prompts. Respond ONLY with compact JSON."
    user = f"""Evaluate the following PROMPT (and RESPONSE if given).

PROMPT:
{prompt}

RESPONSE:
{response or '(none)'}

Return JSON with keys:
clarity_score (0-1), specificity_score (0-1), risk_of_hallucination (0-1), overall_score (0-1), notes (short).
"""

    # STEP 2: Call OpenAI API with structured JSON response
    try:
        out = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=0.2,
            timeout=30,  # hard time limit
        )
        content = out.choices[0].message.content
        data = json.loads(content)
        # basic shape guard
        if not isinstance(data, dict) or "notes" not in data:
            return _fallback("bad JSON shape")
        return data
    except Exception as e:
        # Network, auth, quota, or model errors land here
        return _fallback(f"exception: {type(e).__name__}")
    

def optimize_prompt(original: str, notes: Optional[str] = "") -> str:
    """
    Rewrite/optimize a prompt using GPT-4o-mini.
    
    This function:
    1. Takes an original prompt and improvement notes
    2. Uses LLM to generate a better version
    3. Returns fallback text if API fails
    
    Input: original prompt text, optional improvement notes
    Output: optimized prompt text
    
    Never raises exceptions - always returns usable text.
    """
    client = _get_client()
    if client is None:
        return f"{original.strip()} (Rewrite: be more specific; add constraints and success criteria.)"

    # STEP 1: Build the optimization prompt
    system = "Rewrite prompts to be concise, unambiguous, and outcome-oriented under 40 words. Return ONLY the rewritten prompt text."
    user = f"Original:\n{original}\n\nConsiderations:\n{notes or 'Improve clarity and include success criteria.'}"

    # STEP 2: Call OpenAI API to get optimized version
    try:
        out = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.2,
            timeout=30,
        )
        return (out.choices[0].message.content or "").strip()
    except Exception as e:
        logging.warning(f"[optimize_prompt] Falling back due to {type(e).__name__}")
        return f"{original.strip()} (Rewrite: be specific, add constraints, measurable success criteria.)"
