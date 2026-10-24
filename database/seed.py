"""Tekrarlanabilir demo veritabanı oluşturur."""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from ..tools.database import connect, initialize_database, DEFAULT_DB_PATH


def seed(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    initialize_database(db_path)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with closing(connect(db_path)) as conn:
        with conn:
            conn.executescript("DELETE FROM findings; DELETE FROM scan_details; DELETE FROM scans; DELETE FROM releases; DELETE FROM scorecards; DELETE FROM job_logs; DELETE FROM projects;")
            project_names = ["payments", "catalog", "identity", "analytics", "mobile", "notifications", "checkout", "search"]
            conn.executemany("INSERT INTO projects(name) VALUES (?)", [(name,) for name in project_names])
            project_ids = {name: conn.execute("SELECT id FROM projects WHERE name=?", (name,)).fetchone()[0] for name in project_names}

            scans = {
                "payments": ("completed", "main", "a1b2c3d", "Trivy + Semgrep", 184),
                "identity": ("completed", "main", "i9d8c7b", "Snyk + Semgrep", 231),
                "catalog": ("completed", "main", "c4t5a6l", "Trivy", 98),
                "analytics": ("completed", "release/2.1", "an7l8yt", "SonarQube", 156),
                "mobile": ("completed", "main", "m1o2b3l", "MobSF", 205),
                "notifications": ("completed", "main", "n4o5t6f", "Trivy + Semgrep", 119),
                "checkout": ("completed", "main", "c7h8e9k", "Trivy + Snyk", 177),
                "search": ("completed", "main", "s1e2a3r", "SonarQube", 144),
            }
            scan_ids = {}
            for project, (status, branch, commit, scanner, duration) in scans.items():
                conn.execute("INSERT INTO scans(project_id,scanned_at,status,branch,commit_sha) VALUES (?,?,?,?,?)", (project_ids[project], now, status, branch, commit))
                scan_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                scan_ids[project] = scan_id
                conn.execute("INSERT INTO scan_details(scan_id,scanner,duration_seconds,total_findings,summary) VALUES (?,?,?,?,?)", (scan_id, scanner, duration, 0, f"{scanner} taraması tamamlandı."))

            findings = [
                ("payments", "critical", "Kimlik doğrulama bypass", "CVE-2026-10001", "open", "gateway"),
                ("payments", "high", "Güvensiz bağımlılık", "CVE-2026-10002", "open", "payments-api"),
                ("payments", "medium", "Eksik güvenlik başlığı", None, "resolved", "web"),
                ("identity", "critical", "JWT doğrulama zafiyeti", "CVE-2026-10011", "open", "auth-service"),
                ("identity", "high", "Zayıf parola politikası", None, "open", "user-api"),
                ("catalog", "low", "Eksik güvenlik başlığı", None, "resolved", "catalog-web"),
                ("mobile", "high", "Güvensiz deep link", "CVE-2026-10021", "open", "mobile-app"),
                ("checkout", "medium", "Loglarda hassas veri", None, "open", "checkout-api"),
                ("checkout", "low", "Eski TLS protokolü", None, "open", "payment-gateway"),
            ]
            conn.executemany("INSERT INTO findings(scan_id,severity,title,cve,status,component) VALUES (?,?,?,?,?,?)", [(scan_ids[p], s, t, c, st, component) for p, s, t, c, st, component in findings])
            for project, scan_id in scan_ids.items():
                count = conn.execute("SELECT COUNT(*) FROM findings WHERE scan_id=?", (scan_id,)).fetchone()[0]
                conn.execute("UPDATE scan_details SET total_findings=? WHERE scan_id=?", (count, scan_id))

            releases = [("payments", "v2.4.0", "review", "Kritik açık bulguları mevcut; otomatik karar verilmedi."), ("identity", "v5.8.1", "blocked", "Kritik JWT bulgusu açık."), ("catalog", "v3.2.0", "approved", "Kritik ve yüksek bulgu yok."), ("analytics", "v2.1.0", "approved", "Tarama temiz."), ("mobile", "v7.0.2", "review", "Yüksek deep link bulgusu açık."), ("notifications", "v4.5.0", "approved", "Release kriterleri karşılandı."), ("checkout", "v6.3.0", "review", "Orta seviye bulgular için ekip onayı bekleniyor."), ("search", "v2.9.0", "approved", "Tarama temiz.")]
            conn.executemany("INSERT INTO releases(project_id,version,released_at,decision,reason) VALUES (?,?,?,?,?)", [(project_ids[p], v, now, d, r) for p, v, d, r in releases])
            for project in project_names:
                conn.executemany("INSERT INTO scorecards(project_id,metric,target,actual,measured_at) VALUES (?,?,?,?,?)", [(project_ids[project], "kritik bulgu kapatma oranı", 100, 75 if project in {"payments", "identity"} else 100, now), (project_ids[project], "test kapsamı", 80, 72 if project == "mobile" else 86, now)])
            jobs = [("payments", "nightly-scan", "failed", "Container registry erişimi zaman aşımına uğradı", "scanner-runner-01"), ("identity", "nightly-scan", "failed", "Snyk API rate limit aşıldı", "scanner-runner-03"), ("catalog", "nightly-scan", "success", None, "scanner-runner-02"), ("analytics", "nightly-scan", "success", None, "scanner-runner-04"), ("mobile", "mobile-security-scan", "failed", "MobSF worker bağlantısı kesildi", "mobile-runner-01"), ("notifications", "nightly-scan", "success", None, "scanner-runner-02"), ("checkout", "nightly-scan", "success", None, "scanner-runner-05"), ("search", "nightly-scan", "success", None, "scanner-runner-04")]
            conn.executemany("INSERT INTO job_logs(project_id,job_name,status,started_at,finished_at,error,source) VALUES (?,?,?,?,?,?,?)", [(project_ids[p], j, st, now, now, e, src) for p, j, st, e, src in jobs])
    return Path(db_path).resolve()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args()
    print(f"Demo veritabanı hazır: {seed(args.db)}")
