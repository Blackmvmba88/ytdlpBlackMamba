from __future__ import annotations
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import threading
import time
import json

from .jobs import Job, JobStatus, JobMode
from .ytdlp_wrapper import Downloader
from shared.library import identity, existing_media

class DownloadManager:
    def __init__(self, config: Dict[str, Any], logger):
        self.cfg = config
        self.logger = logger
        self.downloader = Downloader(config, logger)
        self.jobs: Dict[str, Job] = {}
        self.pending: List[str] = []
        self.lock = threading.RLock()
        self.workers: List[threading.Thread] = []
        self.running: Dict[str, threading.Event] = {}
        self.stop_event = threading.Event()
        self.history_path = Path(config["history_path"])
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_path.exists():
            self.history_path.write_text("[]", encoding="utf-8")

    def add_job(self, urls: List[str], mode: str) -> Job:
        from shared.security import validate_urls
        clean_urls = validate_urls(urls)
        job = Job(urls=clean_urls, mode=JobMode(mode), total_count=len(clean_urls))
        with self.lock:
            self.jobs = {k: v for k, v in self.jobs.items() if v.status in (JobStatus.running, JobStatus.queued)} | dict(list(self.jobs.items())[-100:])
            requested = {identity(url) for url in clean_urls}
            for previous in self.jobs.values():
                if previous.mode == job.mode and previous.status in (JobStatus.queued, JobStatus.running) and {identity(url) for url in previous.urls} == requested:
                    return previous
            overlap = any(previous.mode == job.mode and previous.status in (JobStatus.queued, JobStatus.running) and requested.intersection(identity(url) for url in previous.urls) for previous in self.jobs.values())
            root = None if overlap else self.cfg.get("download_root")
            paths = [existing_media(root, url, job.mode.value) for url in clean_urls] if root else []
            if paths and all(paths):
                job.output_paths = list(dict.fromkeys(paths))
                job.status = JobStatus.completed
                job.progress = 100
                job.message = "Ya está en tu colección. Listo para reproducir."
                self.jobs[job.id] = job
                return job
            if len(self.pending) >= 100:
                raise ValueError("La cola está llena; espera a que terminen las descargas.")
            self.jobs = {k: v for k, v in self.jobs.items() if v.status in (JobStatus.running, JobStatus.queued)} | dict(list(self.jobs.items())[-100:])
            self.jobs[job.id] = job
            self.pending.append(job.id)
        self.logger.info(f"Añadido trabajo {job.id} ({job.mode}) con {len(clean_urls)} URL(s)")
        return job

    def list_jobs(self) -> List[Job]:
        with self.lock:
            return [job.model_copy(deep=True) for job in self.jobs.values()]

    def get_job(self, job_id: str) -> Optional[Job]:
        with self.lock:
            return self.jobs.get(job_id)

    def start(self) -> None:
        self.stop_event.clear()
        desired = int(self.cfg.get("concurrency", 2))
        with self.lock:
            current = len(self.workers)
        for _ in range(desired - current):
            t = threading.Thread(target=self._worker_loop, daemon=True)
            t.start()
            with self.lock:
                self.workers.append(t)
        self.logger.info(f"Gestor iniciado con {len(self.workers)} hilos")

    def cancel(self, job_id: str) -> bool:
        with self.lock:
            if job_id in self.pending:
                self.pending = [j for j in self.pending if j != job_id]
                job = self.jobs.get(job_id)
                if job:
                    job.status = JobStatus.canceled
                    job.message = "Cancelado antes de iniciar"
                    self._persist_history_entry(job)
                return True
            ev = self.running.get(job_id)
            if ev:
                ev.set()
                return True
        return False

    def _next_job(self) -> Optional[Job]:
        with self.lock:
            job_id = self.pending.pop(0) if self.pending else None
            if not job_id:
                return None
            job = self.jobs.get(job_id)
            if not job:
                return None
            job.status = JobStatus.running
            job.progress = 0.0
            job.current_index = 0
            cancel_ev = threading.Event()
            self.running[job.id] = cancel_ev
            return job

    def _finish_job(self, job: Job) -> None:
        with self.lock:
            self.running.pop(job.id, None)
        self._persist_history_entry(job)

    def _worker_loop(self) -> None:
        while not self.stop_event.is_set():
            job = self._next_job()
            if not job:
                time.sleep(0.2)
                continue
            cancel_ev = None
            with self.lock:
                cancel_ev = self.running.get(job.id)

            def on_event(d: Dict[str, Any]):
                try:
                    status = d.get("status")
                    filename = d.get("filename") or (d.get("info_dict") or {}).get("filepath")
                    with self.lock:
                        if job.id not in self.jobs:
                            return
                        if filename:
                            job.current = str(filename)
                        if status == "downloading":
                            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                            downloaded = d.get("downloaded_bytes") or 0
                            pct = float(downloaded) / float(total) * 100.0 if total else 0.0
                            if job.total_count:
                                overall = ((job.current_index) * 100.0 + pct) / float(job.total_count)
                            else:
                                overall = pct
                            job.progress = min(100.0, overall)
                        elif status in ("finished", "post_process", "processing"):
                            pass
                except Exception as e:
                    self.logger.error(f"Error actualizando progreso: {e}")

            try:
                outputs = self.downloader.download(job, on_event, cancel_ev)
                with self.lock:
                    job.output_paths = outputs or job.output_paths
                    job.progress = 100.0
                    job.status = JobStatus.canceled if cancel_ev.is_set() else JobStatus.completed
                    job.message = "Cancelado" if cancel_ev.is_set() else "OK"
            except Exception as e:
                with self.lock:
                    if cancel_ev.is_set():
                        job.status = JobStatus.canceled
                        job.message = "Cancelado"
                    else:
                        job.status = JobStatus.error
                        job.message = str(e)
                    job.progress = job.progress or 0.0
            finally:
                self._finish_job(job)

    def _persist_history_entry(self, job: Job) -> None:
        try:
            item = {
                "id": job.id,
                "mode": job.mode.value if hasattr(job.mode, "value") else str(job.mode),
                "urls": job.urls,
                "status": job.status.value if hasattr(job.status, "value") else str(job.status),
                "message": job.message,
                "output_paths": job.output_paths,
                "created_at": job.created_at.isoformat() + "Z",
                "finished_at": datetime.utcnow().isoformat() + "Z",
            }
            with self.lock:
                data = []
                if self.history_path.exists():
                    with open(self.history_path, "r", encoding="utf-8") as f:
                        try:
                            data = json.load(f) or []
                        except Exception:
                            data = []
                data.append(item)
                temporary = self.history_path.with_suffix(".tmp")
                temporary.write_text(json.dumps(data[-1000:], ensure_ascii=False, indent=2), encoding="utf-8")
                temporary.replace(self.history_path)
        except Exception as e:
            self.logger.error(f"No se pudo persistir historial: {e}")

    def get_history(self) -> List[Dict[str, Any]]:
        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                return json.load(f) or []
        except Exception:
            return []
