"""
Base API endpoint class for the DCP AI Scouting Platform.

This module provides a base class for API endpoints to reduce code duplication
and standardize common operations like background refreshing, Twitter data handling,
and database operations.
"""
import logging
import json
from typing import Dict, Any, List, Optional, Type, Generic, TypeVar, Tuple
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel

from db.database.db import get_db
from db.database.models import SERPUsage
from backend.config.logs import LogManager
from backend.config.cache import cached, CacheManager
from backend.config.config import settings

# Initialize logger
logger = logging.getLogger(__name__)

# Generic type variables
T = TypeVar('T')  # Database model
R = TypeVar('R')  # Response model

class BaseEndpoint(Generic[T, R]):
    """
    Base class for API endpoints.
    
    This class provides common functionality for API endpoints, including:
    - Background refresh handling
    - Twitter data processing
    - Database operations
    - Error handling
    - Caching
    
    Generic parameters:
    - T: Database model class
    - R: Response model class
    """
    
    def __init__(
        self,
        model_class: Type[T],
        response_class: Type[R],
        entity_type: str,
        cache_prefix: str,
        cache_expire: int = None
    ):
        """
        Initialize the base endpoint.
        
        Args:
            model_class: SQLAlchemy model class
            response_class: Pydantic response model class
            entity_type: Entity type (e.g., "company", "founder")
            cache_prefix: Cache prefix for the entity
            cache_expire: Cache expiration time in seconds (defaults to settings)
        """
        self.model_class = model_class
        self.response_class = response_class
        self.entity_type = entity_type
        self.cache_prefix = cache_prefix
        
        # Use settings-based cache expiration if not provided
        if cache_expire is None:
            if entity_type == "company":
                self.cache_expire = settings.cache.COMPANY_TTL
            elif entity_type == "founder":
                self.cache_expire = settings.cache.FOUNDER_TTL
            else:
                self.cache_expire = settings.cache.DEFAULT_TTL
        else:
            self.cache_expire = cache_expire
            
        logger.debug(f"Initialized {entity_type} endpoint with cache TTL: {self.cache_expire}s")
    
    async def track_serp_usage(
        self,
        db: AsyncSession,
        query_count: int,
        entity_name: str
    ) -> None:
        """
        Track SERP API usage for monitoring and quota management.
        
        Args:
            db: Database session
            query_count: Number of queries made
            entity_name: Name of the entity being searched
        """
        try:
            # Check daily quota
            today = datetime.now(timezone.utc).date()
            start_of_day = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
            
            # Get today's usage
            query = select(func.sum(SERPUsage.query_count)).where(
                SERPUsage.timestamp >= start_of_day
            )
            result = await db.execute(query)
            daily_usage = result.scalar() or 0
            
            # Check if we're over quota
            if daily_usage + query_count > settings.scraper.DAILY_QUOTA:
                logger.warning(f"SERP API daily quota exceeded: {daily_usage}/{settings.scraper.DAILY_QUOTA}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="SERP API daily quota exceeded. Please try again tomorrow."
                )
            
            # Record usage
            usage = SERPUsage(
                timestamp=datetime.now(timezone.utc),
                query_count=query_count,
                entity_name=entity_name,
                entity_type=self.entity_type,
                endpoint=f"{self.entity_type}_api"
            )
            db.add(usage)
            await db.commit()
            
            logger.info(f"Tracked {query_count} SERP queries for {entity_name} ({self.entity_type})")
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to track SERP usage: {e}", exc_info=True)
    
    async def get_entity_from_db(
        self,
        db: AsyncSession,
        name: str
    ) -> Optional[T]:
        """
        Get an entity from the database by name.
        
        Args:
            db: Database session
            name: Entity name
            
        Returns:
            Entity if found, None otherwise
        """
        try:
            # Get the name field for the model
            name_field = self.get_name_field()
            
            # Build query
            query = select(self.model_class).where(
                getattr(self.model_class, name_field) == name
            )
            
            # Execute query
            result = await db.execute(query)
            entity = result.scalars().first()
            
            return entity
        except Exception as e:
            logger.error(f"Error getting {self.entity_type} from database: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while retrieving {self.entity_type}"
            )
    
    def get_name_field(self) -> str:
        """
        Get the name field for the model.
        
        Returns:
            Name field for the model
        """
        # Default name fields based on entity type
        if self.entity_type == "company":
            return "name"
        elif self.entity_type == "founder":
            return "full_name"
        else:
            return "name"  # Default
    
    def prepare_twitter_summary(self, entity: T) -> Optional[Dict[str, Any]]:
        """
        Prepare Twitter summary from entity.
        
        Args:
            entity: Database entity
            
        Returns:
            Twitter summary if available, None otherwise
        """
        try:
            # Check if entity has Twitter data
            if not hasattr(entity, "twitter_data") or not entity.twitter_data:
                return None
                
            # Parse Twitter data
            twitter_data = json.loads(entity.twitter_data) if isinstance(entity.twitter_data, str) else entity.twitter_data
            
            # Extract relevant fields
            return {
                "summary": twitter_data.get("summary", ""),
                "actionability_score": twitter_data.get("actionability_score", 0),
                "topics": twitter_data.get("topics", []),
                "key_insights": twitter_data.get("key_insights", [])[:3],  # Limit to top 3 insights
                "last_updated": entity.twitter_last_updated.isoformat() if entity.twitter_last_updated else None
            }
        except Exception as e:
            logger.error(f"Error preparing Twitter summary: {e}", exc_info=True)
            return None
    
    def prepare_response(
        self,
        entity: T,
        is_refreshing: bool = False
    ) -> R:
        """
        Prepare response from entity.
        
        Args:
            entity: Database entity
            is_refreshing: Whether the entity is being refreshed in the background
            
        Returns:
            Response model
        """
        try:
            # Convert entity to dict
            entity_dict = {c.name: getattr(entity, c.name) for c in entity.__table__.columns}
            
            # Add Twitter summary if available
            twitter_summary = self.prepare_twitter_summary(entity)
            if twitter_summary:
                entity_dict["twitter_summary"] = twitter_summary.get("summary", "")
                entity_dict["twitter_actionability"] = twitter_summary.get("actionability_score", 0)
                entity_dict["twitter_last_updated"] = twitter_summary.get("last_updated")
            
            # Add metadata
            entity_dict["is_refreshing"] = is_refreshing
            entity_dict["last_updated"] = entity.last_updated.isoformat() if entity.last_updated else None
            entity_dict["created_at"] = entity.created_at.isoformat() if entity.created_at else None
            
            # Calculate data freshness
            if entity.last_updated:
                age = datetime.now(timezone.utc) - entity.last_updated
                days = age.days
                
                if days <= 1:
                    entity_dict["data_freshness_score"] = 1.0
                elif days <= 7:
                    entity_dict["data_freshness_score"] = 0.8
                elif days <= 30:
                    entity_dict["data_freshness_score"] = 0.6
                elif days <= 90:
                    entity_dict["data_freshness_score"] = 0.4
                else:
                    entity_dict["data_freshness_score"] = 0.2
            
            # Create response model
            return self.response_class(**entity_dict)
        except Exception as e:
            logger.error(f"Error preparing response: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error preparing {self.entity_type} response"
            )
    
    @cached("stats", expire=300)  # Cache for 5 minutes
    async def get_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get statistics for the entity type.
        
        Args:
            db: Database session
            
        Returns:
            Statistics dictionary
        """
        try:
            # Get total count
            total_query = select(func.count(self.model_class.id))
            total_result = await db.execute(total_query)
            total_count = total_result.scalar() or 0
            
            # Get Duke-affiliated count if applicable
            duke_count = 0
            if hasattr(self.model_class, "duke_affiliated"):
                duke_query = select(func.count(self.model_class.id)).where(
                    self.model_class.duke_affiliated == True
                )
                duke_result = await db.execute(duke_query)
                duke_count = duke_result.scalar() or 0
            
            # Get recently updated count
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_query = select(func.count(self.model_class.id)).where(
                self.model_class.last_updated >= recent_cutoff
            )
            recent_result = await db.execute(recent_query)
            recent_count = recent_result.scalar() or 0
            
            # Get creation date distribution
            creation_query = select(
                func.date_trunc('month', self.model_class.created_at).label('month'),
                func.count(self.model_class.id).label('count')
            ).group_by('month').order_by('month')
            creation_result = await db.execute(creation_query)
            creation_distribution = [
                {"month": row.month.isoformat() if row.month else None, "count": row.count}
                for row in creation_result
            ]
            
            # Return stats
            return {
                "total_count": total_count,
                "duke_affiliated_count": duke_count,
                "duke_affiliated_percentage": round((duke_count / total_count) * 100, 1) if total_count > 0 else 0,
                "recently_updated_count": recent_count,
                "creation_distribution": creation_distribution,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting {self.entity_type} stats: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving {self.entity_type} statistics"
            )
    
    async def get_entities_by_filter(
        self,
        db: AsyncSession,
        filters: Dict[str, Any],
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[T], int]:
        """
        Get entities by filter.
        
        Args:
            db: Database session
            filters: Filter dictionary
            page: Page number (1-indexed)
            page_size: Page size
            
        Returns:
            Tuple of (entities, total_count)
        """
        try:
            # Build base query
            query = select(self.model_class)
            count_query = select(func.count(self.model_class.id))
            
            # Apply filters
            filter_conditions = []
            for field, value in filters.items():
                if hasattr(self.model_class, field) and value is not None:
                    if field == "duke_affiliated" and isinstance(value, bool):
                        filter_conditions.append(getattr(self.model_class, field) == value)
                    elif isinstance(value, str) and value:
                        filter_conditions.append(getattr(self.model_class, field).ilike(f"%{value}%"))
            
            # Apply filter conditions
            if filter_conditions:
                query = query.where(and_(*filter_conditions))
                count_query = count_query.where(and_(*filter_conditions))
            
            # Get total count
            count_result = await db.execute(count_query)
            total_count = count_result.scalar() or 0
            
            # Apply pagination
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            # Execute query
            result = await db.execute(query)
            entities = result.scalars().all()
            
            return entities, total_count
        except Exception as e:
            logger.error(f"Error getting {self.entity_type} entities by filter: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving {self.entity_type} entities"
            )
    
    async def check_data_freshness(
        self,
        entity: T,
        max_age_hours: int = 24
    ) -> bool:
        """
        Check if the entity data is fresh enough.
        
        Args:
            entity: Entity to check
            max_age_hours: Maximum age in hours
            
        Returns:
            True if data is fresh, False otherwise
        """
        if not entity or not entity.last_updated:
            return False
            
        now = datetime.now(timezone.utc)
        age = now - entity.last_updated
        return age.total_seconds() < (max_age_hours * 3600) 