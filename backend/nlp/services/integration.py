"""
Integration service for the DCP AI Scouting Platform.

This module provides functionality to integrate data from multiple sources (SERP, Twitter),
apply consistent scoring, and produce a unified output ready for database insertion.
"""
import logging
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from backend.config.logs import LogManager
from backend.nlp.services.scoring import ScoringService
from backend.nlp.services.social_media import SocialMediaService

# Initialize logger
LogManager.setup_logging()
logger = logging.getLogger(__name__)

class IntegrationService:
    """
    Service for integrating data from multiple sources and producing unified outputs.
    
    This class combines data from scrapers and processors, applies consistent scoring,
    and generates output ready for database insertion.
    """
    
    @staticmethod
    async def process_company_data(
        company_name: str,
        serp_data: Dict[str, Any],
        twitter_data: Optional[Dict[str, Any]] = None,
        company_processor_result: Optional[Dict[str, Any]] = None,
        twitter_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process company data from multiple sources and produce a unified output.
        
        Args:
            company_name: Name of the company
            serp_data: Data from SERP scraper
            twitter_data: Data from Twitter scraper (optional)
            company_processor_result: Result from company processor (optional)
            twitter_analysis: Result from Twitter analyzer (optional)
            
        Returns:
            Dict[str, Any]: Unified output ready for database insertion
        """
        try:
            logger.info(f"Integrating data for company: {company_name}")
            
            # Start with the company processor result as the base
            output = company_processor_result.copy() if company_processor_result else {}
            
            # Ensure consistent naming
            if not output.get("name") and company_name:
                output["name"] = company_name
                
            # Ensure website field exists (use domain if website is missing)
            if not output.get("website") and output.get("domain"):
                output["website"] = f"https://{output['domain']}"
                
            # Ensure consistent year_founded field
            if not output.get("year_founded") and output.get("founded_year"):
                output["year_founded"] = output["founded_year"]
            elif not output.get("founded_year") and output.get("year_founded"):
                output["founded_year"] = output["year_founded"]
                
            # Add metadata
            output.update({
                "processed_at": datetime.utcnow().isoformat(),
                "source_data": {
                    "serp": serp_data is not None,
                    "twitter": twitter_data is not None
                },
                "processed_data": {
                    "company": company_processor_result is not None,
                    "twitter": twitter_analysis is not None
                }
            })
            
            # Add Twitter data if available
            if twitter_analysis:
                # Store the full Twitter analysis
                output["twitter_analysis"] = twitter_analysis
                
                # Extract key Twitter fields for easier access
                twitter_handle = ""
                if twitter_data and twitter_data.get("username"):
                    twitter_handle = twitter_data.get("username")
                elif output.get("twitter_handle"):
                    twitter_handle = output.get("twitter_handle")
                    
                output["twitter"] = {
                    "handle": twitter_handle,
                    "last_updated": datetime.utcnow().isoformat(),
                    "followers_count": twitter_data.get("profile", {}).get("followers_count", 0) if twitter_data else 0,
                    "following_count": twitter_data.get("profile", {}).get("friends_count", 0) if twitter_data else 0,
                    "verified": twitter_data.get("profile", {}).get("verified", False) if twitter_data else False,
                    "summary": twitter_analysis.get("summary", ""),
                    "actionability_score": twitter_analysis.get("actionability_score", 0),
                    "topics": twitter_analysis.get("topics", []),
                    "key_insights": twitter_analysis.get("key_insights", [])
                }
                
                # Update twitter_handle in the main output for consistency
                if twitter_handle and not output.get("twitter_handle"):
                    output["twitter_handle"] = twitter_handle
            
            # Prepare data for scoring
            scoring_data = {
                "duke_affiliated": output.get("duke_affiliated", False),
                "duke_connection": output.get("duke_connection", {}),
                "funding_stage": output.get("latest_funding_stage", ""),
                "founded_year": output.get("year_founded"),
                "industry": output.get("industry", "")
            }
            
            # Add Twitter data to scoring if available
            if "twitter" in output:
                scoring_data.update({
                    "twitter_actionability": output["twitter"].get("actionability_score", 0),
                    "twitter_topics": output["twitter"].get("topics", []),
                    "twitter_key_insights": output["twitter"].get("key_insights", [])
                })
            
            # Calculate scores
            duke_score = ScoringService.calculate_duke_affiliation_score(scoring_data)
            startup_score = ScoringService.calculate_startup_potential_score(scoring_data)
            content_score = ScoringService.calculate_content_relevance_score(scoring_data)
            overall_score = ScoringService.calculate_relevance_score(scoring_data)
            
            # Add scores to output
            output["scores"] = {
                "duke_affiliation": round(duke_score * 100, 2),
                "startup_potential": round(startup_score * 100, 2),
                "content_relevance": round(content_score * 100, 2),
                "overall": round(overall_score, 2)
            }
            
            # Add database-ready fields for convenience
            output["db_ready"] = IntegrationService._prepare_db_fields(output)
            
            logger.info(f"Successfully integrated data for company: {company_name} with overall score: {output['scores']['overall']}")
            return output
            
        except Exception as e:
            logger.error(f"Error integrating company data: {e}", exc_info=True)
            return {
                "name": company_name,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    async def process_founder_data(
        founder_name: str,
        serp_data: Dict[str, Any],
        twitter_data: Optional[Dict[str, Any]] = None,
        founder_processor_result: Optional[Dict[str, Any]] = None,
        twitter_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process founder data from multiple sources and produce a unified output.
        
        Args:
            founder_name: Name of the founder
            serp_data: Data from SERP scraper
            twitter_data: Data from Twitter scraper (optional)
            founder_processor_result: Result from founder processor (optional)
            twitter_analysis: Result from Twitter analyzer (optional)
            
        Returns:
            Dict[str, Any]: Unified output ready for database insertion
        """
        try:
            logger.info(f"Integrating data for founder: {founder_name}")
            
            # Start with the founder processor result as the base
            output = founder_processor_result.copy() if founder_processor_result else {}
            
            # Ensure consistent naming
            if not output.get("full_name") and founder_name:
                output["full_name"] = founder_name
                
            # Add metadata
            output.update({
                "processed_at": datetime.utcnow().isoformat(),
                "source_data": {
                    "serp": serp_data is not None,
                    "twitter": twitter_data is not None
                },
                "processed_data": {
                    "founder": founder_processor_result is not None,
                    "twitter": twitter_analysis is not None
                }
            })
            
            # Add Twitter data if available
            if twitter_analysis:
                # Store the full Twitter analysis
                output["twitter_analysis"] = twitter_analysis
                
                # Extract key Twitter fields for easier access
                twitter_handle = ""
                if twitter_data and twitter_data.get("username"):
                    twitter_handle = twitter_data.get("username")
                elif output.get("twitter_handle"):
                    twitter_handle = output.get("twitter_handle")
                    
                output["twitter"] = {
                    "handle": twitter_handle,
                    "last_updated": datetime.utcnow().isoformat(),
                    "followers_count": twitter_data.get("profile", {}).get("followers_count", 0) if twitter_data else 0,
                    "following_count": twitter_data.get("profile", {}).get("friends_count", 0) if twitter_data else 0,
                    "verified": twitter_data.get("profile", {}).get("verified", False) if twitter_data else False,
                    "summary": twitter_analysis.get("summary", ""),
                    "actionability_score": twitter_analysis.get("actionability_score", 0),
                    "topics": twitter_analysis.get("topics", []),
                    "key_insights": twitter_analysis.get("key_insights", [])
                }
                
                # Update twitter_handle in the main output for consistency
                if twitter_handle and not output.get("twitter_handle"):
                    output["twitter_handle"] = twitter_handle
            
            # Prepare data for scoring
            scoring_data = {
                "duke_affiliated": output.get("duke_affiliated", False),
                "duke_connection": output.get("duke_connection", {}),
                "current_role": output.get("current_role", ""),
                "education": output.get("education", []),
                "experience": output.get("experience", [])
            }
            
            # Add Twitter data to scoring if available
            if "twitter" in output:
                scoring_data.update({
                    "twitter_actionability": output["twitter"].get("actionability_score", 0),
                    "twitter_topics": output["twitter"].get("topics", []),
                    "twitter_key_insights": output["twitter"].get("key_insights", [])
                })
            
            # Calculate scores
            duke_score = ScoringService.calculate_duke_affiliation_score(scoring_data)
            startup_score = ScoringService.calculate_startup_potential_score(scoring_data)
            content_score = ScoringService.calculate_content_relevance_score(scoring_data)
            overall_score = ScoringService.calculate_relevance_score(scoring_data)
            
            # Add scores to output
            output["scores"] = {
                "duke_affiliation": round(duke_score * 100, 2),
                "startup_potential": round(startup_score * 100, 2),
                "content_relevance": round(content_score * 100, 2),
                "overall": round(overall_score, 2)
            }
            
            # Add database-ready fields for convenience
            output["db_ready"] = IntegrationService._prepare_db_fields(output, is_founder=True)
            
            logger.info(f"Successfully integrated data for founder: {founder_name} with overall score: {output['scores']['overall']}")
            return output
            
        except Exception as e:
            logger.error(f"Error integrating founder data: {e}", exc_info=True)
            return {
                "full_name": founder_name,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def _prepare_db_fields(output: Dict[str, Any], is_founder: bool = False) -> Dict[str, Any]:
        """
        Prepare fields ready for database insertion.
        
        Args:
            output: Integrated output data
            is_founder: Whether this is founder data (vs company)
            
        Returns:
            Dict[str, Any]: Database-ready fields
        """
        db_fields = {}
        
        # Common fields
        if is_founder:
            db_fields["full_name"] = output.get("full_name", "")
            # Use current_position instead of current_role to match the model
            db_fields["current_position"] = output.get("current_position", "") or output.get("current_role", "")
            db_fields["current_company"] = output.get("current_company", "")
            db_fields["linkedin_url"] = output.get("linkedin_url", "")
            db_fields["graduation_year"] = output.get("graduation_year")
            
            # Add education and work_history fields that exist in the model
            if "education" in output:
                db_fields["education"] = output["education"]
            if "work_history" in output:
                db_fields["work_history"] = output["work_history"]
        else:
            # Company fields
            db_fields["name"] = output.get("name", "")
            db_fields["description"] = output.get("description", "")
            db_fields["website"] = output.get("website", "")
            db_fields["domain"] = output.get("domain", "")
            db_fields["industry"] = output.get("industry", "")
            db_fields["location"] = output.get("location", "")
            
            # Ensure consistent year_founded field
            db_fields["year_founded"] = output.get("year_founded") or output.get("founded_year")
            
            # Use latest_funding_stage to match the model (not funding_stage)
            db_fields["latest_funding_stage"] = output.get("latest_funding_stage", "") or output.get("funding_stage", "")
            
            # LinkedIn URL
            db_fields["linkedin_url"] = output.get("linkedin_url", "")
            
            # Additional company fields
            db_fields["total_funding"] = output.get("total_funding")
            db_fields["latest_valuation"] = output.get("latest_valuation")
            db_fields["competitors"] = output.get("competitors", [])
            
            # Include funding rounds if available
            if "funding_rounds" in output:
                db_fields["funding_rounds"] = output["funding_rounds"]
                
            # Include founders if available
            if "founders" in output:
                db_fields["founders"] = output["founders"]
        
        # Duke affiliation
        db_fields["duke_affiliated"] = output.get("duke_affiliated", False)
        db_fields["duke_connection_type"] = output.get("duke_connection_type", [])
        db_fields["duke_department"] = output.get("duke_department")
        db_fields["duke_affiliation_confidence"] = output.get("duke_affiliation_confidence", 0)
        db_fields["duke_affiliation_sources"] = output.get("duke_affiliation_sources", [])
        
        # Twitter data
        if "twitter" in output:
            twitter = output["twitter"]
            db_fields["twitter_handle"] = twitter.get("handle", "") or output.get("twitter_handle", "")
            db_fields["twitter_summary"] = twitter.get("summary", "")
            db_fields["twitter_actionability"] = twitter.get("actionability_score", 0)
            db_fields["twitter_last_updated"] = twitter.get("last_updated")
            db_fields["social_media_score"] = twitter.get("followers_count", 0) or output.get("social_media_score", 0)
            
        # Data quality metrics
        db_fields["data_freshness_score"] = output.get("data_freshness_score", 0)
        db_fields["data_quality_score"] = output.get("data_quality_score", 0)
        db_fields["data_sources"] = output.get("data_sources", [])
        
        # Timestamps
        db_fields["last_updated"] = output.get("last_updated") or datetime.utcnow().isoformat()
        db_fields["created_at"] = output.get("created_at") or datetime.utcnow().isoformat()
        
        # Scores
        if "scores" in output:
            scores = output["scores"]
            db_fields["duke_affiliation_score"] = scores.get("duke_affiliation", 0)
            db_fields["startup_potential_score"] = scores.get("startup_potential", 0)
            db_fields["content_relevance_score"] = scores.get("content_relevance", 0)
            db_fields["overall_score"] = scores.get("overall", 0)
        
        return db_fields
    
    @staticmethod
    def save_output_to_json(output: Dict[str, Any], filename: str) -> str:
        """
        Save the integrated output to a JSON file.
        
        Args:
            output: Integrated output data
            filename: Base filename (without extension)
            
        Returns:
            str: Path to the saved file
        """
        try:
            # Add timestamp to filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"output/{filename}_{timestamp}.json"
            
            # Ensure output directory exists
            import os
            os.makedirs("output", exist_ok=True)
            
            # Save to file
            with open(filepath, "w") as f:
                json.dump(output, f, indent=2)
            
            logger.info(f"Saved integrated output to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving output to JSON: {e}", exc_info=True)
            return "" 