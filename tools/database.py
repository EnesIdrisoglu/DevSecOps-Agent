"""SQLite şeması ve salt-okunur kanıt araçları."""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_DIR / "database" / "devsecops.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS scans (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
  scanned_at TEXT NOT NULL, status TEXT NOT NULL, branch TEXT, commit_sha TEXT
);
CREATE TABLE IF NOT EXISTS scan_details (
  id INTEGER PRIMARY KEY, scan_id INTEGER NOT NULL REFERENCES scans(id),
  scanner TEXT NOT NULL, duration_seconds INTEGER, total_findings INTEGER,
  summary TEXT
);
CREATE TABLE IF NOT EXISTS findings (
  id INTEGER PRIMARY KEY, scan_id INTEGER NOT NULL REFERENCES scans(id),
  severity TEXT NOT NULL, title TEXT NOT NULL, cve TEXT, status TEXT NOT NULL,
  component TEXT
);
CREATE TABLE IF NOT EXISTS releases (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
  version TEXT NOT NULL, released_at TEXT NOT NULL, decision TEXT NOT NULL,
  reason TEXT
);
CREATE TABLE IF NOT EXISTS scorecards (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
  metric TEXT NOT NULL, target REAL NOT NULL, actual REAL NOT NULL,
  measured_at TEXT NOT NULL, UNIQUE(project_id, metric)
);
CREATE TABLE IF NOT EXISTS job_logs (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
  job_name TEXT NOT NULL, status TEXT NOT NULL, started_at TEXT NOT NULL,
  finished_at TEXT, error TEXT, source TEXT
);
CREATE INDEX IF NOT EXISTS idx_scans_project_time ON scans(project_id, scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_project_time ON job_logs(project_id, started_at DESC);
"""


def connect(db_path: str | Path = DEFAULT_DB_PATH, *, readonly: bool = False) -> sqlite3.Connection:
    path = Path(db_path).expanduser().resolve()
    if readonly:
        if not path.exists():
            raise FileNotFoundError(f"Veritabanı bulunamadı: {path}")
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def readonly_connection(db_path: str | Path = DEFAULT_DB_PATH) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path, readonly=True)
    try:
        yield conn
    finally:
        conn.close()


def _project_id(conn: sqlite3.Connection, project: str) -> int | None:
    row = conn.execute("SELECT id FROM projects WHERE lower(name) = lower(?)", (project,)).fetchone()
    return int(row["id"]) if row else None


def list_projects(db_path: str | Path = DEFAULT_DB_PATH) -> list[str]:
    with readonly_connection(db_path) as conn:
        return [r["name"] for r in conn.execute("SELECT name FROM projects ORDER BY name")]


def projects_with_open_findings(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    """Son taramasında çözülmemiş bulgusu olan projeleri ve sayılarını döndürür."""
    with readonly_connection(db_path) as conn:
        rows = conn.execute(
            """
            WITH latest_scans AS (
                SELECT project_id, MAX(scanned_at) AS scanned_at
                FROM scans GROUP BY project_id
            )
            SELECT p.name AS project, COUNT(f.id) AS finding_count
            FROM latest_scans ls
            JOIN projects p ON p.id = ls.project_id
            JOIN scans s ON s.project_id = ls.project_id AND s.scanned_at = ls.scanned_at
            JOIN findings f ON f.scan_id = s.id AND f.status != 'resolved'
            GROUP BY p.id, p.name ORDER BY finding_count DESC, p.name
            """
        ).fetchall()
        return [dict(row) for row in rows]


def all_open_findings(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    """Tüm projelerin son taramasındaki çözülmemiş bulguları döndürür."""
    with readonly_connection(db_path) as conn:
        rows = conn.execute(
            """
            WITH latest_scans AS (
                SELECT project_id, MAX(scanned_at) AS scanned_at
                FROM scans GROUP BY project_id
            )
            SELECT p.name AS project, f.severity, f.title, f.cve, f.component
            FROM latest_scans ls
            JOIN projects p ON p.id = ls.project_id
            JOIN scans s ON s.project_id = ls.project_id AND s.scanned_at = ls.scanned_at
            JOIN findings f ON f.scan_id = s.id AND f.status != 'resolved'
            ORDER BY CASE f.severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, p.name
            """
        ).fetchall()
        return [dict(row) for row in rows]


def total_open_findings(db_path: str | Path = DEFAULT_DB_PATH) -> int:
    """Son taramalardaki çözülmemiş bulguların toplam sayısı."""
    return len(all_open_findings(db_path))


def projects_by_scanner(scanner: str, db_path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with readonly_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT p.name AS project, d.scanner, s.status, s.scanned_at, d.total_findings
            FROM projects p JOIN scans s ON s.project_id=p.id
            JOIN scan_details d ON d.scan_id=s.id
            WHERE lower(d.scanner) LIKE lower(?)
              AND s.scanned_at=(SELECT MAX(s2.scanned_at) FROM scans s2 WHERE s2.project_id=p.id)
            ORDER BY p.name
        """, (f"%{scanner}%",)).fetchall()
        return [dict(row) for row in rows]


def release_portfolio(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    """Her proje için release uygunluğunu yalnızca high/critical bulgularla değerlendirir."""
    with readonly_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT p.name AS project, r.version, r.decision,
                   COALESCE(SUM(CASE WHEN f.severity IN ('critical','high') THEN 1 ELSE 0 END), 0) AS blocking_findings,
                   COALESCE(SUM(CASE WHEN f.severity IN ('medium','low') THEN 1 ELSE 0 END), 0) AS non_blocking_findings
            FROM projects p
            LEFT JOIN releases r ON r.project_id = p.id
            LEFT JOIN scans s ON s.project_id = p.id AND s.scanned_at = (SELECT MAX(s2.scanned_at) FROM scans s2 WHERE s2.project_id = p.id)
            LEFT JOIN findings f ON f.scan_id = s.id AND f.status != 'resolved'
            GROUP BY p.id, p.name, r.version, r.decision ORDER BY p.name
            """
        ).fetchall()
        return [dict(row, suitable=(row["blocking_findings"] == 0)) for row in rows]


def project_risk_summary(project: str, db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    with readonly_connection(db_path) as conn:
        pid = _project_id(conn, project)
        if pid is None:
            return None
        scan = conn.execute("SELECT * FROM scans WHERE project_id=? ORDER BY scanned_at DESC LIMIT 1", (pid,)).fetchone()
        release = conn.execute("SELECT * FROM releases WHERE project_id=? ORDER BY released_at DESC LIMIT 1", (pid,)).fetchone()
        details = []
        findings = []
        if scan:
            details = [dict(r) for r in conn.execute(
                "SELECT scanner,duration_seconds,total_findings,summary FROM scan_details WHERE scan_id=?", (scan["id"],)
            )]
            findings = [dict(r) for r in conn.execute(
                "SELECT severity,title,cve,status,component FROM findings WHERE scan_id=? AND status != 'resolved' "
                "ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, id",
                (scan["id"],))]
        return {"project": project, "scan": dict(scan) if scan else None, "scan_details": details,
                "release": dict(release) if release else None, "findings": findings,
                "evidence_time": (scan["scanned_at"] if scan else None)}


def latest_failed_job(project: str, db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    with readonly_connection(db_path) as conn:
        pid = _project_id(conn, project)
        if pid is None:
            return None
        row = conn.execute("SELECT * FROM job_logs WHERE project_id=? AND status='failed' ORDER BY started_at DESC LIMIT 1", (pid,)).fetchone()
        return dict(row) if row else None


def scorecard_status(project: str, db_path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]] | None:
    with readonly_connection(db_path) as conn:
        pid = _project_id(conn, project)
        if pid is None:
            return None
        rows = conn.execute("SELECT metric,target,actual,measured_at FROM scorecards WHERE project_id=? ORDER BY metric", (pid,)).fetchall()
        return [dict(r, status="hedef karşılandı" if r["actual"] >= r["target"] else "eksik") for r in rows]


def safe_read_query(db_path: str | Path, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """Yalnızca tek bir SELECT sorgusunu çalıştırır; yazma/çoklu sorgu reddedilir."""
    normalized = query.strip().lower()
    if not re.match(r"^select\b", normalized) or ";" in normalized.rstrip(";"):
        raise ValueError("Yalnızca tek bir salt-okunur SELECT sorgusuna izin verilir")
    with readonly_connection(db_path) as conn:
        return [dict(row) for row in conn.execute(query, params)]
