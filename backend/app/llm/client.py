import anthropic

from app.core.config import get_settings
from app.llm.holiday_check import cross_check_features
from app.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from app.llm.schema import BatchDiagnosticOutput, ConfirmedSeriesDiagnostic
from app.profiling.schema import SeriesProfile

MODEL = "claude-opus-5"


def run_diagnostics(profiles: list[SeriesProfile]) -> list[ConfirmedSeriesDiagnostic]:
    if not profiles:
        return []

    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(profiles)}],
        output_format=BatchDiagnosticOutput,
    )
    batch = response.parsed_output

    profiles_by_id = {p.series_id: p for p in profiles}
    confirmed_results = []
    for diag in batch.results:
        profile = profiles_by_id.get(diag.series_id)
        if profile is None:
            continue  # LLM echoed a series_id we didn't send; skip rather than guess a date range
        confirmed_features = cross_check_features(
            diag.suggested_features, profile.start_timestamp, profile.end_timestamp
        )
        confirmed_results.append(
            ConfirmedSeriesDiagnostic(
                series_id=diag.series_id,
                narrative=diag.narrative,
                suggested_features=confirmed_features,
                suggested_models=diag.suggested_models,
            )
        )

    return confirmed_results
