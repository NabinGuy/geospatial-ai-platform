import chromadb
from typing import List, Dict, Any
from backend.config import Config

class VectorDBService:
    def __init__(self):
        self.client = chromadb.HttpClient(host=Config.CHROMA_HOST, port=Config.CHROMA_PORT)
        self.collection = self.client.get_or_create_collection(
            name="geospatial_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
        self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self):
        """Initialize the knowledge base with common geospatial operations"""
        knowledge_base = [
            {
                "id": "buffer_analysis",
                "operation": "buffer",
                "description": "Create buffer zones around geometric objects",
                "code": """
# Buffer analysis example
import geopandas as gpd
from shapely.geometry import Point

def create_buffer(gdf, distance, units='meters'):
    if gdf.crs and gdf.crs.to_string() != 'EPSG:4326':
        # Project to appropriate CRS for accurate distance calculation
        if units == 'meters':
            gdf_projected = gdf.to_crs('EPSG:3857')  # Web Mercator
        else:
            gdf_projected = gdf.copy()
    else:
        gdf_projected = gdf.copy()
    
    # Create buffer
    buffered = gdf_projected.copy()
    buffered['geometry'] = gdf_projected.geometry.buffer(distance)
    
    # Project back to original CRS
    if gdf.crs:
        buffered = buffered.to_crs(gdf.crs)
    
    return buffered

# Usage
result = create_buffer(input_gdf, buffer_distance)
""",
                "parameters": ["distance", "units"]
            },
            {
                "id": "spatial_join",
                "operation": "spatial_join",
                "description": "Join attributes from one layer to another based on spatial relationship",
                "code": """
# Spatial join example
import geopandas as gpd

def spatial_join_analysis(left_gdf, right_gdf, how='inner', predicate='intersects'):
    # Ensure both GeoDataFrames have the same CRS
    if left_gdf.crs != right_gdf.crs:
        right_gdf = right_gdf.to_crs(left_gdf.crs)
    
    # Perform spatial join
    joined = gpd.sjoin(left_gdf, right_gdf, how=how, predicate=predicate)
    
    return joined

# Usage
result = spatial_join_analysis(left_layer, right_layer, how='inner', predicate='intersects')
""",
                "parameters": ["how", "predicate"]
            },
            {
                "id": "distance_analysis",
                "operation": "distance",
                "description": "Calculate distances between geometric objects",
                "code": """
# Distance analysis example
import geopandas as gpd
import numpy as np

def calculate_distances(gdf, target_point=None, to_nearest=False):
    if gdf.crs and gdf.crs.to_string() != 'EPSG:4326':
        gdf_projected = gdf.to_crs('EPSG:3857')  # Web Mercator for meters
    else:
        gdf_projected = gdf.copy()
    
    if target_point:
        # Distance to specific point
        distances = gdf_projected.geometry.distance(target_point)
    elif to_nearest:
        # Distance to nearest feature
        distances = []
        for idx, geom in gdf_projected.iterrows():
            other_geoms = gdf_projected.drop(idx)
            min_dist = other_geoms.geometry.distance(geom.geometry).min()
            distances.append(min_dist)
    
    result = gdf.copy()
    result['distance'] = distances
    
    return result

# Usage
result = calculate_distances(input_gdf, target_point=target_geometry)
""",
                "parameters": ["target_point", "to_nearest"]
            }
        ]
        
        # Add to vector database
        for item in knowledge_base:
            try:
                self.collection.add(
                    ids=[item["id"]],
                    documents=[item["code"]],
                    metadatas=[{
                        "operation": item["operation"],
                        "description": item["description"],
                        "parameters": item["parameters"]
                    }]
                )
            except Exception as e:
                print(f"Failed to add {item['id']} to vector database: {e}")
    
    def search_similar_code(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Search for similar code examples"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "code": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
            
            return formatted_results
        except Exception as e:
            print(f"Vector search failed: {e}")
            return []
    
    def add_code_example(self, operation_id: str, code: str, metadata: Dict[str, Any]) -> bool:
        """Add a new code example to the knowledge base"""
        try:
            self.collection.add(
                ids=[operation_id],
                documents=[code],
                metadatas=[metadata]
            )
            return True
        except Exception as e:
            print(f"Failed to add code example: {e}")
            return False