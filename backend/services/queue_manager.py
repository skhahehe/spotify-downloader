import asyncio
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

@dataclass
class DownloadTask:
    track_id: str
    track_info: dict
    youtube_url: str
    max_attempts: int = 3
    attempts: int = 0
    last_error: str = ""
    manual_url: Optional[str] = None

class QueueManager:
    def __init__(self, download_func: Callable, concurrency: int = 3):
        self.download_func = download_func
        self.concurrency = concurrency
        self.queue = asyncio.Queue()
        self.workers = []
        self.running = False
        self.in_progress = set() # track_id -> bool to prevent duplicates (Issue 4)
        self.active_tasks: Dict[str, asyncio.Task] = {} # track_id -> running Task
        self._loop = None

    async def start(self):
        if self.running: return
        self.running = True
        self._loop = asyncio.get_running_loop()
        self.workers = [asyncio.create_task(self._worker()) for _ in range(self.concurrency)]

    async def stop(self):
        self.running = False
        for w in self.workers:
            w.cancel()
        self.workers = []
        for t in self.active_tasks.values():
            t.cancel()
        self.active_tasks = []

    async def add_task(self, track_id: str, track_info: dict, manual_url: Optional[str] = None):
        if track_id in self.in_progress and not manual_url:
            return
        
        if manual_url:
            # For manual overrides, we allow re-adding even if in_progress
            # and we will handle cancellation from the main.py instead or here
            pass
            
        self.in_progress.add(track_id)
        # Manual overrides only get 1 attempt (Issue 10)
        max_att = 1 if manual_url else 3
        task = DownloadTask(track_id=track_id, track_info=track_info, youtube_url="", manual_url=manual_url, max_attempts=max_att)
        await self.queue.put(task)

    def cancel_task(self, track_id: str):
        """Force-kills the running asyncio task for a specific track_id."""
        if track_id in self.active_tasks:
            print(f"🛑 Killing active download task for {track_id}...")
            self.active_tasks[track_id].cancel()
            self.in_progress.discard(track_id)
            return True
        return False

    async def _worker(self):
        while self.running:
            task: DownloadTask = await self.queue.get()
            try:
                # Wrap the process call so we can cancel it specifically
                p_task = asyncio.create_task(self._process_task(task))
                self.active_tasks[task.track_id] = p_task
                await p_task
            except asyncio.CancelledError:
                print(f"🛑 Worker task for {task.track_id} was cancelled.")
            except Exception as e:
                print(f"Error in worker processing {task.track_id}: {e}")
            finally:
                self.queue.task_done()
                if task:
                    self.in_progress.discard(task.track_id)
                    self.active_tasks.pop(task.track_id, None)

    async def _process_task(self, task: DownloadTask):
        task.attempts += 1
        print(f"🚀 [Worker] Starting {task.track_info['title']} (Attempt {task.attempts}/{task.max_attempts})")
        
        try:
            # Execute download
            success = await self.download_func(task.track_info, manual_url=task.manual_url)
            if success:
                print(f"✅ [Worker] Finished {task.track_info['title']}")
            else:
                raise Exception("Download failed or duration mismatch")
                
        except Exception as e:
            task.last_error = str(e)
            if task.attempts < task.max_attempts:
                # Exponential backoff
                wait_time = 2 ** task.attempts
                print(f"⚠️ [Worker] Failed {task.track_info['title']}: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                await self.queue.put(task)
            else:
                print(f"❌ [Worker] Permanently failed {task.track_info['title']}: {e}")
