import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.access_logs import Access_logsService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/access_logs", tags=["access_logs"])


# ---------- Pydantic Schemas ----------
class Access_logsData(BaseModel):
    """Entity data schema (for create/update)"""
    emp_no: str
    employee_name: str = None
    terminal_id: str = None
    device_name: str = None
    event_time: datetime
    event_date: Optional[date] = None
    event_type: str = None
    auth_mode: str = None
    source: str = None
    raw_payload: str = None


class Access_logsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    emp_no: Optional[str] = None
    employee_name: Optional[str] = None
    terminal_id: Optional[str] = None
    device_name: Optional[str] = None
    event_time: Optional[datetime] = None
    event_date: Optional[date] = None
    event_type: Optional[str] = None
    auth_mode: Optional[str] = None
    source: Optional[str] = None
    raw_payload: Optional[str] = None


class Access_logsResponse(BaseModel):
    """Entity response schema"""
    id: int
    emp_no: str
    employee_name: Optional[str] = None
    terminal_id: Optional[str] = None
    device_name: Optional[str] = None
    event_time: datetime
    event_date: Optional[date] = None
    event_type: Optional[str] = None
    auth_mode: Optional[str] = None
    source: Optional[str] = None
    raw_payload: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Access_logsListResponse(BaseModel):
    """List response schema"""
    items: List[Access_logsResponse]
    total: int
    skip: int
    limit: int


class Access_logsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Access_logsData]


class Access_logsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Access_logsUpdateData


class Access_logsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Access_logsBatchUpdateItem]


class Access_logsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Access_logsListResponse)
async def query_access_logss(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query access_logss with filtering, sorting, and pagination"""
    logger.debug(f"Querying access_logss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Access_logsService(db)
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
        logger.debug(f"Found {result['total']} access_logss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid access_logs query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying access_logss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Access_logsListResponse)
async def query_access_logss_all(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query access_logss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying access_logss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Access_logsService(db)
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
        logger.debug(f"Found {result['total']} access_logss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid access_logs query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying access_logss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Access_logsResponse)
async def get_access_logs(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single access_logs by ID"""
    logger.debug(f"Fetching access_logs with id: {id}, fields={fields}")
    
    service = Access_logsService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Access_logs with id {id} not found")
            raise HTTPException(status_code=404, detail="Access_logs not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching access_logs {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Access_logsResponse, status_code=201)
async def create_access_logs(
    data: Access_logsData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new access_logs"""
    logger.debug(f"Creating new access_logs with data: {data}")
    
    service = Access_logsService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create access_logs")
        
        logger.info(f"Access_logs created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating access_logs: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating access_logs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Access_logsResponse], status_code=201)
async def create_access_logss_batch(
    request: Access_logsBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple access_logss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} access_logss")
    
    service = Access_logsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} access_logss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Access_logsResponse])
async def update_access_logss_batch(
    request: Access_logsBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple access_logss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} access_logss")
    
    service = Access_logsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} access_logss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Access_logsResponse)
async def update_access_logs(
    id: int,
    data: Access_logsUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing access_logs"""
    logger.debug(f"Updating access_logs {id} with data: {data}")

    service = Access_logsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Access_logs with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Access_logs not found")
        
        logger.info(f"Access_logs {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating access_logs {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating access_logs {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_access_logss_batch(
    request: Access_logsBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple access_logss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} access_logss")
    
    service = Access_logsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} access_logss successfully")
        return {"message": f"Successfully deleted {deleted_count} access_logss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_access_logs(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single access_logs by ID"""
    logger.debug(f"Deleting access_logs with id: {id}")
    
    service = Access_logsService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Access_logs with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Access_logs not found")
        
        logger.info(f"Access_logs {id} deleted successfully")
        return {"message": "Access_logs deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting access_logs {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")