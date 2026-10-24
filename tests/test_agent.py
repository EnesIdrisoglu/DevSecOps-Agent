import unittest

from devsecops_ai_agent.agents.findings_agent import FindingsAgent
from devsecops_ai_agent.agents.global_findings_agent import GlobalFindingsAgent
from devsecops_ai_agent.agents.global_metrics_agent import GlobalMetricsAgent
from devsecops_ai_agent.agents.state import AgentState


class SpecialistAgentTests(unittest.TestCase):
    def test_project_findings_agent(self):
        result = FindingsAgent().run(AgentState(question="bulguları getir", project="identity"))
        self.assertIn("JWT doğrulama", result.answer)

    def test_global_critical_filter(self):
        result = GlobalFindingsAgent().run(AgentState(question="sadece critical bulguları getir"))
        self.assertIn("CRITICAL", result.answer)
        self.assertNotIn("MEDIUM", result.answer)
        self.assertNotIn("LOW", result.answer)

    def test_global_metric_is_only_number(self):
        result = GlobalMetricsAgent().run(AgentState(question="toplam bulgu sayısı"))
        self.assertTrue(result.answer.isdigit())


if __name__ == "__main__":
    unittest.main()
