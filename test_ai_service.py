import asyncio
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models.recommendation import (
    PriorityDecision,
    PriorityDecisionList,
)
from app.models.todo import Todo
from app.services.ai import (
    AIRecommendationError,
    AIRecommendationService,
    PrioritySuggestion,
    PrioritySuggestionList,
    suggest_priority,
)


class FakeResponsesAPI:
    def __init__(self, parsed_output: object) -> None:
        self.parsed_output = parsed_output
        self.kwargs: dict[str, object] = {}

    async def parse(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=self.parsed_output)


def test_ai_service_uses_gpt_5_5_structured_output() -> None:
    parsed_output = PriorityDecisionList(
        recommendations=[
            PriorityDecision(todo_id=2, reason="마감일이 더 가깝습니다."),
            PriorityDecision(todo_id=1, reason="그다음으로 처리합니다."),
        ]
    )
    responses_api = FakeResponsesAPI(parsed_output)
    service = AIRecommendationService(responses_api=responses_api)
    todos = [
        Todo(id=1, title="Write tests", due="2026-06-30"),
        Todo(id=2, title="Submit report", due="2026-06-25"),
    ]

    result = asyncio.run(service.recommend(todos))

    assert [item.todo_id for item in result] == [2, 1]
    assert responses_api.kwargs["model"] == "gpt-5.5"
    assert responses_api.kwargs["text_format"] is PriorityDecisionList
    assert responses_api.kwargs["reasoning"] == {"effort": "low"}
    payload = json.loads(responses_api.kwargs["input"])
    assert payload["timezone"] == "Asia/Seoul"
    assert payload["todos"] == [
        {
            "todo_id": 1,
            "title": "Write tests",
            "due": "2026-06-30",
        },
        {
            "todo_id": 2,
            "title": "Submit report",
            "due": "2026-06-25",
        },
    ]


@pytest.mark.parametrize(
    "parsed_output",
    [
        None,
        PriorityDecisionList(
            recommendations=[
                PriorityDecision(todo_id=1, reason="첫 번째입니다."),
                PriorityDecision(todo_id=1, reason="중복입니다."),
            ]
        ),
        PriorityDecisionList(
            recommendations=[
                PriorityDecision(todo_id=999, reason="없는 항목입니다."),
            ]
        ),
    ],
)
def test_ai_service_rejects_invalid_results(parsed_output: object) -> None:
    service = AIRecommendationService(responses_api=FakeResponsesAPI(parsed_output))
    todos = [
        Todo(id=1, title="First"),
        Todo(id=2, title="Second"),
    ]

    with pytest.raises(AIRecommendationError):
        asyncio.run(service.recommend(todos))


def test_priority_reason_must_be_one_line() -> None:
    with pytest.raises(ValidationError):
        PriorityDecision(todo_id=1, reason="첫 번째 이유\n두 번째 줄")


class FakeSyncResponsesAPI:
    def __init__(
        self,
        parsed_output: object = None,
        error: Exception | None = None,
    ) -> None:
        self.parsed_output = parsed_output
        self.error = error
        self.kwargs: dict[str, object] = {}

    def parse(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        if self.error is not None:
            raise self.error
        return SimpleNamespace(output_parsed=self.parsed_output)


def test_suggest_priority_returns_parsed_gpt_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses_api = FakeSyncResponsesAPI(
        PrioritySuggestionList(
            suggestions=[
                PrioritySuggestion(
                    title="Submit report",
                    reason="마감일이 가장 가깝습니다.",
                    rank=1,
                ),
                PrioritySuggestion(
                    title="Write tests",
                    reason="보고서 제출 후 처리합니다.",
                    rank=2,
                ),
            ]
        )
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.ai.OpenAI",
        lambda api_key: SimpleNamespace(responses=responses_api),
    )

    result = suggest_priority(
        [
            {"title": "Write tests", "due": "2026-06-30"},
            {"title": "Submit report", "due": "2026-06-25"},
        ]
    )

    assert result == [
        {
            "title": "Submit report",
            "reason": "마감일이 가장 가깝습니다.",
            "rank": 1,
        },
        {
            "title": "Write tests",
            "reason": "보고서 제출 후 처리합니다.",
            "rank": 2,
        },
    ]
    assert responses_api.kwargs["model"] == "gpt-5.5"
    assert responses_api.kwargs["text_format"] is PrioritySuggestionList


def test_suggest_priority_empty_list_skips_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    result = suggest_priority([])

    assert result == []


def test_suggest_priority_without_api_key_falls_back_to_due_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = suggest_priority(
        [
            Todo(id=1, title="No due date"),
            Todo(id=2, title="Later", due="2026-07-01"),
            Todo(id=3, title="Sooner", due="2026-06-25"),
        ]
    )

    assert [item["title"] for item in result] == [
        "Sooner",
        "Later",
        "No due date",
    ]
    assert [item["rank"] for item in result] == [1, 2, 3]


def test_suggest_priority_invalid_due_dates_sort_last(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = suggest_priority(
        [
            {"title": "Invalid due", "due": "not-a-date"},
            {"title": "Sooner", "due": "2026-06-25"},
        ]
    )

    assert [item["title"] for item in result] == ["Sooner", "Invalid due"]


def test_suggest_priority_invalid_gpt_result_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses_api = FakeSyncResponsesAPI(
        PrioritySuggestionList(
            suggestions=[
                PrioritySuggestion(
                    title="Wrong title",
                    reason="입력에 없는 항목입니다.",
                    rank=1,
                )
            ]
        )
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.ai.OpenAI",
        lambda api_key: SimpleNamespace(responses=responses_api),
    )

    result = suggest_priority(
        [
            {"title": "Later", "due": "2026-07-01"},
            {"title": "Sooner", "due": "2026-06-25"},
        ]
    )

    assert [item["title"] for item in result] == ["Sooner", "Later"]


def test_suggest_priority_unparsed_gpt_result_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses_api = FakeSyncResponsesAPI(parsed_output={"suggestions": []})
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.ai.OpenAI",
        lambda api_key: SimpleNamespace(responses=responses_api),
    )

    result = suggest_priority(
        [
            {"title": "Later", "due": "2026-07-01"},
            {"title": "Sooner", "due": "2026-06-25"},
        ]
    )

    assert [item["title"] for item in result] == ["Sooner", "Later"]


def test_suggest_priority_api_failure_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses_api = FakeSyncResponsesAPI(error=RuntimeError("API unavailable"))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.ai.OpenAI",
        lambda api_key: SimpleNamespace(responses=responses_api),
    )

    result = suggest_priority(
        [
            {"title": "Later", "due": "2026-07-01"},
            {"title": "Sooner", "due": "2026-06-25"},
        ]
    )

    assert [item["title"] for item in result] == ["Sooner", "Later"]
    assert all(set(item) == {"title", "reason", "rank"} for item in result)
