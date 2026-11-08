from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.core.db import get_db
from app.domain.report_context import DISCLAIMER
from app.main import app
from app.service import report_service as rs

ID = "00000000-0000-0000-0000-000000000001"
H = {"X-Service-Token": "t"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "SERVICE_TOKEN", "t")
    monkeypatch.setitem(app.dependency_overrides, get_db, lambda: None)
    monkeypatch.setattr(rs.diagnosis_repo, "get", lambda db, i: {"signal": {}} if str(i) == ID else None)
    return TestClient(app)


def _graph(monkeypatch, outcome):
    monkeypatch.setattr(rs, "report_graph", SimpleNamespace(invoke=lambda s: {"report": "본문", "outcome": outcome}))


def test_통과한_리포트에는_면책_문구(client, monkeypatch):
    _graph(monkeypatch, "passed")
    r = client.post("/api/report", json={"diagnosisId": ID}, headers=H)
    assert r.status_code == 200 and r.text.endswith(DISCLAIMER)
    assert r.headers["X-Report-Outcome"] == "passed"


def test_공고_없음은_그대로(client, monkeypatch):
    _graph(monkeypatch, "no_docs")
    r = client.post("/api/report", json={"diagnosisId": ID}, headers=H)
    assert r.text == "본문"


def test_없는_진단은_404(client):
    r = client.post("/api/report", json={"diagnosisId": "00000000-0000-0000-0000-000000000002"}, headers=H)
    assert r.status_code == 404


def test_토큰_없으면_401(client):
    assert client.post("/api/report", json={"diagnosisId": ID}).status_code == 401