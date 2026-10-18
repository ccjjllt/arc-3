"""Bounded Linux sampling. No signals, model calls, network, or source mutation."""
from pathlib import Path
import os
import shutil
import subprocess
import threading
import time


class ResourceObserver:
    def __init__(self, scratch, interval=15):
        self.scratch = Path(scratch)
        self.interval = interval
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.result = {'samples': 0, 'errors': [], 'interval_seconds': interval,
                       'host_available_min_bytes': None, 'scratch_free_min_bytes': None,
                       'gpu_used_peak_bytes': 0, 'gpu_total_bytes': 0,
                       'owned_group_rss_peak_bytes': 0, 'sampled_not_exact_peak': True}
        self.thread = threading.Thread(target=self._loop, daemon=True, name='arc3-resource-observer')

    def _sample(self):
        mem = {a.split(':', 1)[0]: a.split(':', 1)[1].split()[0]
               for a in Path('/proc/meminfo').read_text().splitlines()}
        available = int(mem['MemAvailable']) * 1024
        free = shutil.disk_usage(self.scratch).free
        pgid, rss, deadline = os.getpgrp(), 0, time.monotonic() + 3
        for entry in Path('/proc').iterdir():
            if time.monotonic() >= deadline:
                raise RuntimeError('BOUNDED_PROC_SCAN_EXPIRED')
            if not entry.name.isdigit():
                continue
            try:
                fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
                if int(fields[2]) == pgid:
                    rss += int((entry / 'statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
            except (FileNotFoundError, ProcessLookupError):
                continue
        gpu = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'],
                             check=True, capture_output=True, text=True, timeout=3).stdout.strip().splitlines()
        if len(gpu) != 1:
            raise RuntimeError('EXACTLY_ONE_GPU_REQUIRED')
        used, total = [int(v.strip()) * 1024**2 for v in gpu[0].split(',')]
        with self.lock:
            r = self.result
            r['samples'] += 1
            for key, value in [('host_available_min_bytes', available), ('scratch_free_min_bytes', free)]:
                r[key] = value if r[key] is None else min(value, r[key])
            r['gpu_used_peak_bytes'] = max(r['gpu_used_peak_bytes'], used)
            r['owned_group_rss_peak_bytes'] = max(r['owned_group_rss_peak_bytes'], rss)
            if r['gpu_total_bytes'] not in (0, total):
                raise RuntimeError('GPU_TOTAL_CHANGED')
            r['gpu_total_bytes'] = total

    def _observe(self):
        try:
            self._sample()
        except Exception as error:
            with self.lock:
                # Bounded classifications, no raw paths or private messages.
                key = type(error).__name__
                if key not in self.result['errors'] and len(self.result['errors']) < 16:
                    self.result['errors'].append(key)

    def _loop(self):
        self._observe()
        while not self.stop.wait(self.interval):
            self._observe()

    def start(self):
        self.thread.start()
        return self

    def close(self):
        self.stop.set()
        self.thread.join(timeout=10)
        if self.thread.is_alive():
            raise RuntimeError('RESOURCE_OBSERVER_DID_NOT_STOP')
        self._observe()
        with self.lock:
            return dict(self.result)
