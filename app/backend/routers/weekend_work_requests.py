import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.weekend_work_requests import Weekend_work_requestsService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/weekend_work_requests", tags=["weekend_work_requests"])


# ---------- Pydantic Schemas ----------
class Weekend_work_requestsData(BaseModel):
    """Entity data schema (for create/update)"""
    emp_no: str
    employee_name: str = None
    department: str = None
    work_date: date
    day_type: str = None
    planned_start: str = None
    planned_end: str = None
    planned_minutes: int = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    actual_minutes: int = None
    premium_rate: float = None
    reason: str = None
    status: str = None
    approval_id: int = None
    matched: bool = None


class Weekend_work_requestsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    emp_no: Optional[str] = None
    employee_name: Optional[str] = None
    department: Optional[str] = None
    work_date: Optional[date] = None
    day_type: Optional[str] = None
    planned_start: Optional[str] = None
    planned_end: Optional[str] = None
    planned_minutes: Optional[int] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    actual_minutes: Optional[int] = None
    premium_rate: Optional[float] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    approval_id: Optional[int] = None
    matched: Optional[bool] = None


class Weekend_work_requestsResponse(BaseModel):
    """Entity response schema"""
    id: int
    emp_no: str
    employee_name: Optional[str] = None
    department: Optional[str] = None
    work_date: date
    day_type: Optional[str] = None
    planned_start: Optional[str] = None
    planned_end: Optional[str] = None
    planned_minutes: Optional[int] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    actual_minutes: Optional[int] = None
    premium_rate: Optional[float] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    approval_id: Optional[int] = None
    matched: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Weekend_work_requestsListResponse(BaseModel):
    """List response schema"""
    items: List[Weekend_work_requestsResponse]
    total: int
    skip: int
    limit: int


class Weekend_work_requestsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Weekend_work_requestsData]


class Weekend_work_requestsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Weekend_work_requestsUpdateData


class Weekend_work_requestsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Weekend_work_requestsBatchUpdateItem]


class Weekend_work_requestsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Weekend_work_requestsListResponse)
async def query_weekend_work_requestss(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query weekend_work_requestss with filtering, sorting, and pagination"""
    logger.debug(f"Querying weekend_work_requestss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Weekend_work_requestsService(db)
    try:
        # Parse query JSON if provided
        query_dict = None
        if query:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid query JSON format")
        
        result = await service.get_list(
            skip=skip, 
            limit=limit,
            query_dict=query_dict,
            sort=sort,
        )
        logger.debug(f"Found {result['total']} weekend_work_requestss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid weekend_work_requests query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying weekend_work_requestss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Weekend_work_requestsListResponse)
async def query_weekend_work_requestss_all(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query weekend_work_requestss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying weekend_work_requestss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Weekend_work_requestsService(db)
    try:
        # Parse query JSON if provided
        query_dict = None
        if query:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid query JSON format")

        result = await service.get_list(
            skip=skip,
            limit=limit,
            query_dict=query_dict,
            sort=sort
        )
        logger.debug(f"Found {result['total']} weekend_work_requestss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid weekend_work_requests query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying weekend_work_requestss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Weekend_work_requestsResponse)
async def get_weekend_work_requests(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single weekend_work_requests by ID"""
    logger.debug(f"Fetching weekend_work_requests with id: {id}, fields={fields}")
    
    service = Weekend_work_requestsService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Weekend_work_requests with id {id} not found")
            raise HTTPException(status_code=404, detail="Weekend_work_requests not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching weekend_work_requests {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Weekend_work_requestsResponse, status_code=201)
async def create_weekend_work_requests(
    data: Weekend_work_requestsData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new weekend_work_requests"""
    logger.debug(f"Creating new weekend_work_requests with data: {data}")
    
    service = Weekend_work_requestsService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create weekend_work_requests")
        
        logger.info(f"Weekend_work_requests created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating weekend_work_requests: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating weekend_work_requests: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Weekend_work_requestsResponse], status_code=201)
async def create_weekend_work_requestss_batch(
    request: Weekend_work_requestsBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple weekend_work_requestss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} weekend_work_requestss")
    
    service = Weekend_work_requestsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} weekend_work_requestss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Weekend_work_requestsResponse])
async def update_weekend_work_requestss_batch(
    request: Weekend_work_requestsBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple weekend_work_requestss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} weekend_work_requestss")
    
    service = Weekend_work_requestsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} weekend_work_requestss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Weekend_work_requestsResponse)
async def update_weekend_work_requests(
    id: int,
    data: Weekend_work_requestsUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing weekend_work_requests"""
    logger.debug(f"Updating weekend_work_requests {id} with data: {data}")

    service = Weekend_work_requestsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Weekend_work_requests with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Weekend_work_requests not found")
        
        logger.info(f"Weekend_work_requests {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating weekend_work_requests {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating weekend_work_requests {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_weekend_work_requestss_batch(
    request: Weekend_work_requestsBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple weekend_work_requestss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} weekend_work_requestss")
    
    service = Weekend_work_requestsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} weekend_work_requestss successfully")
        return {"message": f"Successfully deleted {deleted_count} weekend_work_requestss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_weekend_work_requests(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single weekend_work_requests by ID"""
    logger.debug(f"Deleting weekend_work_requests with id: {id}")
    
    service = Weekend_work_requestsService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Weekend_work_requests with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Weekend_work_requests not found")
        
        logger.info(f"Weekend_work_requests {id} deleted successfully")
        return {"message": "Weekend_work_requests deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting weekend_work_requests {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")