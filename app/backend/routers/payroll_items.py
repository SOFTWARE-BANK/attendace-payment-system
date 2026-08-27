import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.payroll_items import Payroll_itemsService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/payroll_items", tags=["payroll_items"])


# ---------- Pydantic Schemas ----------
class Payroll_itemsData(BaseModel):
    """Entity data schema (for create/update)"""
    payroll_run_id: int = None
    emp_no: str
    employee_name: str = None
    department: str = None
    pay_cycle: str = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    regular_minutes: int = None
    overtime_minutes: int = None
    holiday_minutes: int = None
    night_minutes: int = None
    late_minutes: int = None
    offset_minutes: int = None
    absent_days: float = None
    leave_days: float = None
    work_days: int = None
    confirmed_days: int = None
    base_pay: float = None
    overtime_pay: float = None
    holiday_pay: float = None
    night_pay: float = None
    late_deduction: float = None
    offset_credit: float = None
    absent_deduction: float = None
    gross_pay: float = None
    net_pay: float = None


class Payroll_itemsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    payroll_run_id: Optional[int] = None
    emp_no: Optional[str] = None
    employee_name: Optional[str] = None
    department: Optional[str] = None
    pay_cycle: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    regular_minutes: Optional[int] = None
    overtime_minutes: Optional[int] = None
    holiday_minutes: Optional[int] = None
    night_minutes: Optional[int] = None
    late_minutes: Optional[int] = None
    offset_minutes: Optional[int] = None
    absent_days: Optional[float] = None
    leave_days: Optional[float] = None
    work_days: Optional[int] = None
    confirmed_days: Optional[int] = None
    base_pay: Optional[float] = None
    overtime_pay: Optional[float] = None
    holiday_pay: Optional[float] = None
    night_pay: Optional[float] = None
    late_deduction: Optional[float] = None
    offset_credit: Optional[float] = None
    absent_deduction: Optional[float] = None
    gross_pay: Optional[float] = None
    net_pay: Optional[float] = None


class Payroll_itemsResponse(BaseModel):
    """Entity response schema"""
    id: int
    payroll_run_id: Optional[int] = None
    emp_no: str
    employee_name: Optional[str] = None
    department: Optional[str] = None
    pay_cycle: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    regular_minutes: Optional[int] = None
    overtime_minutes: Optional[int] = None
    holiday_minutes: Optional[int] = None
    night_minutes: Optional[int] = None
    late_minutes: Optional[int] = None
    offset_minutes: Optional[int] = None
    absent_days: Optional[float] = None
    leave_days: Optional[float] = None
    work_days: Optional[int] = None
    confirmed_days: Optional[int] = None
    base_pay: Optional[float] = None
    overtime_pay: Optional[float] = None
    holiday_pay: Optional[float] = None
    night_pay: Optional[float] = None
    late_deduction: Optional[float] = None
    offset_credit: Optional[float] = None
    absent_deduction: Optional[float] = None
    gross_pay: Optional[float] = None
    net_pay: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Payroll_itemsListResponse(BaseModel):
    """List response schema"""
    items: List[Payroll_itemsResponse]
    total: int
    skip: int
    limit: int


class Payroll_itemsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Payroll_itemsData]


class Payroll_itemsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Payroll_itemsUpdateData


class Payroll_itemsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Payroll_itemsBatchUpdateItem]


class Payroll_itemsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Payroll_itemsListResponse)
async def query_payroll_itemss(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query payroll_itemss with filtering, sorting, and pagination"""
    logger.debug(f"Querying payroll_itemss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Payroll_itemsService(db)
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
        logger.debug(f"Found {result['total']} payroll_itemss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid payroll_items query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying payroll_itemss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Payroll_itemsListResponse)
async def query_payroll_itemss_all(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query payroll_itemss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying payroll_itemss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Payroll_itemsService(db)
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
        logger.debug(f"Found {result['total']} payroll_itemss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid payroll_items query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying payroll_itemss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Payroll_itemsResponse)
async def get_payroll_items(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single payroll_items by ID"""
    logger.debug(f"Fetching payroll_items with id: {id}, fields={fields}")
    
    service = Payroll_itemsService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Payroll_items with id {id} not found")
            raise HTTPException(status_code=404, detail="Payroll_items not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching payroll_items {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Payroll_itemsResponse, status_code=201)
async def create_payroll_items(
    data: Payroll_itemsData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new payroll_items"""
    logger.debug(f"Creating new payroll_items with data: {data}")
    
    service = Payroll_itemsService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create payroll_items")
        
        logger.info(f"Payroll_items created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating payroll_items: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating payroll_items: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Payroll_itemsResponse], status_code=201)
async def create_payroll_itemss_batch(
    request: Payroll_itemsBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple payroll_itemss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} payroll_itemss")
    
    service = Payroll_itemsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} payroll_itemss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Payroll_itemsResponse])
async def update_payroll_itemss_batch(
    request: Payroll_itemsBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple payroll_itemss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} payroll_itemss")
    
    service = Payroll_itemsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} payroll_itemss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Payroll_itemsResponse)
async def update_payroll_items(
    id: int,
    data: Payroll_itemsUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing payroll_items"""
    logger.debug(f"Updating payroll_items {id} with data: {data}")

    service = Payroll_itemsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Payroll_items with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Payroll_items not found")
        
        logger.info(f"Payroll_items {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating payroll_items {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating payroll_items {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_payroll_itemss_batch(
    request: Payroll_itemsBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple payroll_itemss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} payroll_itemss")
    
    service = Payroll_itemsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} payroll_itemss successfully")
        return {"message": f"Successfully deleted {deleted_count} payroll_itemss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_payroll_items(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single payroll_items by ID"""
    logger.debug(f"Deleting payroll_items with id: {id}")
    
    service = Payroll_itemsService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Payroll_items with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Payroll_items not found")
        
        logger.info(f"Payroll_items {id} deleted successfully")
        return {"message": "Payroll_items deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting payroll_items {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")