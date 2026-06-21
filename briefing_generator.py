from ai_agent import get_openai_client

def generate_pre_meeting_brief(student_name, student_context, student_facts, session_summaries):
    """Generates a structured pre-meeting brief for the coach using current stats and past memories."""
    client = get_openai_client()
    
    prompt = f"""
    You are an expert student success advisor preparing a brief for a Coach before they meet with their student, {student_name}.
    
    Using the provided data, generate a highly focused, scannable pre-meeting brief.
    
    DATA INVENTORY:
    Current Academic Profile (Grades, Attendance, Schedule): 
    {student_context}
    
    Factual Memory (Traits, stressors, patterns):
    {student_facts}
    
    Past Session Summaries (Chronological history of meetings):
    {session_summaries}
    
    FORMAT YOUR RESPONSE STRICTLY WITH THESE SECTIONS (Use Markdown):
    ## 📊 Current Academic Situation
    (Briefly summarize their current grades, attendance, and any immediate flags)
    
    ## 🔄 What Changed Since Last Session
    (Compare their past summaries to their current context. Highlight progress or regression)
    
    ## ⚠️ Open Concerns
    (Identify any unresolved issues, academic risks, or personal stressors)
    
    ## 💬 Conversation Starters for Today
    (Provide 2-3 specific, empathetic questions the coach can use to open the meeting based on this data. Do not just ask "how are you?")
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-5.4-mini-2026-03-17",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3 # Low temperature for factual consistency
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating brief: {e}"