import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.leave_balances import Leave_balancesService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/leave_balances", tags=["leave_balances"])


# ---------- Pydantic Schemas ----------
class Leave_balancesData(BaseModel):
    """Entity data schema (for create/update)"""
    emp_no: str
    employee_name: str = None
    department: str = None
    year: int
    leave_type: str
    granted_days: float = None
    used_days: float = None
    pending_days: float = None
    converted_days: float = None
    note: str = None


class Leave_balancesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    emp_no: Optional[str] = None
    employee_name: Optional[str] = None
    department: Optional[str] = None
    year: Optional[int] = None
    leave_type: Optional[str] = None
    granted_days: Optional[float] = None
    used_days: Optional[float] = None
    pending_days: Optional[float] = None
    converted_days: Optional[float] = None
    note: Optional[str] = None


class Leave_balancesResponse(BaseModel):
    """Entity response schema"""
    id: int
    emp_no: str
    employee_name: Optional[str] = None
    department: Optional[str] = None
    year: int
    leave_type: str
    granted_days: Optional[float] = None
    used_days: Optional[float] = None
    pending_days: Optional[float] = None
    converted_days: Optional[float] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Leave_balancesListResponse(BaseModel):
    """List response schema"""
    items: List[Leave_balancesResponse]
    total: int
    skip: int
    limit: int


class Leave_balancesBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Leave_balancesData]


class Leave_balancesBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Leave_balancesUpdateData


class Leave_balancesBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Leave_balancesBatchUpdateItem]


class Leave_balancesBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Leave_balancesListResponse)
async def query_leave_balancess(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query leave_balancess with filtering, sorting, and pagination"""
    logger.debug(f"Querying leave_balancess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Leave_balancesService(db)
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
        logger.debug(f"Found {result['total']} leave_balancess")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid leave_balances query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying leave_balancess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Leave_balancesListResponse)
async def query_leave_balancess_all(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query leave_balancess with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying leave_balancess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Leave_balancesService(db)
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
        logger.debug(f"Found {result['total']} leave_balancess")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid leave_balances query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying leave_balancess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Leave_balancesResponse)
async def get_leave_balances(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single leave_balances by ID"""
    logger.debug(f"Fetching leave_balances with id: {id}, fields={fields}")
    
    service = Leave_balancesService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Leave_balances with id {id} not found")
            raise HTTPException(status_code=404, detail="Leave_balances not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching leave_balances {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Leave_balancesResponse, status_code=201)
async def create_leave_balances(
    data: Leave_balancesData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new leave_balances"""
    logger.debug(f"Creating new leave_balances with data: {data}")
    
    service = Leave_balancesService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create leave_balances")
        
        logger.info(f"Leave_balances created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating leave_balances: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating leave_balances: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Leave_balancesResponse], status_code=201)
async def create_leave_balancess_batch(
    request: Leave_balancesBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple leave_balancess in a single request"""
    logger.debug(f"Batch creating {len(request.items)} leave_balancess")
    
    service = Leave_balancesService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} leave_balancess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Leave_balancesResponse])
async def update_leave_balancess_batch(
    request: Leave_balancesBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple leave_balancess in a single request"""
    logger.debug(f"Batch updating {len(request.items)} leave_balancess")
    
    service = Leave_balancesService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} leave_balancess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Leave_balancesResponse)
async def update_leave_balances(
    id: int,
    data: Leave_balancesUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing leave_balances"""
    logger.debug(f"Updating leave_balances {id} with data: {data}")

    service = Leave_balancesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Leave_balances with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Leave_balances not found")
        
        logger.info(f"Leave_balances {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating leave_balances {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating leave_balances {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_leave_balancess_batch(
    request: Leave_balancesBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple leave_balancess by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} leave_balancess")
    
    service = Leave_balancesService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} leave_balancess successfully")
        return {"message": f"Successfully deleted {deleted_count} leave_balancess", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_leave_balances(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single leave_balances by ID"""
    logger.debug(f"Deleting leave_balances with id: {id}")
    
    service = Leave_balancesService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Leave_balances with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Leave_balances not found")
        
        logger.info(f"Leave_balances {id} deleted successfully")
        return {"message": "Leave_balances deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting leave_balances {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")