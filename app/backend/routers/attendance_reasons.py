import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.attendance_reasons import Attendance_reasonsService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/attendance_reasons", tags=["attendance_reasons"])


# ---------- Pydantic Schemas ----------
class Attendance_reasonsData(BaseModel):
    """Entity data schema (for create/update)"""
    code: str
    name: str
    category: str = None
    pay_effect: str = None
    deduct_rate: float = None
    requires_approval: bool = None
    offsettable: bool = None
    sort_order: int = None
    description: str = None
    active: bool = None


class Attendance_reasonsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    pay_effect: Optional[str] = None
    deduct_rate: Optional[float] = None
    requires_approval: Optional[bool] = None
    offsettable: Optional[bool] = None
    sort_order: Optional[int] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class Attendance_reasonsResponse(BaseModel):
    """Entity response schema"""
    id: int
    code: str
    name: str
    category: Optional[str] = None
    pay_effect: Optional[str] = None
    deduct_rate: Optional[float] = None
    requires_approval: Optional[bool] = None
    offsettable: Optional[bool] = None
    sort_order: Optional[int] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Attendance_reasonsListResponse(BaseModel):
    """List response schema"""
    items: List[Attendance_reasonsResponse]
    total: int
    skip: int
    limit: int


class Attendance_reasonsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Attendance_reasonsData]


class Attendance_reasonsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Attendance_reasonsUpdateData


class Attendance_reasonsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Attendance_reasonsBatchUpdateItem]


class Attendance_reasonsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Attendance_reasonsListResponse)
async def query_attendance_reasonss(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query attendance_reasonss with filtering, sorting, and pagination"""
    logger.debug(f"Querying attendance_reasonss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Attendance_reasonsService(db)
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
        logger.debug(f"Found {result['total']} attendance_reasonss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid attendance_reasons query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying attendance_reasonss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Attendance_reasonsListResponse)
async def query_attendance_reasonss_all(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query attendance_reasonss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying attendance_reasonss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Attendance_reasonsService(db)
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
        logger.debug(f"Found {result['total']} attendance_reasonss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid attendance_reasons query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying attendance_reasonss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Attendance_reasonsResponse)
async def get_attendance_reasons(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single attendance_reasons by ID"""
    logger.debug(f"Fetching attendance_reasons with id: {id}, fields={fields}")
    
    service = Attendance_reasonsService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Attendance_reasons with id {id} not found")
            raise HTTPException(status_code=404, detail="Attendance_reasons not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching attendance_reasons {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Attendance_reasonsResponse, status_code=201)
async def create_attendance_reasons(
    data: Attendance_reasonsData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new attendance_reasons"""
    logger.debug(f"Creating new attendance_reasons with data: {data}")
    
    service = Attendance_reasonsService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create attendance_reasons")
        
        logger.info(f"Attendance_reasons created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating attendance_reasons: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating attendance_reasons: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Attendance_reasonsResponse], status_code=201)
async def create_attendance_reasonss_batch(
    request: Attendance_reasonsBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple attendance_reasonss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} attendance_reasonss")
    
    service = Attendance_reasonsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} attendance_reasonss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Attendance_reasonsResponse])
async def update_attendance_reasonss_batch(
    request: Attendance_reasonsBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple attendance_reasonss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} attendance_reasonss")
    
    service = Attendance_reasonsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} attendance_reasonss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Attendance_reasonsResponse)
async def update_attendance_reasons(
    id: int,
    data: Attendance_reasonsUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing attendance_reasons"""
    logger.debug(f"Updating attendance_reasons {id} with data: {data}")

    service = Attendance_reasonsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Attendance_reasons with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Attendance_reasons not found")
        
        logger.info(f"Attendance_reasons {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating attendance_reasons {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating attendance_reasons {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_attendance_reasonss_batch(
    request: Attendance_reasonsBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple attendance_reasonss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} attendance_reasonss")
    
    service = Attendance_reasonsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} attendance_reasonss successfully")
        return {"message": f"Successfully deleted {deleted_count} attendance_reasonss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_attendance_reasons(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single attendance_reasons by ID"""
    logger.debug(f"Deleting attendance_reasons with id: {id}")
    
    service = Attendance_reasonsService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Attendance_reasons with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Attendance_reasons not found")
        
        logger.info(f"Attendance_reasons {id} deleted successfully")
        return {"message": "Attendance_reasons deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting attendance_reasons {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")