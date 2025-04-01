from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ..db.session import get_db
from ..db import crud, schemas
from ..services.scraper import SERPScraper
from ..services.nlp_processor import NLPProcessor
from ..utils.logger import api_logger
from ..routes.auth import verify_api_key

# Initialize router
router = APIRouter(prefix="/api/company", tags=["company"])

# Initialize services
serp_scraper = SERPScraper()
nlp_processor = NLPProcessor()

@router.get("/search/", response_model=schemas.CompanyResponse)
async def search_company(
    name: str = Query(..., description="Company name to search for"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for a company by name, scraping if not found in database.
    This endpoint handles both retrieval and creation of company data.
    """
    api_logger.info(f"Searching for company: {name}")
    
    # Check if company exists in database by name
    company = await crud.get_company_by_name(db, name)
    if company:
        api_logger.info(f"Company found in database by name: {name}")
        return company
    
    # Company not found by name, proceed with scraping
    api_logger.info(f"Company not found in database by name, scraping: {name}")
    
    try:
        # Query SERP API for company details
        company_serp = serp_scraper.search_company(name)
        
        # Check if we got any results
        if not company_serp.get("organic_results"):
            api_logger.warning(f"No search results found for company: {name}")
            raise HTTPException(status_code=404, detail="No information found for this company")
        
        # Get Duke affiliation search results for each person
        person_duke_searches = {}
        company_data = await nlp_processor.process_company_step1(company_serp)
        
        if "error" in company_data:
            raise HTTPException(status_code=404, detail=company_data["error"])
        
        # Search for Duke affiliation for each person
        for person in company_data.get("people", []):
            person_name = person["name"]
            duke_search = serp_scraper.search_person_duke_affiliation(person_name)
            person_duke_searches[person_name] = duke_search
        
        # Process the complete company pipeline
        company_data = await nlp_processor.process_company_pipeline(
            company_serp,
            person_duke_searches
        )
        
        # Create structured company object for database
        company_create = schemas.CompanyCreate(
            name=company_data["name"],
            duke_affiliation_status=company_data["duke_affiliation_status"],
            relevance_score=int(company_data.get("relevance_score", 0)),
            summary=company_data.get("summary"),
            investors=company_data.get("investors", []),
            funding_stage=company_data.get("funding_stage"),
            industry=company_data.get("industry"),
            founded=company_data.get("founded"),
            location=company_data.get("location"),
            twitter_handle=company_data.get("twitter_handle"),
            linkedin_handle=company_data.get("linkedin_handle"),
            twitter_summary=company_data.get("twitter_summary", {}),
            source_links=company_data.get("source_links", [])
        )
        
        # Save to database
        db_company = await crud.create_company(db, company_create)
        
        # Create person records and associations
        for person_type, people in company_data.get("people", {}).items():
            for person_data in people:
                # Create or get person
                person_create = schemas.PersonCreate(
                    name=person_data["name"],
                    duke_affiliation_status=person_data["duke_affiliation_status"],
                    relevance_score=int(person_data.get("relevance_score", 0)),
                    education=person_data.get("education", []),
                    current_company=company_data["name"],
                    previous_companies=person_data.get("previous_companies", []),
                    twitter_handle=person_data.get("twitter_handle"),
                    linkedin_handle=person_data.get("linkedin_handle"),
                    twitter_summary=str(person_data.get("twitter_summary", "")),
                    source_links=person_data.get("source_links", [])
                )
                
                # Create person and association
                await crud.create_person_with_company(
                    db=db,
                    person=person_create,
                    company_id=db_company.id,
                    title=person_data["title"]
                )
        
        api_logger.info(f"Company saved to database: {db_company.name} (ID: {db_company.id})")
        return db_company
        
    except Exception as e:
        api_logger.error(f"Error searching for company {name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing company information: {str(e)}")

@router.delete("/{company_id}", response_model=schemas.Message)
async def delete_company(company_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a company by ID.
    This is useful for removing incorrect entries or obsolete data.
    """
    api_logger.info(f"Deleting company: {company_id}")
    deleted = await crud.delete_company(db, company_id)
    if not deleted:
        api_logger.warning(f"Company not found for deletion: {company_id}")
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {"message": f"Company {company_id} deleted successfully"} 