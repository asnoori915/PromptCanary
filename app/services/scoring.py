def heuristic_scores(prompt: str, response: str | None = None) -> dict:
    words = len(prompt.split())
    length_score = max(0.0, min(1.0, 1 - abs(words - 40) / 60))  # peak near 40 words
    vague_terms = ["maybe","sort of","kind of","roughly","approximately"]
    vagueness = sum(prompt.lower().count(t) for t in vague_terms)
    clarity_score = max(0.0, 1.0 - 0.15 * vagueness)
    toxicity_score = 1.0
    return {
        "length_score": round(length_score,3),
        "clarity_score": round(clarity_score,3),
        "toxicity_score": round(toxicity_score,3)
    }
