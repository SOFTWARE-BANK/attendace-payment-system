"""Stream en vivo de eventos Hikvision (ISAPI alertStream).

Mantiene una conexión HTTP larga contra /ISAPI/Event/notification/alertStream.
El dispositivo empuja cada evento de control de acceso en el instante en que
ocurre; al recibir uno se dispara un sync inmediato de ventana corta
(`sync_events`), que trae los registros completos con deduplicación.

Robustez frente al modo "sordo" del lector (conexión viva pero sin eventos):
- La lectura nunca se bloquea: los disparos de sync van a un worker aparte.
- Timeout de lectura (READ_TIMEOUT_SECONDS): si el lector no manda nada en
  ese lapso se reconecta; al reconectar el dispositivo reenvía su backlog y
  la ventana de sync con deduplicación recupera cualquier evento perdido.
- El loop periódico de `hikvision_sync` queda como red de seguridad, así que
  ninguna checada se pierde aunque el stream se interrumpa.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from services.hikvision_sync import build_hikvision_client, sync_events

logger = logging.getLogger(__name__)

STREAM_PATH = "/ISAPI/Event/notification/alertStream"
SYNC_COOLDOWN_SECONDS = 3.0
SYNC_WINDOW_MINUTES = 10
ACCESS_EVENT_MAJOR = 5  # eventos major=5: verificación de acceso / puerta
READ_TIMEOUT_SECONDS = 120.0  # silencio máximo antes de reconectar el stream


def _segment_json(segment: bytes) -> Optional[Dict[str, Any]]:
    """Extrae el objeto JSON de un segmento multipart (ignora basura)."""
    start = segment.find(b"{")
    end = segment.rfind(b"}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(segment[start : end + 1].decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None


class _MultipartSplitter:
    """Parser incremental de multipart/mixed usando el boundary del header."""

    def __init__(self, content_type: str):
        match = re.search(r"boundary=([^;]+)", content_type or "")
        self._splitter = (b"--" + match.group(1).strip().strip('"').encode()) if match else b"--MIME_boundary"
        self._buffer = b""

    def feed(self, chunk: bytes) -> List[Dict[str, Any]]:
        self._buffer += chunk
        segments = self._buffer.split(self._splitter)
        self._buffer = segments.pop()  # lo que queda es parcial
        return [data for data in (_segment_json(seg) for seg in segments) if data is not None]


def _event_major(data: Dict[str, Any]) -> Optional[int]:
    """Devuelve el major del evento o None si no se puede determinar."""
    ac = data.get("AccessControllerEvent")
    if isinstance(ac, dict):
        try:
            return int(ac.get("majorEventType"))
        except (TypeError, ValueError):
            return None
    return None


async def _sync_window(client: Any, now: datetime) -> None:
    """Sincroniza una ventana corta y registra el resultado."""
    from core.database import db_manager

    try:
        async with db_manager.async_session_maker() as db:
            result = await sync_events(db, client, now - timedelta(minutes=SYNC_WINDOW_MINUTES), now, 100)
        logger.info(
            "Hikvision stream push sync: fetched=%s inserted=%s duplicates=%s skipped=%s",
            result["fetched"],
            result["inserted"],
            result["duplicates"],
            result["skipped"],
        )
    except Exception as exc:
        logger.warning("Hikvision stream push sync failed: %s", exc)


async def stream_events_loop(stop_event: Any) -> None:
    """Consume el alertStream y sincroniza al instante cada evento de acceso.

    La lectura del socket va en el bucle principal y solo "señala" (sync_now)
    cuando llega un evento; el sync lo ejecuta un worker aparte, de modo que
    el socket nunca deja de leerse. La reconexión usa backoff exponencial
    (2s -> 60s) que se reinicia al conectar con éxito.
    """
    from core.config import settings

    try:
        client = build_hikvision_client(settings)
    except ValueError as exc:
        logger.warning("Hikvision alertStream desactivado: %s", exc)
        return

    url = f"{client.base_url}{STREAM_PATH}"
    backoff = 2

    sync_now = asyncio.Event()  # enlace "evento recibido" -> sync

    async def sync_worker() -> None:
        last_sync = datetime(1970, 1, 1, tzinfo=timezone.utc)
        while not stop_event.is_set():
            try:
                await sync_now.wait()
            except asyncio.CancelledError:
                return
            sync_now.clear()
            remaining = SYNC_COOLDOWN_SECONDS - (datetime.now(timezone.utc) - last_sync).total_seconds()
            if remaining > 0:
                await asyncio.sleep(remaining)  # coalesce ráfagas de puerta
            last_sync = datetime.now(timezone.utc)
            await _sync_window(client, last_sync)

    worker = asyncio.create_task(sync_worker())
    try:
        while not stop_event.is_set():
            try:
                async with httpx.AsyncClient(
                    auth=client.auth,
                    # read timeout: el silencio del lector se traduce en reconexión
                    timeout=httpx.Timeout(client.timeout, read=READ_TIMEOUT_SECONDS),
                    verify=client.verify_ssl,
                ) as http:
                    async with http.stream("GET", url) as response:
                        response.raise_for_status()
                        logger.info("Hikvision alertStream conectado (push en tiempo real)")
                        backoff = 2
                        splitter = _MultipartSplitter(response.headers.get("content-type", ""))
                        async for chunk in response.aiter_bytes():
                            for data in splitter.feed(chunk):
                                if _event_major(data) != ACCESS_EVENT_MAJOR:
                                    continue
                                ac = data.get("AccessControllerEvent") or {}
                                logger.info(
                                    "Hikvision stream event: minor=%s serial=%s",
                                    ac.get("subEventType"),
                                    ac.get("serialNo"),
                                )
                                sync_now.set()
            except asyncio.CancelledError:
                logger.info("Hikvision alertStream detenido")
                return
            except httpx.ReadTimeout:
                logger.warning(
                    "Hikvision alertStream sin datos en %ss (lector en silencio); reconectando...",
                    int(READ_TIMEOUT_SECONDS),
                )
            except Exception as exc:
                logger.warning("Hikvision alertStream error: %s (reintentando en %ss)", exc, backoff)

            try:
                # Espera interrumpible antes de reconectar
                await asyncio.wait_for(stop_event.wait(), timeout=backoff)
                return
            except asyncio.TimeoutError:
                backoff = min(backoff * 2, 60)
    finally:
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass
