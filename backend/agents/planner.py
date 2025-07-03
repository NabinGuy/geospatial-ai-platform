import openai
from typing import List, Dict, Any
from backend.config import Config

class PlannerAgent:
    def __init__(self):
        openai.api_key = Config.OPENAI_API_KEY
        self.model = "gpt-4"
    
    def create_plan(self, user_query: str, available_data: List[Dict]) -> Dict[str, Any]:
        """Creates a step-by-step plan for geospatial analysis"""
        
        system_prompt = """You are an expert geospatial analyst. Create a detailed step-by-step plan 
        for the user's geospatial analysis request. Consider available data and appropriate methods.
        
        Return your response as a JSON object with this structure:
        {
            "analysis_type": "buffer_analysis|spatial_join|overlay|distance_analysis|etc",
            "steps": [
                {
                    "step_number": 1,
                    "description": "Load and validate input data",
                    "operation": "load_data",
                    "parameters": {"file_path": "path/to/file", "data_type": "vector"}
                },
                {
                    "step_number": 2,
                    "description": "Perform buffer analysis",
                    "operation": "buffer",
                    "parameters": {"distance": 1000, "units": "meters"}
                }
            ],
            "expected_output": "Description of final output",
            "confidence": 0.95
        }"""
        
        user_prompt = f"""
        User Query: {user_query}
        
        Available Data:
        {self._format_available_data(available_data)}
        
        Create a detailed execution plan.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            
            return self._parse_plan_response(response.choices[0].message.content)
        except Exception as e:
            return {"error": f"Planning failed: {str(e)}"}
    
    def _format_available_data(self, data_list: List[Dict]) -> str:
        """Format available data for the prompt"""
        formatted = []
        for item in data_list:
            formatted.append(f"- {item['name']}: {item['data_type']} ({item.get('description', 'No description')})")
        return "\n".join(formatted)
    
    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate the plan response"""
        try:
            import json
            plan = json.loads(response)
            
            # Validate plan structure
            required_fields = ["analysis_type", "steps", "expected_output"]
            if not all(field in plan for field in required_fields):
                raise ValueError("Invalid plan structure")
            
            return plan
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response from planner"}
        except Exception as e:
            return {"error": f"Plan parsing failed: {str(e)}"}