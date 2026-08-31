import os
import signal
import time
import subprocess
import re

STATUS_ZOMBIE = 'zombie'

class NoSuchProcess(Exception):
    pass

class Process:
    def __init__(self, pid):
        self.pid = pid
        self._proc = None
        try:
            os.kill(pid, 0)
        except OSError:
            raise NoSuchProcess(f"No process with PID {pid}")

    def children(self, recursive=True):
        return []

    def terminate(self):
        try:
            os.kill(self.pid, signal.SIGTERM)
        except OSError:
            pass

    def wait(self, timeout=None):
        start = time.time()
        while True:
            try:
                os.kill(self.pid, 0)
            except OSError:
                return
            if timeout and time.time() - start > timeout:
                raise subprocess.TimeoutExpired(self.pid, timeout)
            time.sleep(0.1)

    def is_running(self):
        try:
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False

    def status(self):
        try:
            os.kill(self.pid, 0)
            return 'running'
        except OSError:
            return STATUS_ZOMBIE

    def cpu_percent(self, interval=0.1):
        return 0.0

    def memory_info(self):
        class MemInfo:
            rss = 0
        return MemInfo()

    def __repr__(self):
        return f"Process(pid={self.pid})"

def pid_exists(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def wait_procs(procs, timeout=None):
    gone = []
    alive = []
    for p in procs:
        try:
            os.kill(p.pid, 0)
            alive.append(p)
        except OSError:
            gone.append(p)
    return gone, alive

def _read_cgroup_mem():
    try:
        with open('/sys/fs/cgroup/memory/memory.limit_in_bytes') as f:
            limit = int(f.read().strip())
        with open('/sys/fs/cgroup/memory/memory.usage_in_bytes') as f:
            usage = int(f.read().strip())
        return limit, usage
    except:
        try:
            with open('/sys/fs/cgroup/memory.max') as f:
                limit_str = f.read().strip()
            limit = float('inf') if limit_str == 'max' else int(limit_str)
            with open('/sys/fs/cgroup/memory.current') as f:
                usage = int(f.read().strip())
            return limit, usage
        except:
            return None, None

def _read_proc_meminfo():
    try:
        with open('/proc/meminfo') as f:
            data = {}
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    try:
                        data[key] = int(val)
                    except:
                        pass
        total_kb = data.get('MemTotal', 0)
        available_kb = data.get('MemAvailable', data.get('MemFree', 0))
        return total_kb, available_kb
    except:
        return 0, 0

cpu_count = None
def _get_cpu_count():
    global cpu_count
    if cpu_count is not None:
        return cpu_count
    try:
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
    except:
        try:
            cpu_count = len(os.sched_getaffinity(0))
        except:
            try:
                cpu_count = int(subprocess.check_output(['nproc'], timeout=3).strip())
            except:
                cpu_count = 0
    return cpu_count

def cpu_percent(interval=0.5):
    try:
        with open('/proc/stat') as f:
            line = f.readline()
        if not line.startswith('cpu '):
            return 0.0
        vals = [int(x) for x in line.strip().split()[1:]]
        idle = vals[3]
        total = sum(vals)
        time.sleep(interval)
        with open('/proc/stat') as f:
            line = f.readline()
        if not line.startswith('cpu '):
            return 0.0
        vals2 = [int(x) for x in line.strip().split()[1:]]
        idle2 = vals2[3]
        total2 = sum(vals2)
        dtotal = total2 - total
        didle = idle2 - idle
        if dtotal == 0:
            return 0.0
        return round((dtotal - didle) / dtotal * 100, 1)
    except:
        return 0.0

class virtual_memory:
    def __init__(self):
        limit, usage = _read_cgroup_mem()
        if limit is not None and usage is not None:
            self.total = limit if limit != float('inf') else 0
            self.used = usage
            self.available = self.total - self.used if self.total > 0 else 0
        else:
            total_kb, available_kb = _read_proc_meminfo()
            self.total = total_kb * 1024
            self.available = available_kb * 1024
            self.used = self.total - self.available
        self.percent = round((self.used / self.total) * 100, 1) if self.total > 0 else 0
        self.free = self.available

class disk_usage:
    def __init__(self, path='/'):
        try:
            st = os.statvfs(path)
            self.total = st.f_frsize * st.f_blocks
            self.free = st.f_frsize * st.f_bfree
            self.used = self.total - self.free
            if self.total > 100 * (1024**3):
                self.total = self.used + self.free
            self.percent = round((self.used / self.total) * 100, 1) if self.total > 0 else 0
        except:
            self.total = 0
            self.free = 0
            self.used = 0
            self.percent = 0
