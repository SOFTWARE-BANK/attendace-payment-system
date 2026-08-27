import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.approvals import ApprovalsService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/approvals", tags=["approvals"])


# ---------- Pydantic Schemas ----------
class ApprovalsData(BaseModel):
    """Entity data schema (for create/update)"""
    doc_no: str = None
    doc_type: str
    title: str
    target_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    emp_no: str = None
    department: str = None
    requester_emp_no: str = None
    requester_name: str = None
    current_step: str = None
    status: str = None
    hr_approver: str = None
    hr_approved_at: Optional[datetime] = None
    hr_comment: str = None
    manager_approver: str = None
    manager_approved_at: Optional[datetime] = None
    manager_comment: str = None
    ceo_approver: str = None
    ceo_approved_at: Optional[datetime] = None
    ceo_comment: str = None
    rejected_by: str = None
    reject_reason: str = None
    record_count: int = None
    summary: str = None
    payload: str = None


class ApprovalsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    doc_no: Optional[str] = None
    doc_type: Optional[str] = None
    title: Optional[str] = None
    target_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    emp_no: Optional[str] = None
    department: Optional[str] = None
    requester_emp_no: Optional[str] = None
    requester_name: Optional[str] = None
    current_step: Optional[str] = None
    status: Optional[str] = None
    hr_approver: Optional[str] = None
    hr_approved_at: Optional[datetime] = None
    hr_comment: Optional[str] = None
    manager_approver: Optional[str] = None
    manager_approved_at: Optional[datetime] = None
    manager_comment: Optional[str] = None
    ceo_approver: Optional[str] = None
    ceo_approved_at: Optional[datetime] = None
    ceo_comment: Optional[str] = None
    rejected_by: Optional[str] = None
    reject_reason: Optional[str] = None
    record_count: Optional[int] = None
    summary: Optional[str] = None
    payload: Optional[str] = None


class ApprovalsResponse(BaseModel):
    """Entity response schema"""
    id: int
    doc_no: Optional[str] = None
    doc_type: str
    title: str
    target_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    emp_no: Optional[str] = None
    department: Optional[str] = None
    requester_emp_no: Optional[str] = None
    requester_name: Optional[str] = None
    current_step: Optional[str] = None
    status: Optional[str] = None
    hr_approver: Optional[str] = None
    hr_approved_at: Optional[datetime] = None
    hr_comment: Optional[str] = None
    manager_approver: Optional[str] = None
    manager_approved_at: Optional[datetime] = None
    manager_comment: Optional[str] = None
    ceo_approver: Optional[str] = None
    ceo_approved_at: Optional[datetime] = None
    ceo_comment: Optional[str] = None
    rejected_by: Optional[str] = None
    reject_reason: Optional[str] = None
    record_count: Optional[int] = None
    summary: Optional[str] = None
    payload: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApprovalsListResponse(BaseModel):
    """List response schema"""
    items: List[ApprovalsResponse]
    total: int
    skip: int
    limit: int


class ApprovalsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[ApprovalsData]


class ApprovalsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: ApprovalsUpdateData


class ApprovalsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[ApprovalsBatchUpdateItem]


class ApprovalsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=ApprovalsListResponse)
async def query_approvalss(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query approvalss with filtering, sorting, and pagination"""
    logger.debug(f"Querying approvalss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = ApprovalsService(db)
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
        logger.debug(f"Found {result['total']} approvalss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid approvals query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying approvalss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=ApprovalsListResponse)
async def query_approvalss_all(
    query: str = Query(None, description='Query conditions as JSON, e.g. {"id":2} or {"id":{"$gte":2}}'),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query approvalss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying approvalss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = ApprovalsService(db)
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
        logger.debug(f"Found {result['total']} approvalss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid approvals query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying approvalss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=ApprovalsResponse)
async def get_approvals(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single approvals by ID"""
    logger.debug(f"Fetching approvals with id: {id}, fields={fields}")
    
    service = ApprovalsService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Approvals with id {id} not found")
            raise HTTPException(status_code=404, detail="Approvals not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching approvals {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=ApprovalsResponse, status_code=201)
async def create_approvals(
    data: ApprovalsData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new approvals"""
    logger.debug(f"Creating new approvals with data: {data}")
    
    service = ApprovalsService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create approvals")
        
        logger.info(f"Approvals created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating approvals: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating approvals: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[ApprovalsResponse], status_code=201)
async def create_approvalss_batch(
    request: ApprovalsBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple approvalss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} approvalss")
    
    service = ApprovalsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} approvalss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[ApprovalsResponse])
async def update_approvalss_batch(
    request: ApprovalsBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple approvalss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} approvalss")
    
    service = ApprovalsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} approvalss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=ApprovalsResponse)
async def update_approvals(
    id: int,
    data: ApprovalsUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing approvals"""
    logger.debug(f"Updating approvals {id} with data: {data}")

    service = ApprovalsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Approvals with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Approvals not found")
        
        logger.info(f"Approvals {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating approvals {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating approvals {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_approvalss_batch(
    request: ApprovalsBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple approvalss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} approvalss")
    
    service = ApprovalsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} approvalss successfully")
        return {"message": f"Successfully deleted {deleted_count} approvalss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_approvals(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single approvals by ID"""
    logger.debug(f"Deleting approvals with id: {id}")
    
    service = ApprovalsService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Approvals with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Approvals not found")
        
        logger.info(f"Approvals {id} deleted successfully")
        return {"message": "Approvals deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting approvals {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")