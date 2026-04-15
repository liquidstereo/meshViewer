import os
import psutil

def get_usable_cpu(reserved_core: int = 2,
                   default_usage: float = 0.80) -> int:
    cpu_count = psutil.cpu_count(logical=False) or 1
    usable_cores = max(1, cpu_count - reserved_core)
    optimal_workers = max(1, int(usable_cores * default_usage))
    return optimal_workers

def get_system_info() -> dict:
    try:
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count(logical=False) or 1

        return {
            'cpu_percent': cpu_percent,
            'cpu_count': cpu_count,
            'memory_percent': memory.percent,
            'memory_total': memory.total,
            'memory_available': memory.available,
            'memory_gb': memory.total / (1024**3),
            'memory_used_gb': memory.used / (1024**3),
            'memory_available_gb': memory.available / (1024**3)
        }

    except (OSError, psutil.Error):
        return {
            'cpu_percent': 0,
            'cpu_count': 1,
            'memory_percent': 0,
            'memory_total': 8 * (1024**3),
            'memory_available': 4 * (1024**3),
            'memory_gb': 8.0,
            'memory_used_gb': 4.0,
            'memory_available_gb': 4.0
        }

def get_gpu_info() -> dict | None:
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp = pynvml.nvmlDeviceGetTemperature(
            handle, pynvml.NVML_TEMPERATURE_GPU
        )
        return {
            'gpu_percent': float(util.gpu),
            'vram_used_gb': mem.used / (1024 ** 3),
            'vram_total_gb': mem.total / (1024 ** 3),
            'vram_percent': mem.used / mem.total * 100,
            'temp_c': temp,
        }
    except Exception:
        return None

def compute_window_size(
    reserved_mb: float,
    system_usage: float,
    est_frame_mb: int = 12,
    min_size: int = 1500,
) -> int:
    total_ram_mb = psutil.virtual_memory().total / (1024 ** 2)
    avail_ram_mb = max(1024, (total_ram_mb - reserved_mb) * system_usage)
    return max(min_size, int(avail_ram_mb / est_frame_mb))

if __name__ == '__main__':
    workers = get_usable_cpu()
    print(f'Default Worker Count: {workers}')

    system_info = get_system_info()
    print(
        f'System Info: CPU {system_info["cpu_percent"]}%, '
        f'Memory {system_info["memory_percent"]}%'
    )
