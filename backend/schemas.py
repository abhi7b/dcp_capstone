##### schemas.py #####
"""
Defines Pydantic models (schemas) for FastAPI responses.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class CompanySearchResponse(BaseModel):
    name: str
    domain: Optional[str] = None
    duke_affiliation: bool = False
    founders: List[str] = []

    model_config = ConfigDict(from_attributes=True)

class FounderSearchResponse(BaseModel):
    name: str
    duke_affiliation: bool = False
    companies: List[str] = []

    model_config = ConfigDict(from_attributes=True)
