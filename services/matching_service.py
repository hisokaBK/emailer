from __future__ import annotations

from services.validation_service import sanitize_text


def estimate_match(profile: dict, offer_text: str) -> dict:
    text = sanitize_text(offer_text).lower()
    skills = []
    for group in profile.get("technical_skills", {}).values():
        for skill in group:
            if skill.lower() in text:
                skills.append(skill)
    profile_tokens = []
    for value in profile.get("technical_skills", {}).values():
        profile_tokens.extend([item.lower() for item in value])
    score = min(100, max(0, round((len(set(skills)) / max(1, len(set(profile_tokens)))) * 100))) if profile_tokens else 0
    return {
        "score": score,
        "matching_skills": sorted(set(skills)),
        "missing_requirements": [],
        "to_verify": [],
    }
