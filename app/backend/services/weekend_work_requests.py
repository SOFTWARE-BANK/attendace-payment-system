import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID as PythonUUID

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Boolean, Date, DateTime, Float, Integer, Numeric

from models.weekend_work_requests import Weekend_work_requests

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Weekend_work_requestsService:
    """Service layer for Weekend_work_requests operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _invalid_field_value(field_name: str, value: Any) -> ValueError:
        return ValueError("Invalid value for field " + field_name + ": " + repr(value))

    @classmethod
    def _is_json_field(cls, column: Any) -> bool:
        try:
            column_type = column.property.columns[0].type
        except (AttributeError, IndexError):
            return False
        return column_type.__class__.__name__ in {"JSON", "JSONB"}

    @classmethod
    def _coerce_field_value(cls, column: Any, value: Any, field_name: str) -> Any:
        try:
            column_type = column.property.columns[0].type
        except (AttributeError, IndexError):
            return value

        if value is None:
            return value

        if isinstance(column_type, DateTime) and isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(normalized)
            except ValueError:
                try:
                    parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    raise cls._invalid_field_value(field_name, value)
            if not getattr(column_type, "timezone", False) and parsed.tzinfo is not None:
                parsed = parsed.replace(tzinfo=None)
            return parsed

        if isinstance(column_type, Date):
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                try:
                    return date.fromisoformat(value)
                except ValueError:
                    try:
                        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
                    except ValueError:
                        raise cls._invalid_field_value(field_name, value)

        if isinstance(column_type, Boolean) and isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "t", "yes", "y", "on"}:
                return True
            if normalized in {"false", "0", "f", "no", "n", "off"}:
                return False
            raise cls._invalid_field_value(field_name, value)

        if isinstance(column_type, Integer) and isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                raise cls._invalid_field_value(field_name, value)

        if isinstance(column_type, Float) and isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                raise cls._invalid_field_value(field_name, value)

        if isinstance(column_type, Numeric) and isinstance(value, str):
            try:
                return Decimal(value)
            except ArithmeticError:
                raise cls._invalid_field_value(field_name, value)

        if isinstance(column_type, PG_UUID) and isinstance(value, str) and getattr(column_type, "as_uuid", False):
            try:
                return PythonUUID(value)
            except ValueError:
                raise cls._invalid_field_value(field_name, value)

        return value

    @classmethod
    def _build_query_conditions(cls, column: Any, raw_value: Any, field_name: str) -> List[Any]:
        operator_map = {
            "$eq": lambda col, value: col == value,
            "$gte": lambda col, value: col >= value,
            "$lte": lambda col, value: col <= value,
            "$gt": lambda col, value: col > value,
            "$lt": lambda col, value: col < value,
        }

        if isinstance(raw_value, dict):
            has_operator_key = any(isinstance(operator, str) and operator.startswith("$") for operator in raw_value)
            if not has_operator_key:
                if cls._is_json_field(column):
                    coerced_value = cls._coerce_field_value(column, raw_value, field_name)
                    return [column == coerced_value]
                operator_names = {operator[1:] for operator in operator_map}
                matching_operator = next(
                    (
                        operator for operator in raw_value
                        if isinstance(operator, str) and operator.lower() in operator_names
                    ),
                    None,
                )
                if matching_operator is not None:
                    raise ValueError(
                        "Invalid query operator format for field "
                        + field_name
                        + ": "
                        + matching_operator
                        + ". Use $"
                        + matching_operator.lower()
                        + " instead."
                    )
                raise cls._invalid_field_value(field_name, raw_value)
            invalid_operator_keys = [
                operator for operator in raw_value
                if not isinstance(operator, str) or not operator.startswith("$")
            ]
            if invalid_operator_keys:
                raise ValueError("Cannot mix query operators and literal object values for field " + field_name)
            conditions = []
            for operator, value in raw_value.items():
                normalized_operator = operator.lower()
                if normalized_operator not in operator_map:
                    raise ValueError("Unsupported query operator " + operator + " for field " + field_name)
                coerced_value = cls._coerce_field_value(column, value, field_name)
                conditions.append(operator_map[normalized_operator](column, coerced_value))
            return conditions

        coerced_value = cls._coerce_field_value(column, raw_value, field_name)
        return [column == coerced_value]

    async def create(self, data: Dict[str, Any]) -> Optional[Weekend_work_requests]:
        """Create a new weekend_work_requests"""
        try:
            obj = Weekend_work_requests(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created weekend_work_requests with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating weekend_work_requests: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Weekend_work_requests]:
        """Get weekend_work_requests by ID"""
        try:
            query = select(Weekend_work_requests).where(Weekend_work_requests.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching weekend_work_requests {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of weekend_work_requestss"""
        try:
            # Collect filter conditions once and reuse them for both the windowed
            # page query and the empty-page fallback count, so a list call costs a
            # single DB round-trip in the common (non-empty) case.
            conditions = []
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Weekend_work_requests, field):
                        column = getattr(Weekend_work_requests, field)
                        for condition in self._build_query_conditions(column, value, field):
                            conditions.append(condition)

            # func.count().over() returns the full filtered total alongside each
            # row. SQL evaluates window functions before LIMIT/OFFSET, so the
            # total reflects all matching rows, not just the current page.
            stmt = select(Weekend_work_requests, func.count().over().label("total_count"))
            for condition in conditions:
                stmt = stmt.where(condition)

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Weekend_work_requests, field_name):
                        stmt = stmt.order_by(getattr(Weekend_work_requests, field_name).desc())
                else:
                    if hasattr(Weekend_work_requests, sort):
                        stmt = stmt.order_by(getattr(Weekend_work_requests, sort))
            else:
                stmt = stmt.order_by(Weekend_work_requests.id.desc())

            result = await self.db.execute(stmt.offset(skip).limit(limit))
            rows = result.all()

            if rows:
                items = [row[0] for row in rows]
                total = rows[0][1]
            else:
                # Empty page (e.g. skip beyond the end): the window query returns
                # no rows, so fall back to a dedicated count with the same filters.
                items = []
                count_stmt = select(func.count()).select_from(Weekend_work_requests)
                for condition in conditions:
                    count_stmt = count_stmt.where(condition)
                total = (await self.db.execute(count_stmt)).scalar() or 0

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching weekend_work_requests list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any]) -> Optional[Weekend_work_requests]:
        """Update weekend_work_requests"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Weekend_work_requests {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated weekend_work_requests {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating weekend_work_requests {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete weekend_work_requests"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Weekend_work_requests {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted weekend_work_requests {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting weekend_work_requests {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Weekend_work_requests]:
        """Get weekend_work_requests by any field"""
        try:
            if not hasattr(Weekend_work_requests, field_name):
                raise ValueError(f"Field {field_name} does not exist on Weekend_work_requests")
            column = getattr(Weekend_work_requests, field_name)
            field_value = self._coerce_field_value(column, field_value, field_name)
            result = await self.db.execute(
                select(Weekend_work_requests).where(column == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching weekend_work_requests by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Weekend_work_requests]:
        """Get list of weekend_work_requestss filtered by field"""
        try:
            if not hasattr(Weekend_work_requests, field_name):
                raise ValueError(f"Field {field_name} does not exist on Weekend_work_requests")
            column = getattr(Weekend_work_requests, field_name)
            field_value = self._coerce_field_value(column, field_value, field_name)
            result = await self.db.execute(
                select(Weekend_work_requests)
                .where(column == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Weekend_work_requests.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching weekend_work_requestss by {field_name}: {str(e)}")
            raise