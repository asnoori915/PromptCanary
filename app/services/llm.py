import os, json, logging
from typing import Optional

DEFAULT_FALLBACK = {
    "clarity_score": 0.7,
    "specificity_score": 0.6,
    "risk_of_hallucination": 0.4,
    "overall_score": 0.65,
    "notes": "Tighten wording; add explicit constraints and success criteria."
}

def _fallback(reason: str):
    logging.warning(f"[judge_prompt] Falling back to default: {reason}")
    return DEFAULT_FALLBACK.copy()

# Lazy import so app can run even if openai package/key is not ready
_client = None
def _get_client():
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
    Returns JSON-like dict with scores + notes.
    Never raises; always returns something usable.
    """
    client = _get_client()
    if client is None:
        return _fallback("no OPENAI_API_KEY")

    system = "You are a strict evaluator of LLM prompts. Respond ONLY with compact JSON."
    user = f"""Evaluate the following PROMPT (and RESPONSE if given).

PROMPT:
{prompt}

RESPONSE:
{response or '(none)'}

Return JSON with keys:
clarity_score (0-1), specificity_score (0-1), risk_of_hallucination (0-1), overall_score (0-1), notes (short).
"""

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
    Returns a rewritten prompt. Never raises.
    """
    client = _get_client()
    if client is None:
        return f"{original.strip()} (Rewrite: be more specific; add constraints and success criteria.)"

    system = "Rewrite prompts to be concise, unambiguous, and outcome-oriented under 40 words. Return ONLY the rewritten prompt text."
    user = f"Original:\n{original}\n\nConsiderations:\n{notes or 'Improve clarity and include success criteria.'}"

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
