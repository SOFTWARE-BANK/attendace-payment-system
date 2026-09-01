"""Cliente ISAPI para terminales de control de acceso Hikvision."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import httpx

logger = logging.getLogger(__name__)


class HikvisionConfigurationError(ValueError):
    """Raised when Hikvision connection settings are incomplete."""


class HikvisionClient:
    """Read access-control events from a Hikvision ISAPI terminal."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 80,
        use_https: bool = False,
        timeout: float = 30.0,
        verify_ssl: bool = False,
        timezone_name: str = "America/Mexico_City",
    ):
        if not host or not username or not password:
            raise HikvisionConfigurationError(
                "HIKVISION_HOST, HIKVISION_USERNAME y HIKVISION_PASSWORD son obligatorios"
            )
        scheme = "https" if use_https else "http"
        self.base_url = f"{scheme}://{host}:{port}"
        self.auth = httpx.DigestAuth(username, password)
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        try:
            self.device_timezone = ZoneInfo(timezone_name)
        except Exception as exc:
            raise ValueError(f"Zona horaria Hikvision invalida: {timezone_name}") from exc

    async def get_device_info(self) -> Dict[str, Any]:
        """Return device information from the public ISAPI device endpoint."""
        response = await self._request("GET", "/ISAPI/System/deviceInfo")
        return self._parse_object(response)

    async def fetch_events(
        self,
        start_time: datetime,
        end_time: datetime,
        page_size: int = 100,
        max_pages: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fetch events in a time range using Hikvision's event-search API."""
        if end_time <= start_time:
            raise ValueError("end_time debe ser posterior a start_time")
        if page_size < 1 or page_size > 1000:
            raise ValueError("page_size debe estar entre 1 y 1000")

        events: List[Dict[str, Any]] = []
        for page in range(max_pages):
            position = page * page_size
            request_body = self._event_search_body(start_time, end_time, position, page_size, self.device_timezone)
            response = await self._request(
                "POST",
                "/ISAPI/AccessControl/AcsEvent?format=json",
                json=request_body,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            parsed = self._parse_events(response)
            events.extend(parsed)
            if len(parsed) < page_size:
                break
        return events

    async def get_user_info(self, employee_no: str) -> Optional[Dict[str, Any]]:
        """Devuelve el UserInfo del directorio del terminal para un employeeNo."""
        if not employee_no:
            return None
        request_body = {
            "UserInfoSearchCond": {
                "searchID": str(uuid.uuid4()),
                "searchResultPosition": 0,
                "maxResults": 5,
                "EmployeeNoList": [{"employeeNo": str(employee_no)}],
            }
        }
        response = await self._request(
            "POST",
            "/ISAPI/AccessControl/UserInfo/Search?format=json",
            json=request_body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        return self._first_user_info(self._parse_object(response))

    @staticmethod
    def _first_user_info(data: Any) -> Optional[Dict[str, Any]]:
        """Busca el primer UserInfo de la respuesta (JSON o XML)."""

        def find(value: Any) -> Optional[Dict[str, Any]]:
            if isinstance(value, dict):
                if value.get("employeeNo") is not None or value.get("employeeNoString") is not None:
                    return value
                search = value.get("UserInfoSearch")
                if isinstance(search, dict):
                    found = find(search)
                    if found:
                        return found
                info = value.get("UserInfo")
                if isinstance(info, list):
                    for item in info:
                        found = find(item)
                        if found:
                            return found
                for child in value.values():
                    found = find(child)
                    if found:
                        return found
            if isinstance(value, list):
                for item in value:
                    found = find(item)
                    if found:
                        return found
            return None

        return find(data)

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                auth=self.auth,
                timeout=self.timeout,
                verify=self.verify_ssl,
            ) as client:
                response = await client.request(method, f"{self.base_url}{path}", **kwargs)
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500].replace("\n", " ")
            logger.warning("Hikvision ISAPI respondio con HTTP %s: %s", exc.response.status_code, detail)
            raise ConnectionError(f"Hikvision devolvio HTTP {exc.response.status_code}: {detail}") from exc
        except httpx.HTTPError as exc:
            raise ConnectionError(f"No se pudo conectar con Hikvision: {exc}") from exc

    @staticmethod
    def _event_search_body(
        start_time: datetime,
        end_time: datetime,
        position: int,
        page_size: int,
        device_timezone: ZoneInfo,
    ) -> Dict[str, Any]:
        start = HikvisionClient._format_device_time(start_time, device_timezone)
        end = HikvisionClient._format_device_time(end_time, device_timezone)
        return {
            "AcsEventCond": {
                "searchID": str(uuid.uuid4()),
                "searchResultPosition": position,
                "maxResults": page_size,
                "major": 5,
                "minor": 0,
                "startTime": start,
                "endTime": end,
            }
        }

    @staticmethod
    def _format_device_time(value: datetime, device_timezone: ZoneInfo = ZoneInfo("America/Mexico_City")) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=device_timezone)
        formatted = value.astimezone(device_timezone).strftime("%Y-%m-%dT%H:%M:%S%z")
        return f"{formatted[:-2]}:{formatted[-2:]}"

    @staticmethod
    def _parse_object(response: httpx.Response) -> Dict[str, Any]:
        if "json" in response.headers.get("content-type", "").lower():
            data = response.json()
            return data if isinstance(data, dict) else {"data": data}
        root = ElementTree.fromstring(response.text)
        return {HikvisionClient._local_name(root.tag): HikvisionClient._xml_to_value(root)}

    @staticmethod
    def _parse_events(response: httpx.Response) -> List[Dict[str, Any]]:
        if "json" in response.headers.get("content-type", "").lower():
            data = response.json()
            return HikvisionClient._events_from_json(data)
        root = ElementTree.fromstring(response.text)
        event_nodes = [node for node in root.iter() if HikvisionClient._local_name(node.tag).lower() == "event"]
        return [HikvisionClient._event_from_xml(node) for node in event_nodes]

    @staticmethod
    def _events_from_json(data: Any) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return [HikvisionClient._normalize_event(item) for item in data if isinstance(item, dict)]
        if not isinstance(data, dict):
            return []
        for key in ("InfoList", "infoList", "events", "Events"):
            value = data.get(key)
            if isinstance(value, list):
                return [HikvisionClient._normalize_event(item) for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                return HikvisionClient._events_from_json(value)
        for value in data.values():
            if isinstance(value, (dict, list)):
                events = HikvisionClient._events_from_json(value)
                if events:
                    return events
        return []

    @staticmethod
    def _event_from_xml(node: ElementTree.Element) -> Dict[str, Any]:
        values: Dict[str, Any] = {}
        for child in node.iter():
            if child is node:
                continue
            name = HikvisionClient._local_name(child.tag)
            if child.text and not list(child):
                values[name] = child.text.strip()
        return HikvisionClient._normalize_event(values)

    @staticmethod
    def _normalize_event(value: Dict[str, Any]) -> Dict[str, Any]:
        employee_no = HikvisionClient._first(value, "employeeNoString", "employeeNo", "userId", "emp_no")
        event_time = HikvisionClient._first(value, "time", "eventTime", "event_time")
        event_type = HikvisionClient._event_type(value)
        auth_mode = HikvisionClient._first(value, "currentVerifyMode", "verifyMode", "auth_mode") or "face"
        return {
            "employeeNo": str(employee_no or "").strip(),
            "event_time": event_time,
            "event_type": event_type,
            "auth_mode": str(auth_mode).lower(),
            "terminal_id": HikvisionClient._first(value, "deviceID", "deviceId", "terminal_id"),
            "device_name": HikvisionClient._first(value, "deviceName", "device_name"),
            "raw_payload": json.dumps(value, ensure_ascii=False, default=str),
        }

    @staticmethod
    def _event_type(value: Dict[str, Any]) -> str:
        raw = str(HikvisionClient._first(value, "attendanceStatus", "eventType", "event_type") or "").lower()
        if any(token in raw for token in ("checkout", "check_out", "out", "leave")):
            return "OUT"
        if any(token in raw for token in ("checkin", "check_in", "in", "enter")):
            return "IN"
        return "ACCESS"

    @staticmethod
    def _first(value: Dict[str, Any], *keys: str) -> Optional[Any]:
        for key in keys:
            if value.get(key) not in (None, ""):
                return value[key]
        return None

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    @staticmethod
    def _xml_to_value(node: ElementTree.Element) -> Any:
        children = list(node)
        if not children:
            return (node.text or "").strip()
        result: Dict[str, Any] = {}
        for child in children:
            key = HikvisionClient._local_name(child.tag)
            value = HikvisionClient._xml_to_value(child)
            if key in result:
                if not isinstance(result[key], list):
                    result[key] = [result[key]]
                result[key].append(value)
            else:
                result[key] = value
        return result
