"""
Scoring service for the DCP AI Scouting Platform.

This module provides functionality to calculate various scores for entities,
including data quality, Duke affiliation confidence, and social media impact.
"""
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta

from backend.config.logs import LogManager

# Initialize logger
LogManager.setup_logging()
logger = logging.getLogger(__name__)

class ScoringService:
    """
    Service for scoring and evaluating investment opportunities.
    
    This class implements the scoring algorithms outlined in the project scope,
    focusing on Duke affiliation strength, startup potential, and content relevance.
    """
    
    @staticmethod
    def calculate_relevance_score(data: Dict[str, Any]) -> float:
        """
        Calculate the overall relevance score based on the formula from the project scope:
        Score = (0.4 * Duke Affiliation Score) + (0.4 * Startup Potential Score) + (0.2 * Content Relevance Score)
        
        Args:
            data: Data dictionary containing all relevant information
            
        Returns:
            float: Overall relevance score (0-100)
        """
        try:
            # Calculate component scores
            duke_score = ScoringService.calculate_duke_affiliation_score(data)
            startup_score = ScoringService.calculate_startup_potential_score(data)
            content_score = ScoringService.calculate_content_relevance_score(data)
            
            # Apply weights according to the formula
            # 40% weight for Duke affiliation - prioritizes Duke connections
            # 40% weight for startup potential - emphasizes investment viability
            # 20% weight for content relevance - considers data quality and recency
            weighted_score = (0.4 * duke_score) + (0.4 * startup_score) + (0.2 * content_score)
            
            # Normalize to 0-100 scale
            normalized_score = min(max(weighted_score * 100, 0), 100)
            
            logger.debug(f"Calculated relevance score: {normalized_score:.2f} (Duke: {duke_score:.2f}, Startup: {startup_score:.2f}, Content: {content_score:.2f})")
            
            return normalized_score
            
        except Exception as e:
            logger.error(f"Error calculating relevance score: {e}", exc_info=True)
            return 0.0
    
    @staticmethod
    def calculate_duke_affiliation_score(data: Dict[str, Any]) -> float:
        """
        Calculate Duke affiliation strength score (0-1).
        
        Factors:
        1. Graduation year (recent graduates weighted higher)
        2. Degree program (business, engineering weighted higher for startups)
        3. Current role (founder, CEO weighted higher)
        
        Args:
            data: Data dictionary containing Duke affiliation information
            
        Returns:
            float: Duke affiliation score (0-1)
        """
        try:
            score = 0.0
            
            # Check if Duke affiliated - if not, return 0
            if not data.get("duke_affiliated", False):
                return 0.0
                
            # Get Duke connection information
            duke_connection = data.get("duke_connection", {})
            if isinstance(duke_connection, dict):
                # Get confidence score if available (30% weight)
                confidence = duke_connection.get("confidence", 0.5)
                if isinstance(confidence, str):
                    if confidence.lower() == "high":
                        confidence = 0.9
                    elif confidence.lower() == "medium":
                        confidence = 0.6
                    elif confidence.lower() == "low":
                        confidence = 0.3
                    else:
                        confidence = 0.5
                score += confidence * 0.3  # 30% weight for confidence
                
                # Check connection type (up to 30% weight)
                connection_type = duke_connection.get("connection_type", "")
                if connection_type:
                    if isinstance(connection_type, list):
                        connection_type = connection_type[0] if connection_type else ""
                        
                    if "alumni" in connection_type.lower():
                        score += 0.3  # 30% weight for alumni status (highest)
                    elif "faculty" in connection_type.lower():
                        score += 0.2  # 20% weight for faculty status
                    elif "student" in connection_type.lower():
                        score += 0.15  # 15% weight for student status
                    else:
                        score += 0.1  # 10% weight for other connections
            
            # Check graduation year (up to 20% weight)
            graduation_year = data.get("graduation_year") or duke_connection.get("graduation_year")
            if graduation_year and isinstance(graduation_year, (int, str)):
                try:
                    grad_year = int(graduation_year)
                    current_year = datetime.now().year
                    years_since_graduation = current_year - grad_year
                    
                    # Recent graduates get higher scores
                    if years_since_graduation <= 5:
                        score += 0.2  # 20% weight for recent graduates (highest)
                    elif years_since_graduation <= 10:
                        score += 0.15  # 15% weight for graduates within 10 years
                    elif years_since_graduation <= 20:
                        score += 0.1  # 10% weight for graduates within 20 years
                    else:
                        score += 0.05  # 5% weight for older graduates
                except (ValueError, TypeError):
                    pass
            
            # Check degree/major (up to 20% weight)
            degree = data.get("duke_degree") or duke_connection.get("degree", "")
            major = data.get("duke_major") or duke_connection.get("major", "")
            
            # Higher weights for business and engineering degrees
            if degree or major:
                degree_str = (str(degree) + " " + str(major)).lower()
                if any(term in degree_str for term in ["business", "mba", "management", "finance", "economics"]):
                    score += 0.2  # 20% weight for business-related degrees (highest)
                elif any(term in degree_str for term in ["engineering", "computer", "tech", "science"]):
                    score += 0.15  # 15% weight for technical degrees
                else:
                    score += 0.05  # 5% weight for other degrees
            
            # Cap at 1.0
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating Duke affiliation score: {e}", exc_info=True)
            return 0.0
    
    @staticmethod
    def calculate_startup_potential_score(data: Dict[str, Any]) -> float:
        """
        Calculate startup potential score (0-1).
        
        Factors:
        1. Stage of company (pre-seed/seed/Series A weighted higher)
        2. Recent funding activity (raised a round in the last 6 months)
        3. Industry growth potential (AI, biotech, fintech)
        
        Args:
            data: Data dictionary containing startup information
            
        Returns:
            float: Startup potential score (0-1)
        """
        try:
            score = 0.0
            
            # Check company stage (up to 30% weight)
            funding_stage = data.get("latest_funding_stage", "").lower()
            if funding_stage:
                if funding_stage in ["seed", "pre-seed"]:
                    score += 0.3  # 30% weight for seed/pre-seed (highest)
                elif funding_stage == "series_a":
                    score += 0.25  # 25% weight for Series A
                elif funding_stage == "series_b":
                    score += 0.2  # 20% weight for Series B
                elif funding_stage in ["series_c", "series_d"]:
                    score += 0.15  # 15% weight for Series C/D
                elif funding_stage in ["late_stage", "ipo", "acquired"]:
                    score += 0.1  # 10% weight for late stage/IPO/acquired
            
            # Check recent funding activity (up to 30% weight)
            funding_rounds = data.get("funding_rounds", [])
            if funding_rounds and isinstance(funding_rounds, list):
                # Look for recent funding rounds (within last 6 months)
                current_date = datetime.now()
                six_months_ago = current_date - timedelta(days=180)
                
                for round_info in funding_rounds:
                    if isinstance(round_info, dict) and "date" in round_info:
                        try:
                            round_date = datetime.fromisoformat(round_info["date"].replace("Z", "+00:00"))
                            if round_date >= six_months_ago:
                                score += 0.3  # 30% weight for recent funding (highest)
                                break
                        except (ValueError, TypeError):
                            pass
            
            # Check industry growth potential (up to 20% weight)
            industry = data.get("industry", "").lower()
            if industry:
                # High-growth industries get higher scores
                high_growth_industries = [
                    "ai", "artificial intelligence", "machine learning", 
                    "biotech", "biotechnology", "healthcare", 
                    "fintech", "financial technology", 
                    "cleantech", "clean energy", "renewable", 
                    "saas", "software", "cloud"
                ]
                
                if any(term in industry for term in high_growth_industries):
                    score += 0.2  # 20% weight for high-growth industries (highest)
                else:
                    score += 0.1  # 10% weight for other industries
            
            # Check total funding amount (up to 20% weight)
            total_funding = data.get("total_funding")
            if total_funding:
                try:
                    # Ensure we're working with a number
                    funding_value = float(total_funding)
                    
                    # Scale based on funding amount
                    if funding_value < 1_000_000:  # Less than $1M
                        score += 0.2  # 20% weight for early-stage startups (highest)
                    elif funding_value < 5_000_000:  # $1M - $5M
                        score += 0.15  # 15% weight for early growth
                    elif funding_value < 20_000_000:  # $5M - $20M
                        score += 0.1  # 10% weight for mid-stage
                    else:  # More than $20M
                        score += 0.05  # 5% weight for later-stage (less growth potential)
                except (ValueError, TypeError):
                    pass
            
            # Cap at 1.0
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating startup potential score: {e}", exc_info=True)
            return 0.0
    
    @staticmethod
    def calculate_content_relevance_score(data: Dict[str, Any]) -> float:
        """
        Calculate content relevance score (0-1).
        
        Factors:
        1. Data freshness (recent data weighted higher)
        2. Data quality (completeness of information)
        3. Source reliability (verified sources weighted higher)
        
        Args:
            data: Data dictionary containing content information
            
        Returns:
            float: Content relevance score (0-1)
        """
        try:
            score = 0.0
            
            # Check data freshness (up to 40% weight)
            freshness_score = data.get("data_freshness_score")
            if freshness_score is not None and isinstance(freshness_score, (int, float)):
                score += min(freshness_score, 1.0) * 0.4  # 40% weight for freshness
            
            # Check data quality (up to 40% weight)
            quality_score = data.get("data_quality_score")
            if quality_score is not None and isinstance(quality_score, (int, float)):
                score += min(quality_score, 1.0) * 0.4  # 40% weight for quality
            
            # Check source reliability (up to 20% weight)
            sources = data.get("data_sources", [])
            if sources and isinstance(sources, list):
                # Higher weights for more reliable sources
                reliable_sources = [
                    "linkedin", "crunchbase", "pitchbook", "bloomberg", 
                    "techcrunch", "wsj", "ft", "reuters", "duke.edu"
                ]
                
                reliability_score = 0.0
                for source in sources:
                    if isinstance(source, str):
                        source_lower = source.lower()
                        if any(rs in source_lower for rs in reliable_sources):
                            reliability_score += 0.1  # 10% per reliable source
                
                score += min(reliability_score, 0.2)  # Cap at 20% weight for reliability
            
            # Cap at 1.0
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating content relevance score: {e}", exc_info=True)
            return 0.0 