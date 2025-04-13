"""
Background tasks for data collection and processing.
"""
from typing import List, Dict, Any, Optional
import time
import asyncio
import json
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from ..tasks.celery_app import celery_app
from ..utils.logger import get_logger
from ..db.session import get_db
from ..db import crud, models, schemas
from ..services.scraper import SERPScraper
from ..services.nitter import NitterScraper
from ..services.nlp_processor import NLPProcessor
from ..services.scorer import Scorer
from ..utils.query_utils import QueryBuilder
from ..utils.logger import app_logger as logger

# --- Helper Function for Person Processing ---

async def _process_person_details(person_name: str) -> Dict[str, Any]:
    """
    Processes a single person: Scrape -> NLP -> Score.
    Returns a dictionary with extracted and scored person data.
    Designed to be called internally by company processing or the founder task.
    """
    logger.info(f"Processing details for person: {person_name}")
    
    # Initialize services (can be optimized if called very frequently)
    serp_scraper = SERPScraper()
    nitter_scraper = NitterScraper()
    nlp_processor = NLPProcessor()
    scorer = Scorer()
    
    # 1. Scrape SERP
    # Need to decide if we always search with include_duke=True for people
    serp_results = serp_scraper.search_founder(person_name, include_duke=True)
    if not serp_results.get("organic_results"):
        logger.warning(f"No SERP results for person: {person_name}")
        # Return minimal data indicating lookup but failure
        return {"name": person_name, "error": "No SERP results"}
        
    # 2. NLP Pass 1 (to get potential handle)
    nlp_extracted_data = await nlp_processor.process_founder_data(serp_results)
    if nlp_extracted_data.get("error"):
        logger.error(f"NLP Step 1 failed for {person_name}: {nlp_extracted_data['error']}")
        return nlp_extracted_data # Return error state
        
    # 3. Scrape Nitter (if handle found)
    twitter_handle = nlp_extracted_data.get("twitter_handle")
    twitter_data = None
    if twitter_handle:
        twitter_data = nitter_scraper.get_recent_tweets(twitter_handle)
        if twitter_data.get("twitter_unavailable"):
            twitter_data = None
            
    # 4. NLP Pass 2 (if twitter data found)
    if twitter_data:
        nlp_extracted_data = await nlp_processor.process_founder_data(serp_results, twitter_data)
        if nlp_extracted_data.get("error"):
             logger.error(f"NLP Step 2 failed for {person_name}: {nlp_extracted_data['error']}")
             return nlp_extracted_data # Return error state
             
    # 5. Score Person Data
    scored_person_data = scorer.score_person_data(nlp_extracted_data)
    
    return scored_person_data

# --- Celery Tasks ---

@celery_app.task(name="process_company")
def process_company(company_name: str) -> Dict[str, Any]:
    """Task to process a company: Scrape -> NLP -> Process People -> Score -> Store."""
    return asyncio.run(_process_company_async(company_name))

async def _process_company_async(company_name: str) -> Dict[str, Any]:
    """
    Async implementation of company processing, including processing associated people.
    """
    logger.info(f"Starting full processing for company: {company_name}")
    start_time = time.time()

    serp_scraper = SERPScraper()
    nitter_scraper = NitterScraper()
    nlp_processor = NLPProcessor()
    scorer = Scorer()
    
    processed_people_results = [] # To store results of individual person processing
    final_company_data = {} # To store company data after scoring

    async with get_db() as db:
        try:
            # Step 1: Scrape Company SERP data
            logger.info(f"Scraping company SERP data for {company_name}")
            # No include_duke needed here, affiliation comes from people
            serp_results = serp_scraper.search_company(company_name, include_duke=False)
            if not serp_results.get("organic_results"):
                return {"status": "error", "message": "No SERP information found for company"}

            # Step 2: NLP for Company Basic Details + Identify People
            logger.info(f"Processing company SERP data with NLP for {company_name}")
            # Twitter data isn't processed here yet, maybe later based on handle
            company_nlp_data = await nlp_processor.process_company_data(serp_results)
            if company_nlp_data.get("error"):
                return {"status": "error", "message": f"NLP failed for company: {company_nlp_data['error']}"}

            # Step 3: Process Each Identified Person
            people_to_process = company_nlp_data.get("people", [])
            person_names_to_process = {p.get("name") for p in people_to_process if p.get("name")}
            
            logger.info(f"Identified {len(person_names_to_process)} unique people for {company_name}: {person_names_to_process}")
            
            person_processing_tasks = [
                _process_person_details(name) for name in person_names_to_process
            ]
            processed_people_results = await asyncio.gather(*person_processing_tasks)
            
            # Filter out people who failed processing
            successful_people = [p for p in processed_people_results if not p.get("error")]
            logger.info(f"Successfully processed details for {len(successful_people)} people.")

            # Step 4: Determine Final Company Affiliation Status & Score based on People
            company_affiliation_status = scorer.determine_company_affiliation_status(company_nlp_data, successful_people)
            company_affiliation_score = None
            if company_affiliation_status == "confirmed":
                company_affiliation_score = scorer.calculate_company_duke_affiliation_score(company_nlp_data, successful_people)
            
            # Step 5: Calculate Company Relevance Score
            company_relevance_score = scorer.calculate_company_relevance_score(
                company_nlp_data, 
                company_affiliation_status, 
                company_affiliation_score
            )
            
            # Step 6: Assemble Final Company Data for DB
            final_company_data = company_nlp_data.copy() # Start with NLP extracted data
            final_company_data["duke_affiliation_status"] = company_affiliation_status
            final_company_data["duke_affiliation_score"] = company_affiliation_score
            final_company_data["relevance_score"] = company_relevance_score
            
            # Map the *processed* people data to PersonBase for DB association
            # We need the title from the *company* NLP context, not the person's primary title
            people_for_db = []
            original_people_map = {p.get("name"): p.get("title") for p in people_to_process if p.get("name")} 
            
            for person_result in successful_people:
                 person_name = person_result.get("name")
                 company_title = original_people_map.get(person_name, "Unknown Role") # Get title assigned in company context
                 
                 # Create PersonBase using the scored person data
                 people_for_db.append(schemas.PersonBase(
                     name=person_name,
                     title=company_title, # Title specific to this company association
                     duke_affiliation_status=person_result.get("duke_affiliation_status", "no"),
                     duke_affiliation_score=person_result.get("duke_affiliation_score"), # Score from individual processing
                     relevance_score=person_result.get("relevance_score"), # Score from individual processing
                     education=person_result.get("education", []), # Details from individual processing
                     current_company=person_result.get("current_company"),
                     previous_companies=person_result.get("previous_companies", []),
                     twitter_handle=person_result.get("twitter_handle"),
                     linkedin_handle=person_result.get("linkedin_handle"),
                     source_links=person_result.get("source_links", [])
                 ))

            # Step 7: Create or Update Company in DB
            db_company = await crud.get_company_by_name(db, final_company_data["name"])

            # Choose Create or Update schema
            if db_company:
                company_payload = schemas.CompanyUpdate(
                    **{k: v for k, v in final_company_data.items() if k != 'people'}, # Exclude people temporarily
                    people=people_for_db # Add the processed people list
                )
                company = await crud.update_company(db, db_company.id, company_payload)
                logger.info(f"Updated company record: {company.name} (ID: {company.id})")
            else:
                company_payload = schemas.CompanyCreate(
                    **{k: v for k, v in final_company_data.items() if k != 'people'}, # Exclude people temporarily
                    people=people_for_db, # Add the processed people list
                    raw_data_path=serp_results.get("_file_path") # Add raw path on create
                )
                company = await crud.create_company(db, company_payload)
                logger.info(f"Created new company record: {company.name} (ID: {company.id})")

            process_time = time.time() - start_time
            logger.info(f"Completed full processing for company {final_company_data.get('name', company_name)} in {process_time:.2f} seconds")
            return {"status": "success", "company_id": company.id, "processing_time": process_time}

        except Exception as e:
            logger.error(f"Error processing company {company_name}: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}

@celery_app.task(name="process_founder")
def process_founder(founder_name: str) -> Dict[str, Any]:
    """Task to process an individual founder/person: Scrape -> NLP -> Score -> Store."""
    return asyncio.run(_process_founder_async(founder_name))

async def _process_founder_async(founder_name: str) -> Dict[str, Any]:
    """
    Async implementation of founder/person processing.
    """
    logger.info(f"Starting standalone processing for person: {founder_name}")
    start_time = time.time()

    # Process person details using the helper function
    scored_person_data = await _process_person_details(founder_name)

    if scored_person_data.get("error"):
        logger.error(f"Failed to process details for {founder_name}: {scored_person_data['error']}")
        return {"status": "error", "message": scored_person_data['error']}

    async with get_db() as db:
        try:
            # Store results (Create/Update Person)
            logger.info(f"Storing results for {founder_name}")
            db_person = await crud.get_person_by_name(db, scored_person_data["name"])

            if db_person:
                person_update = schemas.PersonUpdate(
                     **{k: v for k, v in scored_person_data.items() if k != 'title'} # Exclude title from update schema
                )
                person = await crud.update_person(db, db_person.id, person_update)
                logger.info(f"Updated person record: {person.name} (ID: {person.id})")
            else:
                # Ensure title is present for creation
                if not scored_person_data.get("title"):
                     logger.warning(f"Person {scored_person_data['name']} missing title for creation, using default.")
                     scored_person_data["title"] = "Unknown Role"
                     
                person_create = schemas.PersonCreate(**scored_person_data)
                person = await crud.create_person(db, person_create)
                logger.info(f"Created new person record: {person.name} (ID: {person.id})")

            process_time = time.time() - start_time
            logger.info(f"Completed standalone processing for person {scored_person_data.get('name', founder_name)} in {process_time:.2f} seconds")
            return {"status": "success", "person_id": person.id, "processing_time": process_time}

        except Exception as e:
            logger.error(f"Error storing person {founder_name}: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}

# --- Scheduled Tasks --- 

@celery_app.task(name="periodic_data_update")
def periodic_data_update():
    """Periodically trigger updates for existing companies and persons."""
    logger.info("Starting periodic data update task submission")
    async def _trigger_updates():
        async with get_db() as db:
            companies = await crud.get_companies(db, skip=0, limit=10000) # Configurable limit?
            persons = await crud.get_persons(db, skip=0, limit=10000) # Configurable limit?
            company_names = [c.name for c in companies]
            person_names = [p.name for p in persons]
        
        # Submit individual processing tasks with a delay
        for name in company_names:
            logger.debug(f"Submitting periodic update for company: {name}")
            process_company.apply_async(args=[name], countdown=5) # Add small delay
            await asyncio.sleep(0.5) # Short sleep between submissions
            
        for name in person_names:
            logger.debug(f"Submitting periodic update for person: {name}")
            process_founder.apply_async(args=[name], countdown=5) 
            await asyncio.sleep(0.5)
            
    asyncio.run(_trigger_updates())
    logger.info("Completed periodic data update task submission")

@celery_app.task(name="discover_new_startups")
def discover_new_startups(time_filter: str = "m6"):
    """
    Discover new startups using predefined queries and process them if new.
    Uses NLP for better entity extraction.
    """
    logger.info(f"Starting new startup discovery task (time_filter: {time_filter})")
    query_builder = QueryBuilder()
    serp_scraper = SERPScraper()
    nlp_processor = NLPProcessor()
    
    queries = query_builder.get_predefined_search_queries()
    
    async def _discover():
        processed_entities = set()
        async with get_db() as db:
            for query_info in queries:
                current_time_filter = query_info.get("time_filter", "m6")
                if time_filter != "all" and current_time_filter != time_filter:
                    continue # Skip if time filter doesn't match override
                
                logger.info(f"Running discovery query: {query_info['query']}")
                try:
                    serp_results = serp_scraper.search(query_info['query'], time_filter=current_time_filter)
                    if not serp_results.get("organic_results"):
                        continue
                        
                    # --- Use NLP to extract potential names --- 
                    # Create a combined text input from snippets for NLP
                    combined_snippets = "\n---\n".join([
                        f"Title: {r.get('title', '')}\nSnippet: {r.get('snippet', '')}"
                        for r in serp_results["organic_results"][:10] # Limit input context
                    ])
                    
                    # Simplified NLP prompt for entity extraction
                    extraction_prompt = f"""
                    Extract all potential company names and person names (likely founders or CEOs) mentioned 
                    in the following text snippets. Return ONLY a JSON object with two keys: 
                    "companies": ["<Company Name 1>", ...], "people": ["<Person Name 1>", ...]
                    
                    Text:
                    {combined_snippets}
                    """
                    
                    extraction_messages = [
                        {"role": "system", "content": "Extract company and person names into the specified JSON format."},
                        {"role": "user", "content": extraction_prompt}
                    ]
                    
                    extracted_names_json = await nlp_processor._process_with_llm(extraction_messages)
                    extracted_entities = json.loads(extracted_names_json)
                    potential_companies = extracted_entities.get("companies", [])
                    potential_people = extracted_entities.get("people", [])
                    logger.info(f"NLP extracted - Companies: {potential_companies}, People: {potential_people}")
                    # --- End NLP Extraction --- 
                    
                    # Process potential companies
                    for name in potential_companies:
                        if name in processed_entities: continue
                        exists = await crud.get_company_by_name(db, name)
                        if not exists:
                            logger.info(f"New potential company found: {name}. Submitting.")
                            process_company.delay(name)
                            processed_entities.add(name)
                            await asyncio.sleep(2)
                        else: processed_entities.add(name)
                            
                    # Process potential people
                    for name in potential_people:
                        if name in processed_entities: continue
                        exists = await crud.get_person_by_name(db, name)
                        if not exists:
                            logger.info(f"New potential person found: {name}. Submitting.")
                            process_founder.delay(name)
                            processed_entities.add(name)
                            await asyncio.sleep(2)
                        else: processed_entities.add(name)
                            
                except json.JSONDecodeError as json_err:
                     logger.error(f"Failed to parse NLP extraction for query '{query_info['query']}': {json_err}")
                except Exception as e:
                    logger.error(f"Error processing discovery query '{query_info['query']}': {e}", exc_info=True)
            
    asyncio.run(_discover())
    logger.info("Completed new startup discovery task") 