WEIGHTS = {
    "ranking": 0.45,
    "backtesting": 0.20,
    "confidence": 0.20,
    "risk": 0.15,
}


def clamp(value, minimum=0.0, maximum=1.0):
    if value is None:
        return 0.5
    return max(minimum, min(maximum, float(value)))


def normalize_backtesting(total_return):
    # 0 % -> 0.50; +50 % -> 1.00; -50 % -> 0.00.
    return clamp(0.5 + float(total_return or 0.0))


def classify_decision(score):
    if score >= 0.75:
        return "OPORTUNIDAD_ALTA"
    if score >= 0.60:
        return "OPORTUNIDAD_MEDIA"
    if score >= 0.45:
        return "OBSERVAR"
    return "OPORTUNIDAD_BAJA"


def calculate_decision(ranking_score, backtesting_return, confidence, risk):
    ranking_score = clamp(ranking_score)
    backtesting_score = normalize_backtesting(backtesting_return)
    confidence = clamp(confidence)
    risk = clamp(abs(float(risk or 0.0)))
    risk_component = 1.0 - risk

    final_score = (
        ranking_score * WEIGHTS["ranking"]
        + backtesting_score * WEIGHTS["backtesting"]
        + confidence * WEIGHTS["confidence"]
        + risk_component * WEIGHTS["risk"]
    )
    final_score = clamp(final_score)
    decision = classify_decision(final_score)

    explanation = (
        f"Score cuantitativo={ranking_score:.3f}; "
        f"backtesting normalizado={backtesting_score:.3f}; "
        f"confianza Walk-Forward={confidence:.3f}; "
        f"riesgo MDD={risk:.3f}; score final={final_score:.3f}."
    )

    return {
        "backtesting_score": backtesting_score,
        "final_score": final_score,
        "decision": decision,
        "explanation": explanation,
    }
