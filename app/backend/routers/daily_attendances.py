import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.daily_attendances import Daily_attendancesService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/daily_attendances", tags=["daily_attendances"])


# ---------- Pydantic Schemas ----------
class Daily_attendancesData(BaseModel):
    """Entity data schema (for create/update)"""
    emp_no: str
    employee_name: str = None
    department: str = None
    work_date: date
    day_type: str = None
    raw_check_in: Optional[datetime] = None
    raw_check_out: Optional[datetime] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    log_count: int = None
    scheduled_minutes: int = None
    work_minutes: int = None
    overtime_minutes: int = None
    night_minutes: int = None
    holiday_minutes: int = None
    late_minutes: int = None
    early_leave_minutes: int = None
    offset_minutes: int = None
    status: str = None
    reason_code: str = None
    reason_note: str = None
    adjusted: bool = None
    adjusted_by: str = None
    adjust_history: str = None
    confirm_status: str = None
    approval_id: int = None
    leave_request_id: int = None
    locked: bool = None


class Daily_attendancesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    emp_no: Optional[str] = None
    employee_name: Optional[str] = None
    department: Optional[str] = None
    work_date: Optional[date] = None
    day_type: Optional[str] = None
    raw_check_in: Optional[datetime] = None
    raw_check_out: Optional[datetime] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    log_count: Optional[int] = None
    scheduled_minutes: Optional[int] = None
    work_minutes: Optional[int] = None
    overtime_minutes: Optional[int] = None
    night_minutes: Optional[int] = None
    holiday_minutes: Optional[int] = None
    late_minutes: Optional[int] = None
    early_leave_minutes: Optional[int] = None
    offset_minutes: Optional[int] = None
    status: Optional[str] = None
    reason_code: Optional[str] = None
    reason_note: Optional[str] = None
    adjusted: Optional[bool] = None
    adjusted_by: Optional[str] = None
    adjust_history: Optional[str] = None
    confirm_status: Optional[str] = None
    approval_id: Optional[int] = None
    leave_request_id: Optional[int] = None
    locked: Optional[bool] = None


class Daily_attendancesResponse(BaseModel):
    """Entity response schema"""
    id: int
    emp_no: str
    employee_name: Optional[str] = None
    department: Optional[str] = None
    work_date: date
    day_type: Optional[str] = None
    raw_check_in: Optional[datetime] = None
    raw_check_out: Optional[datetime] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    log_count: Optional[int] = None
    scheduled_minutes: Optional[int] = None
    work_minutes: Optional[int] = None
    overtime_minutes: Optional[int] = None
    night_minutes: Optional[int] = None
    holiday_minutes: Optional[int] = None
    late_minutes: Optional[int] = None
    early_leave_minutes: Optional[int] = None
    offset_minutes: Optional[int] = None
    status: Optional[str] = None
    reason_code: Optional[str] = None
    reason_note: Optional[str] = None
    adjusted: Optional[bool] = None
    adjusted_by: Optional[str] = None
    adjust_history: Optional[str] = None
    confirm_status: Optional[str] = None
    approval_id: Optional[int] = None
    leave_request_id: Optional[int] = None
    locked: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Daily_attendancesListResponse(BaseModel):
    """List response schema"""
    items: List[Daily_attendancesResponse]
    total: int
    skip: int
    limit: int


class Daily_attendancesBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Daily_attendancesData]


class Daily_attendancesBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Daily_attendancesUpdateData


class Daily_attendancesBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Daily_attendancesBatchUpdateItem]


class Daily_attendancesBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Daily_attendancesListResponse)
async def query_daily_attendancess(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query daily_attendancess with filtering, sorting, and pagination"""
    logger.debug(f"Querying daily_attendancess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Daily_attendancesService(db)
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
        logger.debug(f"Found {result['total']} daily_attendancess")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid daily_attendances query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying daily_attendancess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Daily_attendancesListResponse)
async def query_daily_attendancess_all(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query daily_attendancess with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying daily_attendancess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Daily_attendancesService(db)
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
        logger.debug(f"Found {result['total']} daily_attendancess")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid daily_attendances query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying daily_attendancess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Daily_attendancesResponse)
async def get_daily_attendances(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single daily_attendances by ID"""
    logger.debug(f"Fetching daily_attendances with id: {id}, fields={fields}")
    
    service = Daily_attendancesService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Daily_attendances with id {id} not found")
            raise HTTPException(status_code=404, detail="Daily_attendances not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching daily_attendances {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Daily_attendancesResponse, status_code=201)
async def create_daily_attendances(
    data: Daily_attendancesData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new daily_attendances"""
    logger.debug(f"Creating new daily_attendances with data: {data}")
    
    service = Daily_attendancesService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create daily_attendances")
        
        logger.info(f"Daily_attendances created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating daily_attendances: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating daily_attendances: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Daily_attendancesResponse], status_code=201)
async def create_daily_attendancess_batch(
    request: Daily_attendancesBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple daily_attendancess in a single request"""
    logger.debug(f"Batch creating {len(request.items)} daily_attendancess")
    
    service = Daily_attendancesService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} daily_attendancess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Daily_attendancesResponse])
async def update_daily_attendancess_batch(
    request: Daily_attendancesBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple daily_attendancess in a single request"""
    logger.debug(f"Batch updating {len(request.items)} daily_attendancess")
    
    service = Daily_attendancesService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} daily_attendancess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Daily_attendancesResponse)
async def update_daily_attendances(
    id: int,
    data: Daily_attendancesUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing daily_attendances"""
    logger.debug(f"Updating daily_attendances {id} with data: {data}")

    service = Daily_attendancesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Daily_attendances with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Daily_attendances not found")
        
        logger.info(f"Daily_attendances {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating daily_attendances {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating daily_attendances {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_daily_attendancess_batch(
    request: Daily_attendancesBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple daily_attendancess by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} daily_attendancess")
    
    service = Daily_attendancesService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} daily_attendancess successfully")
        return {"message": f"Successfully deleted {deleted_count} daily_attendancess", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_daily_attendances(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single daily_attendances by ID"""
    logger.debug(f"Deleting daily_attendances with id: {id}")
    
    service = Daily_attendancesService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Daily_attendances with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Daily_attendances not found")
        
        logger.info(f"Daily_attendances {id} deleted successfully")
        return {"message": "Daily_attendances deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting daily_attendances {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")