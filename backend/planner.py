import json
from datetime import datetime

class Planner:
    def __init__(self):
        self.plan = []
        self.current_step = 0
        self.history = []
        self.session_start = datetime.now().isoformat()
    
    def create_plan(self, task, llm_response):
        """Parse LLM response to extract plan steps"""
        # Look for numbered steps or bullet points
        lines = llm_response.split('\n')
        steps = []
        
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                # Remove numbering/bullets
                clean = line.lstrip('0123456789.-* ')
                if clean:
                    steps.append({'step': len(steps)+1, 'action': clean, 'status': 'pending'})
        
        if steps:
            self.plan = steps
            return True
        return False
    
    def update_step(self, step_num, status, result=None):
        """Update a plan step status"""
        for step in self.plan:
            if step['step'] == step_num:
                step['status'] = status
                if result:
                    step['result'] = result[:200]  # Truncate long results
                break
        self.current_step = step_num
    
    def get_current(self):
        """Get current step"""
        if self.current_step < len(self.plan):
            return self.plan[self.current_step]
        return None
    
    def get_progress(self):
        """Get completion progress"""
        if not self.plan:
            return 0
        completed = sum(1 for s in self.plan if s['status'] == 'completed')
        return completed / len(self.plan) * 100
    
    def add_to_history(self, event_type, content):
        """Add event to session history"""
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'content': content
        })
    
    def to_dict(self):
        """Serialize planner state"""
        return {
            'plan': self.plan,
            'current_step': self.current_step,
            'progress': self.get_progress(),
            'history_count': len(self.history),
            'session_start': self.session_start
        }
