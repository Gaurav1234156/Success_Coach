from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from agent_tools import get_pending_signals, create_calendar_event, update_sheet_actioned

def get_coach_agent():
    llm = ChatOpenAI(model="gpt-5.4-mini-2026-03-17", temperature=0)
    
    # We added the new "eyes" tool to the list!
    tools = [get_pending_signals, create_calendar_event, update_sheet_actioned]
    
    agent = create_react_agent(llm, tools)
    return agent
