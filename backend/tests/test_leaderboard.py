import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.models.leaderboard import get_leaderboard_rows, upsert_leaderboard_entry


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_upsert_inserts_new_entry(db_session):
    upsert_leaderboard_entry(
        db_session, series_id="D1", model_name="ARIMA", metrics={"mae": 1.0, "rmse": 2.0, "smape": 3.0}, job_id="job1"
    )
    db_session.commit()

    rows = get_leaderboard_rows(db_session)
    assert len(rows) == 1
    assert rows[0]["model_name"] == "ARIMA"
    assert rows[0]["avg_mae"] == 1.0
    assert rows[0]["n_series"] == 1


def test_upsert_updates_existing_entry_rather_than_duplicating(db_session):
    upsert_leaderboard_entry(
        db_session, series_id="D1", model_name="ARIMA", metrics={"mae": 1.0, "rmse": 2.0, "smape": 3.0}, job_id="job1"
    )
    db_session.commit()

    upsert_leaderboard_entry(
        db_session, series_id="D1", model_name="ARIMA", metrics={"mae": 5.0, "rmse": 6.0, "smape": 7.0}, job_id="job2"
    )
    db_session.commit()

    rows = get_leaderboard_rows(db_session)
    assert len(rows) == 1
    assert rows[0]["avg_mae"] == 5.0
    assert rows[0]["n_series"] == 1


def test_leaderboard_aggregates_per_model_across_series_and_sorts_by_smape(db_session):
    upsert_leaderboard_entry(
        db_session, series_id="D1", model_name="ARIMA", metrics={"mae": 10.0, "rmse": 12.0, "smape": 5.0}, job_id="j"
    )
    upsert_leaderboard_entry(
        db_session, series_id="D2", model_name="ARIMA", metrics={"mae": 20.0, "rmse": 22.0, "smape": 15.0}, job_id="j"
    )
    upsert_leaderboard_entry(
        db_session,
        series_id="D1",
        model_name="LightGBM",
        metrics={"mae": 1.0, "rmse": 1.5, "smape": 1.0},
        job_id="j",
    )
    db_session.commit()

    rows = get_leaderboard_rows(db_session)

    by_model = {r["model_name"]: r for r in rows}
    assert by_model["ARIMA"]["avg_mae"] == pytest.approx(15.0)
    assert by_model["ARIMA"]["n_series"] == 2
    assert by_model["LightGBM"]["n_series"] == 1
    # sorted best (lowest smape) first
    assert rows[0]["model_name"] == "LightGBM"
    assert rows[1]["model_name"] == "ARIMA"
