import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.overtime_banks import Overtime_banksService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/overtime_banks", tags=["overtime_banks"])


# ---------- Pydantic Schemas ----------
class Overtime_banksData(BaseModel):
    """Entity data schema (for create/update)"""
    emp_no: str
    employee_name: str = None
    department: str = None
    txn_type: str
    txn_date: Optional[date] = None
    source_date: Optional[date] = None
    minutes: int
    balance_after: int = None
    target_leave_days: float = None
    target_attendance_id: int = None
    status: str = None
    approval_id: int = None
    note: str = None


class Overtime_banksUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    emp_no: Optional[str] = None
    employee_name: Optional[str] = None
    department: Optional[str] = None
    txn_type: Optional[str] = None
    txn_date: Optional[date] = None
    source_date: Optional[date] = None
    minutes: Optional[int] = None
    balance_after: Optional[int] = None
    target_leave_days: Optional[float] = None
    target_attendance_id: Optional[int] = None
    status: Optional[str] = None
    approval_id: Optional[int] = None
    note: Optional[str] = None


class Overtime_banksResponse(BaseModel):
    """Entity response schema"""
    id: int
    emp_no: str
    employee_name: Optional[str] = None
    department: Optional[str] = None
    txn_type: str
    txn_date: Optional[date] = None
    source_date: Optional[date] = None
    minutes: int
    balance_after: Optional[int] = None
    target_leave_days: Optional[float] = None
    target_attendance_id: Optional[int] = None
    status: Optional[str] = None
    approval_id: Optional[int] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Overtime_banksListResponse(BaseModel):
    """List response schema"""
    items: List[Overtime_banksResponse]
    total: int
    skip: int
    limit: int


class Overtime_banksBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Overtime_banksData]


class Overtime_banksBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Overtime_banksUpdateData


class Overtime_banksBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Overtime_banksBatchUpdateItem]


class Overtime_banksBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Overtime_banksListResponse)
async def query_overtime_bankss(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query overtime_bankss with filtering, sorting, and pagination"""
    logger.debug(f"Querying overtime_bankss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Overtime_banksService(db)
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
        logger.debug(f"Found {result['total']} overtime_bankss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid overtime_banks query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying overtime_bankss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Overtime_banksListResponse)
async def query_overtime_bankss_all(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query overtime_bankss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying overtime_bankss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Overtime_banksService(db)
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
        logger.debug(f"Found {result['total']} overtime_bankss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid overtime_banks query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying overtime_bankss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Overtime_banksResponse)
async def get_overtime_banks(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single overtime_banks by ID"""
    logger.debug(f"Fetching overtime_banks with id: {id}, fields={fields}")
    
    service = Overtime_banksService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Overtime_banks with id {id} not found")
            raise HTTPException(status_code=404, detail="Overtime_banks not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching overtime_banks {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Overtime_banksResponse, status_code=201)
async def create_overtime_banks(
    data: Overtime_banksData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new overtime_banks"""
    logger.debug(f"Creating new overtime_banks with data: {data}")
    
    service = Overtime_banksService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create overtime_banks")
        
        logger.info(f"Overtime_banks created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating overtime_banks: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating overtime_banks: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Overtime_banksResponse], status_code=201)
async def create_overtime_bankss_batch(
    request: Overtime_banksBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple overtime_bankss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} overtime_bankss")
    
    service = Overtime_banksService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} overtime_bankss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Overtime_banksResponse])
async def update_overtime_bankss_batch(
    request: Overtime_banksBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple overtime_bankss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} overtime_bankss")
    
    service = Overtime_banksService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} overtime_bankss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Overtime_banksResponse)
async def update_overtime_banks(
    id: int,
    data: Overtime_banksUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing overtime_banks"""
    logger.debug(f"Updating overtime_banks {id} with data: {data}")

    service = Overtime_banksService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Overtime_banks with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Overtime_banks not found")
        
        logger.info(f"Overtime_banks {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating overtime_banks {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating overtime_banks {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_overtime_bankss_batch(
    request: Overtime_banksBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple overtime_bankss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} overtime_bankss")
    
    service = Overtime_banksService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} overtime_bankss successfully")
        return {"message": f"Successfully deleted {deleted_count} overtime_bankss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_overtime_banks(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single overtime_banks by ID"""
    logger.debug(f"Deleting overtime_banks with id: {id}")
    
    service = Overtime_banksService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Overtime_banks with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Overtime_banks not found")
        
        logger.info(f"Overtime_banks {id} deleted successfully")
        return {"message": "Overtime_banks deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting overtime_banks {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")