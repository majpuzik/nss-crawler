#!/usr/bin/env python3
"""
job_manager.py
Správa běžících jobů pro stahování rozhodnutí
"""

import threading
import time
from datetime import datetime
from typing import Dict, Optional

class JobStatus:
    """Status běžícího jobu"""

    def __init__(self, job_id: str, job_type: str, description: str):
        self.job_id = job_id
        self.job_type = job_type
        self.description = description
        self.status = "running"  # running, completed, failed, cancelled
        self.progress = 0
        self.total = 0
        self.current_item = ""
        self.results = []
        self.error = None
        self.started_at = datetime.now()
        self.completed_at = None
        self.cancel_requested = False

    def update(self, progress: int, total: int, current_item: str = ""):
        """Aktualizuj progress"""
        self.progress = progress
        self.total = total
        self.current_item = current_item

    def add_result(self, result):
        """Přidej výsledek"""
        self.results.append(result)

    def complete(self):
        """Označ jako dokončený"""
        self.status = "completed"
        self.completed_at = datetime.now()

    def fail(self, error: str):
        """Označ jako neúspěšný"""
        self.status = "failed"
        self.error = error
        self.completed_at = datetime.now()

    def cancel(self):
        """Označ pro zrušení"""
        self.cancel_requested = True

    def to_dict(self):
        """Konverze na dict pro API"""
        return {
            'job_id': self.job_id,
            'job_type': self.job_type,
            'description': self.description,
            'status': self.status,
            'progress': self.progress,
            'total': self.total,
            'current_item': self.current_item,
            'results_count': len(self.results),
            'error': self.error,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'elapsed_seconds': (datetime.now() - self.started_at).total_seconds()
        }


class JobManager:
    """Správce běžících jobů"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.jobs: Dict[str, JobStatus] = {}
        return cls._instance

    def create_job(self, job_type: str, description: str) -> JobStatus:
        """Vytvoř nový job"""
        job_id = f"{job_type}_{int(time.time())}"
        job = JobStatus(job_id, job_type, description)
        self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[JobStatus]:
        """Získej job podle ID"""
        return self.jobs.get(job_id)

    def get_all_jobs(self):
        """Získej všechny joby"""
        return list(self.jobs.values())

    def get_active_jobs(self):
        """Získej běžící joby"""
        return [j for j in self.jobs.values() if j.status == "running"]

    def cancel_job(self, job_id: str) -> bool:
        """Zruš job"""
        job = self.get_job(job_id)
        if job and job.status == "running":
            job.cancel()
            return True
        return False

    def cleanup_old_jobs(self, max_age_seconds: int = 3600):
        """Vymaž staré dokončené joby"""
        now = datetime.now()
        to_remove = []

        for job_id, job in self.jobs.items():
            if job.status in ["completed", "failed", "cancelled"]:
                if job.completed_at and (now - job.completed_at).total_seconds() > max_age_seconds:
                    to_remove.append(job_id)

        for job_id in to_remove:
            del self.jobs[job_id]

        return len(to_remove)


# Singleton instance
job_manager = JobManager()
