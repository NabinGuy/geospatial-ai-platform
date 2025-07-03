import subprocess
import tempfile
import os
import json
import sys
from typing import Dict, Any, List
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString, Polygon
import json

class ExecutionEngine:
    def __init__(self):
        self.allowed_imports = {
            'geopandas', 'pandas', 'shapely', 'rasterio', 'numpy',
            'matplotlib', 'seaborn', 'json', 'os', 'tempfile'
        }
    
    def execute_code(self, code: str, input_data: Dict[str, Any], dependencies: List[str]) -> Dict[str, Any]:
        """Execute geospatial processing code in a controlled environment"""
        
        # Validate imports
        if not self._validate_imports(code):
            return {"success": False, "error": "Unauthorized imports detected"}
        
        # Create execution environment
        exec_globals = self._create_execution_environment()
        exec_locals = {"input_data": input_data}
        
        try:
            # Execute the code
            exec(code, exec_globals, exec_locals)
            
            # Extract result
            result = exec_locals.get('result')
            if result is None:
                return {"success": False, "error": "Code did not produce a 'result' variable"}
            
            # Serialize result for JSON transport
            serialized_result = self._serialize_result(result)
            
            return {
                "success": True,
                "result": serialized_result,
                "execution_info": {
                    "variables": list(exec_locals.keys()),
                    "result_type": type(result).__name__
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Execution failed: {str(e)}"}
    
    def _validate_imports(self, code: str) -> bool:
        """Validate that code only uses allowed imports"""
        import ast
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split('.')[0] not in self.allowed_imports:
                            return False
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] not in self.allowed_imports:
                        return False
            return True
        except Exception:
            return False
    
    def _create_execution_environment(self) -> Dict[str, Any]:
        """Create a controlled execution environment"""
        import geopandas as gpd
        import pandas as pd
        import numpy as np
        from shapely.geometry import Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon
        from shapely.ops import unary_union, transform
        import json
        import tempfile
        import os
        
        return {
            # Geospatial libraries
            'gpd': gpd,
            'geopandas': gpd,
            'pd': pd,
            'pandas': pd,
            'np': np,
            'numpy': np,
            
            # Shapely
            'Point': Point,
            'LineString': LineString,
            'Polygon': Polygon,
            'MultiPoint': MultiPoint,
            'MultiLineString': MultiLineString,
            'MultiPolygon': MultiPolygon,
            'unary_union': unary_union,
            'transform': transform,
            
            # Utilities
            'json': json,
            'tempfile': tempfile,
            'os': os,
            
            # Built-ins
            'print': print,
            'len': len,
            'list': list,
            'dict': dict,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'range': range,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'sorted': sorted,
            'max': max,
            'min': min,
            'sum': sum,
            'abs': abs,
            'round': round,
        }
    
    def _serialize_result(self, result: Any) -> Any:
        """Serialize geospatial results for JSON transport"""
        if isinstance(result, gpd.GeoDataFrame):
            return {
                "type": "GeoDataFrame",
                "data": result.to_json(),
                "crs": str(result.crs) if result.crs else None,
                "shape": result.shape,
                "columns": list(result.columns)
            }
        elif isinstance(result, pd.DataFrame):
            return {
                "type": "DataFrame",
                "data": result.to_json(),
                "shape": result.shape,
                "columns": list(result.columns)
            }
        elif hasattr(result, '__geo_interface__'):
            return {
                "type": "Geometry",
                "data": result.__geo_interface__
            }
        elif isinstance(result, dict):
            return result
        elif isinstance(result, (list, tuple)):
            return list(result)
        elif isinstance(result, (int, float, str, bool)):
            return result
        else:
            return str(result)