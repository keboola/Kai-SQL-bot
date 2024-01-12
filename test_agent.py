import unittest
from unittest.mock import MagicMock
from agent import SQLAgentCreator
from langchain.agents.agent_types import AgentType

class TestSQLAgentCreator(unittest.TestCase):
    def setUp(self):
        self.llm = MagicMock()
        self.toolkit = MagicMock()
        self.custom_tool_list = [MagicMock(), MagicMock()]
        self.memory = MagicMock()

    def test_create_agent(self):
        creator = SQLAgentCreator(self.llm, self.toolkit, self.custom_tool_list, self.memory)
        agent_executor = creator.create_agent()

        self.assertEqual(agent_executor.llm, self.llm)
        self.assertEqual(agent_executor.toolkit, self.toolkit)
        self.assertEqual(agent_executor.custom_tool_list, self.custom_tool_list)
        self.assertEqual(agent_executor.memory, self.memory)
        self.assertTrue(agent_executor.verbose)
        self.assertTrue(agent_executor.handle_parsing_errors)
        self.assertEqual(agent_executor.max_iterations, 50)
        self.assertEqual(agent_executor.agent_type, AgentType.OPENAI_FUNCTIONS)

if __name__ == '__main__':
    unittest.main()