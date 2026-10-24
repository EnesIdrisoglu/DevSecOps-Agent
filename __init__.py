"""DevSecOps AI Agent MVP."""

from dotenv import load_dotenv

load_dotenv()

from .agents.supervisor import SupervisorAgent

DevSecOpsAgent = SupervisorAgent

__all__ = ["DevSecOpsAgent"]
