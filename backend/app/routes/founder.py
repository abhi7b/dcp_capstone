from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import json

from ..db.session import get_db
from ..db import crud, schemas
from ..services.scraper import SERPScraper
from ..services.nitter import NitterScraper
from ..services.nlp_processor import NLPProcessor
from ..services.scorer import Scorer
from ..utils.logger import api_logger

# Initialize router
router = APIRouter(prefix="/api/founder", tags=["founder"])

# Initialize services
serp_scraper = SERPScraper()
nitter_scraper = NitterScraper()
nlp_processor = NLPProcessor()
scorer = Scorer()

# Remove Founder routes
# @router.get("/", response_model=List[schemas.FounderResponse])
# async def get_founders(
#     skip: int = 0,
#     limit: int = 100,
#     duke_affiliation_status: Optional[str] = Query(
#         None, 
#         description="Filter by Duke affiliation status (confirmed, please review, no)"
#     ),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Get a list of founders with optional filtering
#     """
#     api_logger.info(f"Getting founders: skip={skip}, limit={limit}, duke_affiliation_status={duke_affiliation_status}")
#     founders = await crud.get_founders(db, skip=skip, limit=limit, duke_affiliation_status=duke_affiliation_status)
#     return founders

# @router.get("/{founder_id}", response_model=schemas.FounderResponse)
# async def get_founder_by_id(founder_id: int, db: AsyncSession = Depends(get_db)):
#     """
#     Get a founder by ID
#     """
#     api_logger.info(f"Getting founder by ID: {founder_id}")
#     founder = await crud.get_founder(db, founder_id)
#     if founder is None:
#         api_logger.warning(f"Founder not found: {founder_id}")
#         raise HTTPException(status_code=404, detail="Founder not found")
#     return founder

# @router.get("/search/", response_model=schemas.FounderResponse)
# async def search_founder(
#     name: str = Query(..., description="Founder name to search for"),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Search for a founder by name, scraping if not found in database
#     """
#     api_logger.info(f"Searching for founder: {name}")
#     
#     # Check if founder exists in database by name
#     founder = await crud.get_founder_by_name(db, name)
#     if founder:
#         api_logger.info(f"Founder found in database by name: {name}")
#         return founder
#     
#     # Founder not found by name, proceed with scraping
#     api_logger.info(f"Founder not found in database by name, scraping: {name}")
#     
#     try:
#         # Query SERP API for founder details
#         serp_results = serp_scraper.search_founder(name)
#         
#         # Check if we got any results
#         if not serp_results.get("organic_results"):
#             api_logger.warning(f"No search results found for founder: {name}")
#             raise HTTPException(status_code=404, detail="No information found for this founder")
#         
#         # Search for Duke affiliation
#         duke_results = serp_scraper.search_founder(name, include_duke=True)
#         
#         # Combine results
#         all_results = {
#             "organic_results": serp_results.get("organic_results", []) + duke_results.get("organic_results", []),
#             "_file_path": serp_results.get("_file_path")
#         }
#         
#         # Extract Twitter handle from NLP results first
#         founder_data = await nlp_processor.process_founder_data(all_results)
#         
#         # If Twitter handle is available, check if founder with same handle exists
#         twitter_data = None
#         if founder_data.get("twitter_handle"):
#             handle = founder_data["twitter_handle"]
#             
#             # Check if a founder with this Twitter handle already exists
#             existing_founder = await crud.get_founder_by_twitter_handle(db, handle)
#             if existing_founder:
#                 api_logger.info(f"Founder found in database by Twitter handle: {handle}")
#                 return existing_founder
#                 
#             api_logger.info(f"Scraping Twitter for founder: {name}, handle: {handle}")
#             twitter_data = nitter_scraper.get_recent_tweets(handle)
#             
#             # Re-process with Twitter data if available
#             if not twitter_data.get("twitter_unavailable", False):
#                 founder_data = await nlp_processor.process_founder_data(all_results, twitter_data)
#         
#         # Score the founder
#         founder_data = scorer.score_founder(founder_data)
#         
#         # Create structured founder object for database
#         founder_create = schemas.FounderCreate(
#             name=founder_data["name"],
#             duke_affiliation_status=founder_data["duke_affiliation_status"],
#             duke_affiliation_score=founder_data["duke_affiliation_score"],
#             relevance_score=founder_data["relevance_score"],
#             education=[schemas.EducationBase(
#                 school=edu["school"],
#                 degree=edu.get("degree"),
#                 years=edu.get("years")
#             ) for edu in founder_data.get("education", [])],
#             current_company=schemas.CurrentCompanyBase(
#                 name=founder_data.get("current_company", {}).get("name"),
#                 role=founder_data.get("current_company", {}).get("role"),
#                 funding_stage=founder_data.get("current_company", {}).get("funding_stage")
#             ) if founder_data.get("current_company") else None,
#             previous_companies=founder_data.get("previous_companies"),
#             twitter_handle=founder_data.get("twitter_handle"),
#             linkedin_handle=founder_data.get("linkedin_handle"),
#             twitter_summary=schemas.TwitterSummaryBase(
#                 tweets_analyzed=founder_data.get("twitter_summary", {}).get("tweets_analyzed"),
#                 mentions_funding=founder_data.get("twitter_summary", {}).get("mentions_funding"),
#                 engagement_score=founder_data.get("twitter_summary", {}).get("engagement_score"),
#                 status=founder_data.get("twitter_summary", {}).get("status", "unavailable")
#             ) if founder_data.get("twitter_summary") else None,
#             source_links=founder_data.get("source_links"),
#             raw_data_path=serp_results.get("_file_path")
#         )
#         
#         # Save to database
#         db_founder = await crud.create_founder(db, founder_create)
#         api_logger.info(f"Founder saved to database: {db_founder.name} (ID: {db_founder.id})")
#         
#         return db_founder
#         
#     except Exception as e:
#         api_logger.error(f"Error searching for founder {name}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Error processing founder information: {str(e)}")

# @router.put("/{founder_id}", response_model=schemas.FounderResponse)
# async def update_founder(
#     founder_id: int,
#     founder_update: schemas.FounderUpdate,
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Update a founder by ID
#     """
#     api_logger.info(f"Updating founder: {founder_id}")
#     founder = await crud.update_founder(db, founder_id, founder_update)
#     if founder is None:
#         api_logger.warning(f"Founder not found for update: {founder_id}")
#         raise HTTPException(status_code=404, detail="Founder not found")
#     
#     return founder

# @router.delete("/{founder_id}", response_model=schemas.ErrorResponse)
# async def delete_founder(founder_id: int, db: AsyncSession = Depends(get_db)):
#     """
#     Delete a founder by ID
#     """
#     api_logger.info(f"Deleting founder: {founder_id}")
#     deleted = await crud.delete_founder(db, founder_id)
#     if not deleted:
#         api_logger.warning(f"Founder not found for deletion: {founder_id}")
#         raise HTTPException(status_code=404, detail="Founder not found")
#     
#     return JSONResponse(
#         status_code=status.HTTP_200_OK,
#         content={"detail": f"Founder {founder_id} deleted successfully"}
#     ) 