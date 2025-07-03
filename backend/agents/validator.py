import tempfile
import subprocess
import json
from typing import Dict, Any, Optional
from backend.services.execution_engine import ExecutionEngine

class ValidatorAgent:
    def __init__(self):
        self.execution_engine = ExecutionEngine()
    
    def validate_and_execute(self, code_result: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and execute the generated code"""
        
        # Step 1: Static code validation
        static_validation = self._validate_code_syntax(code_result["code"])
        if not static_validation["valid"]:
            return {
                "success": False,
                "error": f"Code validation failed: {static_validation['error']}",
                "stage": "static_validation"
            }
        
        # Step 2: Execute the code
        try:
            execution_result = self.execution_engine.execute_code(
                code_result["code"],
                input_data,
                code_result.get("dependencies", [])
            )
            
            if execution_result["success"]:
                # Step 3: Validate output
                output_validation = self._validate_output(execution_result["result"])
                if output_validation["valid"]:
                    return {
                        "success": True,
                        "result": execution_result["result"],
                        "validation_report": output_validation["report"]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Output validation failed: {output_validation['error']}",
                        "stage": "output_validation"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Execution failed: {execution_result['error']}",
                    "stage": "execution"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Validation process failed: {str(e)}",
                "stage": "general"
            }
    
    def _validate_code_syntax(self, code: str) -> Dict[str, Any]:
        """Validate Python code syntax"""
        try:
            compile(code, '<string>', 'exec')
            return {"valid": True}
        except SyntaxError as e:
            return {"valid": False, "error": f"Syntax error: {str(e)}"}
        except Exception as e:
            return {"valid": False, "error": f"Compilation error: {str(e)}"}
    
    def _validate_output(self, result: Any) -> Dict[str, Any]:
        """Validate the execution output"""
        try:
            # Check if result is a valid geospatial object
            if hasattr(result, 'geometry') and hasattr(result, 'crs'):
                # It's likely a GeoDataFrame
                return {
                    "valid": True,
                    "report": {
                        "type": "GeoDataFrame",
                        "shape": result.shape,
                        "crs": str(result.crs),
                        "columns": list(result.columns)
                    }
                }
            elif isinstance(result, dict) and "features" in result:
                # It's likely GeoJSON
                return {
                    "valid": True,
                    "report": {
                        "type": "GeoJSON",
                        "feature_count": len(result["features"])
                    }
                }
            else:
                return {
                    "valid": True,
                    "report": {"type": type(result).__name__}
                }
        except Exception as e:
            return {"valid": False, "error": f"Output validation error: {str(e)}"}