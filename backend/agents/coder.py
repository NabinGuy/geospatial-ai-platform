import openai
from typing import Dict, Any, List
from backend.config import Config
from backend.services.vector_db import VectorDBService

class CoderAgent:
    def __init__(self):
        openai.api_key = Config.OPENAI_API_KEY
        self.model = "gpt-4"
        self.vector_db = VectorDBService()
    
    def generate_code(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executable code from the plan"""
        
        # Retrieve relevant code examples from vector database
        relevant_examples = self.vector_db.search_similar_code(plan["analysis_type"])
        
        system_prompt = """You are an expert geospatial programmer. Generate Python code 
        using GeoPandas, Shapely, and other geospatial libraries to execute the given plan.
        
        Return your response as a JSON object with this structure:
        {
            "code": "import geopandas as gpd\\n# Your complete code here",
            "dependencies": ["geopandas", "shapely", "rasterio"],
            "input_requirements": ["vector_file_path", "buffer_distance"],
            "output_description": "GeoDataFrame with buffered geometries"
        }
        
        Make sure the code is production-ready with proper error handling."""
        
        user_prompt = f"""
        Plan to implement:
        {plan}
        
        Relevant examples from knowledge base:
        {relevant_examples}
        
        Generate complete, executable Python code.
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
            
            return self._parse_code_response(response.choices[0].message.content)
        except Exception as e:
            return {"error": f"Code generation failed: {str(e)}"}
    
    def _parse_code_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate the code response"""
        try:
            import json
            code_result = json.loads(response)
            
            # Validate code structure
            required_fields = ["code", "dependencies", "input_requirements"]
            if not all(field in code_result for field in required_fields):
                raise ValueError("Invalid code structure")
            
            # Additional validation can be added here
            return code_result
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response from coder"}
        except Exception as e:
            return {"error": f"Code parsing failed: {str(e)}"}