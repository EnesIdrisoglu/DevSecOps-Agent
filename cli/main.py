"""Komut satırı arayüzü."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from devsecops_ai_agent.agents.supervisor import SupervisorAgent
from devsecops_ai_agent.tools.database import DEFAULT_DB_PATH
from devsecops_ai_agent.database.seed import seed


DEMO_QUESTIONS = ["payments projesi release'e uygun mu?", "payments son job neden başarısız?", "payments karne durumu nedir?"]


def main() -> None:
    parser = argparse.ArgumentParser(description="DevSecOps verilerini Türkçe sorgulayın")
    parser.add_argument("question", nargs="*", help="sorunuz")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.demo:
        seed(args.db)
        questions = DEMO_QUESTIONS
    else:
        questions = [" ".join(args.question)] if args.question else []
    agent = SupervisorAgent()
    if questions:
        for question in questions:
            print(f"Soru: {question}\n{agent.answer(question)}\n")
    else:
        print("DevSecOps Agent (çıkmak için 'çıkış')")
        for line in sys.stdin:
            if line.strip().lower() in {"çıkış", "exit", "quit"}: break
            print(agent.answer(line))


if __name__ == "__main__":
    main()
