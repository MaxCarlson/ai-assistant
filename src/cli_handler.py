import argparse
import asyncio
from src.ui import start_chat_loop
from src.agent_manager import AgentManager
from src import task_manager
import re

class CLIAgent:
    def __init__(self, agent_manager: AgentManager, task_id: str, agent_mode: bool = False):
        self.agent_manager = agent_manager
        self.task_id = task_id
        self.agent_mode = agent_mode

    async def handle_task(self, user_input: str, conversation_history: list) -> str:
        if self.agent_mode:
            task = task_manager.get_task(self.task_id)
            if not task:
                return {"thought": "Error", "response": f"Task {self.task_id} not found."}

            task_manager.update_task_goal(self.task_id, user_input)
            
            response = await asyncio.to_thread(self.agent_manager.start_task, task)
            
            final_task_state = task_manager.get_task(self.task_id)
            history = final_task_state.get("history", [])
            
            final_response = "No response from agent."
            for i in reversed(history):
                if "Observation: Task marked as complete" in i:
                    final_response = i.replace("Observation: ", "")
                    break
                elif "Observation: " in i:
                    final_response = i.replace("Observation: ", "")
                    break
            
            return {"thought": "Done", "response": final_response}
        else:
            return await asyncio.to_thread(self.agent_manager.get_direct_response, user_input, conversation_history)

def run_cli():
    parser = argparse.ArgumentParser(description="AI Assistant CLI")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--model", type=str, default="gemini-2.5-pro", help="The model to use for the agent.")
    parser.add_argument("--sandbox", action="store_true", help="Enable sandbox mode.")
    parser.add_argument("--agent", action="store_true", help="Run in agent mode.")
    parser.add_argument("-t", "--temperature", type=float, default=0.7, help="Set the temperature for the model.")
    parser.add_argument("--top-p", type=float, default=1.0, help="Set the top-p for the model.")
    parser.add_argument("--top-k", type=int, default=40, help="Set the top-k for the model.")
    parser.add_argument("--max-output-tokens", type=int, default=1024, help="Set the maximum number of output tokens.")
    parser.add_argument("--grounding", action="store_true", help="Enable Google Search grounding.")
    parser.add_argument("--code-execution", action="store_true", help="Enable code execution.")
    args = parser.parse_args()

    try:
        agent_manager = AgentManager(
            model_name=args.model,
            debug=args.debug,
            sandbox=args.sandbox,
            temperature=args.temperature,
            top_p=args.top_p,
            top_k=args.top_k,
            max_output_tokens=args.max_output_tokens,
            grounding=args.grounding,
            code_execution=args.code_execution
        )
        task_id = task_manager.create_task("Chat with user.")
        conversational_agent = CLIAgent(agent_manager=agent_manager, task_id=task_id, agent_mode=args.agent)
        asyncio.run(start_chat_loop(agent=conversational_agent, agent_manager=agent_manager, debug=args.debug))
    except Exception as e:
        print(f"Initialization Error: {e}")