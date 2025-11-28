"""
Metrics collection and monitoring for the AST server.

Provides lightweight metrics tracking for:
- Event processing performance
- UDP listener health
- WebSocket broadcast metrics
- Cache effectiveness
- Error rates
- System health

Metrics can be exported for monitoring dashboards or used for real-time alerting.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class TimingStats:
    """Statistics for timing metrics."""
    count: int = 0
    total: float = 0.0
    min: float = float('inf')
    max: float = 0.0
    recent: deque = field(default_factory=lambda: deque(maxlen=100))

    def record(self, value: float) -> None:
        """Record a timing value."""
        self.count += 1
        self.total += value
        self.min = min(self.min, value)
        self.max = max(self.max, value)
        self.recent.append(value)

    @property
    def mean(self) -> float:
        """Calculate mean value."""
        return self.total / self.count if self.count > 0 else 0.0

    @property
    def p50(self) -> float:
        """Calculate 50th percentile (median)."""
        if not self.recent:
            return 0.0
        sorted_values = sorted(self.recent)
        return sorted_values[len(sorted_values) // 2]

    @property
    def p95(self) -> float:
        """Calculate 95th percentile."""
        if not self.recent:
            return 0.0
        sorted_values = sorted(self.recent)
        idx = int(len(sorted_values) * 0.95)
        return sorted_values[idx] if idx < len(sorted_values) else sorted_values[-1]

    @property
    def p99(self) -> float:
        """Calculate 99th percentile."""
        if not self.recent:
            return 0.0
        sorted_values = sorted(self.recent)
        idx = int(len(sorted_values) * 0.99)
        return sorted_values[idx] if idx < len(sorted_values) else sorted_values[-1]

    def to_dict(self) -> Dict[str, Any]:
        """Export statistics as dictionary."""
        return {
            'count': self.count,
            'mean': round(self.mean, 6),
            'min': round(self.min, 6) if self.min != float('inf') else 0.0,
            'max': round(self.max, 6),
            'p50': round(self.p50, 6),
            'p95': round(self.p95, 6),
            'p99': round(self.p99, 6),
        }


@dataclass
class CounterStats:
    """Statistics for counter metrics."""
    value: int = 0

    def increment(self, amount: int = 1) -> None:
        """Increment counter."""
        self.value += amount

    def decrement(self, amount: int = 1) -> None:
        """Decrement counter."""
        self.value -= amount

    def reset(self) -> None:
        """Reset counter to zero."""
        self.value = 0

    def to_dict(self) -> Dict[str, Any]:
        """Export statistics as dictionary."""
        return {'value': self.value}


@dataclass
class GaugeStats:
    """Statistics for gauge metrics."""
    value: float = 0.0
    min: float = float('inf')
    max: float = 0.0
    recent: deque = field(default_factory=lambda: deque(maxlen=100))

    def set(self, value: float) -> None:
        """Set gauge value."""
        self.value = value
        self.min = min(self.min, value)
        self.max = max(self.max, value)
        self.recent.append(value)

    @property
    def mean(self) -> float:
        """Calculate mean of recent values."""
        return sum(self.recent) / len(self.recent) if self.recent else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Export statistics as dictionary."""
        return {
            'current': round(self.value, 6),
            'min': round(self.min, 6) if self.min != float('inf') else 0.0,
            'max': round(self.max, 6),
            'mean': round(self.mean, 6),
        }


class MetricsCollector:
    """
    Lightweight metrics collector for AST server monitoring.

    Tracks three types of metrics:
    - Timings: Duration measurements (e.g., event processing time)
    - Counters: Incrementing values (e.g., events processed)
    - Gauges: Point-in-time values (e.g., connected clients)

    Usage:
        metrics = MetricsCollector()

        # Timing
        with metrics.timer('event.processing'):
            process_event()

        # Or manually
        start = time.time()
        process_event()
        metrics.timing('event.processing', time.time() - start)

        # Counter
        metrics.increment('events.processed')
        metrics.increment('events.dropped', amount=5)

        # Gauge
        metrics.gauge('websocket.clients', 3)

        # Export
        stats = metrics.get_all_metrics()
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize metrics collector.

        Args:
            enabled: Whether metrics collection is enabled (default: True)
        """
        self.enabled = enabled
        self._lock = Lock()

        # Metric storage
        self._timings: Dict[str, TimingStats] = defaultdict(TimingStats)
        self._counters: Dict[str, CounterStats] = defaultdict(CounterStats)
        self._gauges: Dict[str, GaugeStats] = defaultdict(GaugeStats)

        # Start time for uptime
        self._start_time = time.time()

        logger.debug(f"MetricsCollector initialized: enabled={enabled}")

    def timing(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a timing metric.

        Args:
            name: Metric name (e.g., 'event.processing.duration')
            value: Duration in seconds
            tags: Optional tags for metric categorization
        """
        if not self.enabled:
            return

        metric_key = self._build_key(name, tags)

        with self._lock:
            self._timings[metric_key].record(value)

        logger.debug(f"Timing recorded: {metric_key} = {value:.6f}s")

    def increment(self, name: str, amount: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.

        Args:
            name: Metric name (e.g., 'events.processed')
            amount: Amount to increment (default: 1)
            tags: Optional tags for metric categorization
        """
        if not self.enabled:
            return

        metric_key = self._build_key(name, tags)

        with self._lock:
            self._counters[metric_key].increment(amount)

        logger.debug(f"Counter incremented: {metric_key} += {amount}")

    def decrement(self, name: str, amount: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Decrement a counter metric.

        Args:
            name: Metric name
            amount: Amount to decrement (default: 1)
            tags: Optional tags for metric categorization
        """
        if not self.enabled:
            return

        metric_key = self._build_key(name, tags)

        with self._lock:
            self._counters[metric_key].decrement(amount)

    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge metric.

        Args:
            name: Metric name (e.g., 'websocket.clients.connected')
            value: Current value
            tags: Optional tags for metric categorization
        """
        if not self.enabled:
            return

        metric_key = self._build_key(name, tags)

        with self._lock:
            self._gauges[metric_key].set(value)

        logger.debug(f"Gauge set: {metric_key} = {value}")

    def timer(self, name: str, tags: Optional[Dict[str, str]] = None) -> 'TimerContext':
        """
        Create a context manager for timing code blocks.

        Args:
            name: Metric name
            tags: Optional tags for metric categorization

        Returns:
            TimerContext for use with 'with' statement

        Usage:
            with metrics.timer('event.processing'):
                process_event()
        """
        return TimerContext(self, name, tags)

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all collected metrics.

        Returns:
            Dictionary containing all metrics organized by type
        """
        with self._lock:
            return {
                'timings': {k: v.to_dict() for k, v in self._timings.items()},
                'counters': {k: v.to_dict() for k, v in self._counters.items()},
                'gauges': {k: v.to_dict() for k, v in self._gauges.items()},
                'uptime_seconds': time.time() - self._start_time,
            }

    def get_timing(self, name: str, tags: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Get specific timing metric."""
        metric_key = self._build_key(name, tags)
        with self._lock:
            stats = self._timings.get(metric_key)
            return stats.to_dict() if stats else None

    def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Get specific counter metric."""
        metric_key = self._build_key(name, tags)
        with self._lock:
            stats = self._counters.get(metric_key)
            return stats.to_dict() if stats else None

    def get_gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Get specific gauge metric."""
        metric_key = self._build_key(name, tags)
        with self._lock:
            stats = self._gauges.get(metric_key)
            return stats.to_dict() if stats else None

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._timings.clear()
            self._counters.clear()
            self._gauges.clear()
            self._start_time = time.time()
        logger.debug("All metrics reset")

    def reset_counters(self) -> None:
        """Reset only counter metrics."""
        with self._lock:
            for counter in self._counters.values():
                counter.reset()
        logger.debug("Counters reset")

    @staticmethod
    def _build_key(name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """
        Build metric key from name and tags.

        Args:
            name: Metric name
            tags: Optional tags

        Returns:
            Metric key string
        """
        if not tags:
            return name

        # Sort tags for consistent key generation
        tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"


class TimerContext:
    """Context manager for timing code blocks."""

    def __init__(self, collector: MetricsCollector, name: str, tags: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.name = name
        self.tags = tags
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.collector.timing(self.name, duration, self.tags)
        return False


class MetricsExporter:
    """
    Export metrics to different formats.

    Supports:
    - JSON export
    - Prometheus format (future)
    - StatsD format (future)
    """

    @staticmethod
    def to_json(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export metrics as JSON-serializable dictionary.

        Args:
            metrics: Metrics dictionary from MetricsCollector.get_all_metrics()

        Returns:
            JSON-serializable dictionary
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': metrics.get('uptime_seconds', 0),
            'metrics': {
                'timings': metrics.get('timings', {}),
                'counters': metrics.get('counters', {}),
                'gauges': metrics.get('gauges', {}),
            }
        }

    @staticmethod
    def to_summary(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export high-level summary of key metrics.

        Args:
            metrics: Metrics dictionary from MetricsCollector.get_all_metrics()

        Returns:
            Summary dictionary with key metrics
        """
        timings = metrics.get('timings', {})
        counters = metrics.get('counters', {})
        gauges = metrics.get('gauges', {})

        # Extract key metrics
        summary = {
            'uptime_seconds': metrics.get('uptime_seconds', 0),
            'event_processing': {},
            'udp_listener': {},
            'websocket': {},
            'cache': {},
            'errors': {},
        }

        # Event processing metrics
        for key, stats in timings.items():
            if 'event.processing' in key:
                summary['event_processing']['latency_ms'] = {
                    'p50': round(stats['p50'] * 1000, 2),
                    'p95': round(stats['p95'] * 1000, 2),
                    'p99': round(stats['p99'] * 1000, 2),
                }

        # Counter summaries
        for key, stats in counters.items():
            if 'events.processed' in key:
                summary['event_processing']['total_processed'] = stats['value']
            elif 'udp.packet.received' in key:
                summary['udp_listener']['packets_received'] = stats['value']
            elif 'udp.packet.dropped' in key:
                summary['udp_listener']['packets_dropped'] = stats['value']
            elif 'websocket.broadcast.success' in key:
                summary['websocket']['broadcasts_sent'] = stats['value']
            elif 'error' in key:
                summary['errors'][key] = stats['value']

        # Gauge summaries
        for key, stats in gauges.items():
            if 'websocket.clients' in key:
                summary['websocket']['clients_connected'] = int(stats['current'])
            elif 'cache.hit_rate' in key:
                summary['cache']['hit_rate_percent'] = round(stats['current'] * 100, 1)

        return summary
