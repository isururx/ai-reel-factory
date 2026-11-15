import json
from unittest.mock import patch

import pytest

from app.services import script_generation


def _context():
    return {
        "profile": {},
        "strategy": {},
        "brief": "Create an engaging science Reel.",
        "source_url": None,
    }


def _response(word_count):
    narration = " ".join(f"word{i}" for i in range(word_count))
    return json.dumps({
        "title": "A science story",
        "hook": "Here is a surprising science story.",
        "narration": narration,
        "caption": "Discover more.",
        "hashtags": ["#science"],
        "estimated_duration_seconds": 80,
        "evaluation": {
            "hook_score": 8,
            "storytelling_score": 8,
            "originality_score": 8,
            "visual_suitability_score": 8,
        },
    })


@pytest.mark.parametrize("word_count", [130, 170, 172, 200, 210])
def test_accepts_narration_inside_new_hard_word_range(word_count):
    with patch.object(
        script_generation,
        "_generate_with_fallback",
        return_value=(_response(word_count), {"provider": "gemini", "model": "test", "attempts": []}),
    ):
        result = script_generation.generate_script(_context())

    assert len(result["narration"].split()) == word_count


@pytest.mark.parametrize("word_count", [129, 211])
def test_rejects_narration_outside_new_hard_word_range(word_count):
    with patch.object(
        script_generation,
        "_generate_with_fallback",
        return_value=(_response(word_count), {"provider": "gemini", "model": "test", "attempts": []}),
    ):
        with pytest.raises(RuntimeError, match="130–210 words"):
            script_generation.generate_script(_context())


def test_prompt_sets_150_to_200_word_target_and_130_to_210_hard_range():
    prompt = script_generation._prompt(_context())

    assert "Narration target: 150–200 words" in prompt
    assert "Hard narration range: 130–210 words" in prompt
