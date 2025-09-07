"""
Performance monitoring utilities
"""

import time
import psutil
import threading
from typing import Dict, Any, Optional
from collections import deque


class PerformanceMonitor:
    """Monitor application performance metrics"""
    
    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self.cpu_history = deque(maxlen=history_size)
        self.memory_history = deque(maxlen=history_size)
        self.latency_history = deque(maxlen=history_size)
        
        self.start_time = time.time()
        self.is_monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self, interval: float = 1.0):
        """Start performance monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval,), 
            daemon=True
        )
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
    
    def _monitor_loop(self, interval: float):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.cpu_history.append(cpu_percent)
                
                # Memory usage
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                self.memory_history.append(memory_mb)
                
                time.sleep(interval)
            except Exception as e:
                print(f"Performance monitoring error: {e}")
                time.sleep(interval)
    
    def add_latency_measurement(self, latency_ms: float):
        """Add a latency measurement"""
        self.latency_history.append(latency_ms)
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        stats = {
            'uptime': uptime,
            'cpu_percent': self.cpu_history[-1] if self.cpu_history else 0.0,
            'memory_mb': self.memory_history[-1] if self.memory_history else 0.0,
            'avg_cpu': sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0.0,
            'avg_memory': sum(self.memory_history) / len(self.memory_history) if self.memory_history else 0.0,
            'max_cpu': max(self.cpu_history) if self.cpu_history else 0.0,
            'max_memory': max(self.memory_history) if self.memory_history else 0.0,
            'avg_latency': sum(self.latency_history) / len(self.latency_history) if self.latency_history else 0.0,
            'max_latency': max(self.latency_history) if self.latency_history else 0.0,
        }
        
        return stats
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                'cpu_count': psutil.cpu_count(),
                'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
                'memory_total': psutil.virtual_memory().total / 1024 / 1024,  # MB
                'memory_available': psutil.virtual_memory().available / 1024 / 1024,  # MB
                'platform': psutil.platform(),
                'python_version': psutil.sys.version,
            }
        except Exception as e:
            return {'error': str(e)}


class LatencyTracker:
    """Track and analyze latency measurements"""
    
    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.measurements = deque(maxlen=window_size)
        self.start_times = {}
    
    def start_timing(self, operation_id: str) -> str:
        """Start timing an operation"""
        timing_id = f"{operation_id}_{time.time()}"
        self.start_times[timing_id] = time.time()
        return timing_id
    
    def end_timing(self, timing_id: str) -> Optional[float]:
        """End timing and record measurement"""
        if timing_id not in self.start_times:
            return None
        
        duration = time.time() - self.start_times[timing_id]
        self.measurements.append(duration)
        del self.start_times[timing_id]
        
        return duration
    
    def get_latency_stats(self) -> Dict[str, float]:
        """Get latency statistics"""
        if not self.measurements:
            return {'count': 0, 'avg': 0.0, 'min': 0.0, 'max': 0.0, 'std': 0.0}
        
        measurements = list(self.measurements)
        avg = sum(measurements) / len(measurements)
        min_val = min(measurements)
        max_val = max(measurements)
        
        # Calculate standard deviation
        variance = sum((x - avg) ** 2 for x in measurements) / len(measurements)
        std = variance ** 0.5
        
        return {
            'count': len(measurements),
            'avg': avg * 1000,  # Convert to milliseconds
            'min': min_val * 1000,
            'max': max_val * 1000,
            'std': std * 1000,
        }


def format_bytes(bytes_value: int) -> str:
    """Format bytes in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.1f}s"
