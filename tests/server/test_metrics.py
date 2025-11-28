"""
Tests for metrics collection system (Phase 11e).

Verifies that:
1. MetricsCollector correctly tracks timings, counters, and gauges
2. Timer context manager works correctly
3. Metrics are properly integrated into ASTServer
4. Event processing metrics are tracked
5. Metrics can be exported in different formats
"""

import pytest
import time
import asyncio
from src.server.api import ASTServer
from src.server.utils import MetricsCollector, MetricsExporter
from src.ast import ProjectNode, TrackNode, SceneNode


class TestMetricsCollector:
    """Test the MetricsCollector class."""

    def test_initialization(self):
        """Test metrics collector initialization."""
        metrics1 = MetricsCollector()
        assert metrics1.enabled is True

        metrics2 = MetricsCollector(enabled=False)
        assert metrics2.enabled is False

    def test_timing_metric(self):
        """Test timing metric recording."""
        metrics = MetricsCollector()

        # Record timing
        metrics.timing('test.operation', 0.123)

        # Get the metric
        stats = metrics.get_timing('test.operation')
        assert stats is not None
        assert stats['count'] == 1
        assert stats['mean'] == pytest.approx(0.123, rel=1e-6)
        assert stats['min'] == pytest.approx(0.123, rel=1e-6)
        assert stats['max'] == pytest.approx(0.123, rel=1e-6)

        # Record more timings
        metrics.timing('test.operation', 0.456)
        metrics.timing('test.operation', 0.789)

        stats = metrics.get_timing('test.operation')
        assert stats['count'] == 3
        assert stats['mean'] == pytest.approx((0.123 + 0.456 + 0.789) / 3, rel=1e-6)

    def test_counter_metric(self):
        """Test counter metric."""
        metrics = MetricsCollector()

        # Increment counter
        metrics.increment('test.events')

        stats = metrics.get_counter('test.events')
        assert stats is not None
        assert stats['value'] == 1

        # Increment by custom amount
        metrics.increment('test.events', amount=5)

        stats = metrics.get_counter('test.events')
        assert stats['value'] == 6

        # Decrement
        metrics.decrement('test.events', amount=2)

        stats = metrics.get_counter('test.events')
        assert stats['value'] == 4

    def test_gauge_metric(self):
        """Test gauge metric."""
        metrics = MetricsCollector()

        # Set gauge
        metrics.gauge('test.connections', 3.0)

        stats = metrics.get_gauge('test.connections')
        assert stats is not None
        assert stats['current'] == 3.0

        # Update gauge
        metrics.gauge('test.connections', 5.0)

        stats = metrics.get_gauge('test.connections')
        assert stats['current'] == 5.0
        assert stats['min'] == 3.0
        assert stats['max'] == 5.0

    def test_timer_context_manager(self):
        """Test timer context manager."""
        metrics = MetricsCollector()

        # Use timer context
        with metrics.timer('test.block'):
            time.sleep(0.01)  # Sleep for 10ms

        stats = metrics.get_timing('test.block')
        assert stats is not None
        assert stats['count'] == 1
        assert stats['mean'] >= 0.01  # At least 10ms
        assert stats['mean'] < 0.1    # But less than 100ms

    def test_metrics_with_tags(self):
        """Test metrics with tags."""
        metrics = MetricsCollector()

        # Record metrics with tags
        metrics.timing('request.duration', 0.1, tags={'endpoint': '/api/v1'})
        metrics.timing('request.duration', 0.2, tags={'endpoint': '/api/v2'})

        # Each tag combination creates a separate metric
        stats1 = metrics.get_timing('request.duration', tags={'endpoint': '/api/v1'})
        assert stats1 is not None
        assert stats1['count'] == 1
        assert stats1['mean'] == pytest.approx(0.1, rel=1e-6)

        stats2 = metrics.get_timing('request.duration', tags={'endpoint': '/api/v2'})
        assert stats2 is not None
        assert stats2['count'] == 1
        assert stats2['mean'] == pytest.approx(0.2, rel=1e-6)

    def test_percentiles(self):
        """Test percentile calculations."""
        metrics = MetricsCollector()

        # Record many values
        values = [0.001 * i for i in range(1, 101)]  # 1ms to 100ms
        for value in values:
            metrics.timing('test.latency', value)

        stats = metrics.get_timing('test.latency')
        assert stats is not None

        # Check percentiles (only last 100 values are kept)
        assert stats['p50'] == pytest.approx(0.050, rel=0.1)  # ~50ms
        assert stats['p95'] == pytest.approx(0.095, rel=0.1)  # ~95ms
        assert stats['p99'] == pytest.approx(0.099, rel=0.1)  # ~99ms

    def test_disabled_metrics(self):
        """Test that disabled collector doesn't record metrics."""
        metrics = MetricsCollector(enabled=False)

        # Try to record metrics
        metrics.timing('test.operation', 0.123)
        metrics.increment('test.counter')
        metrics.gauge('test.gauge', 5.0)

        # All should return None
        assert metrics.get_timing('test.operation') is None
        assert metrics.get_counter('test.counter') is None
        assert metrics.get_gauge('test.gauge') is None

    def test_get_all_metrics(self):
        """Test getting all metrics."""
        metrics = MetricsCollector()

        metrics.timing('op.duration', 0.123)
        metrics.increment('events.count')
        metrics.gauge('connections', 5.0)

        all_metrics = metrics.get_all_metrics()

        assert 'timings' in all_metrics
        assert 'counters' in all_metrics
        assert 'gauges' in all_metrics
        assert 'uptime_seconds' in all_metrics

        assert 'op.duration' in all_metrics['timings']
        assert 'events.count' in all_metrics['counters']
        assert 'connections' in all_metrics['gauges']

    def test_reset_metrics(self):
        """Test resetting metrics."""
        metrics = MetricsCollector()

        metrics.timing('test.operation', 0.123)
        metrics.increment('test.counter')
        metrics.gauge('test.gauge', 5.0)

        # Verify metrics exist
        assert metrics.get_timing('test.operation') is not None
        assert metrics.get_counter('test.counter') is not None
        assert metrics.get_gauge('test.gauge') is not None

        # Reset all metrics
        metrics.reset()

        # All should be gone
        assert metrics.get_timing('test.operation') is None
        assert metrics.get_counter('test.counter') is None
        assert metrics.get_gauge('test.gauge') is None


class TestMetricsExporter:
    """Test the MetricsExporter class."""

    def test_to_json_export(self):
        """Test JSON export."""
        metrics = MetricsCollector()

        metrics.timing('test.op', 0.123)
        metrics.increment('test.count')
        metrics.gauge('test.gauge', 5.0)

        all_metrics = metrics.get_all_metrics()
        json_export = MetricsExporter.to_json(all_metrics)

        assert 'timestamp' in json_export
        assert 'uptime_seconds' in json_export
        assert 'metrics' in json_export
        assert 'timings' in json_export['metrics']
        assert 'counters' in json_export['metrics']
        assert 'gauges' in json_export['metrics']

    def test_to_summary_export(self):
        """Test summary export."""
        metrics = MetricsCollector()

        # Simulate realistic metrics
        metrics.timing('event.processing', 0.015)
        metrics.increment('events.processed', 100)
        metrics.increment('udp.packet.received', 200)
        metrics.increment('udp.packet.dropped', 5)
        metrics.gauge('websocket.clients', 3.0)
        metrics.gauge('cache.hit_rate', 0.85)

        all_metrics = metrics.get_all_metrics()
        summary = MetricsExporter.to_summary(all_metrics)

        assert 'event_processing' in summary
        assert 'udp_listener' in summary
        assert 'websocket' in summary
        assert 'cache' in summary
        assert 'errors' in summary


class TestASTServerMetricsIntegration:
    """Test metrics integration in ASTServer."""

    def test_server_has_metrics(self):
        """Test that ASTServer creates metrics instance."""
        server = ASTServer(enable_websocket=False)

        assert hasattr(server, 'metrics')
        assert isinstance(server.metrics, MetricsCollector)
        assert server.metrics.enabled is True

    def test_server_metrics_configuration(self):
        """Test metrics configuration options."""
        # Disabled metrics
        server1 = ASTServer(enable_websocket=False, enable_metrics=False)
        assert server1.metrics.enabled is False

        # Enabled metrics (default)
        server2 = ASTServer(enable_websocket=False, enable_metrics=True)
        assert server2.metrics.enabled is True

    def test_metrics_endpoints(self):
        """Test metrics endpoints."""
        server = ASTServer(enable_websocket=False)

        # Record some metrics
        server.metrics.timing('test.operation', 0.123)
        server.metrics.increment('test.counter')

        # Get full metrics
        metrics = server.get_metrics()
        assert 'timestamp' in metrics
        assert 'metrics' in metrics

        # Get summary
        summary = server.get_metrics_summary()
        assert 'uptime_seconds' in summary
        assert 'event_processing' in summary

    @pytest.mark.asyncio
    async def test_event_processing_metrics(self):
        """Test that event processing records metrics."""
        server = ASTServer(enable_websocket=False)

        # Create test AST
        root = ProjectNode(id="project_test")
        root.hash = "test_hash"
        track = TrackNode(name="Track 1", index=0, id="track_0")
        root.children = [track]
        server.current_ast = root

        # Reset metrics to start fresh
        server.metrics.reset()

        # Process an event
        await server.process_live_event(
            event_path="/live/track/renamed",
            args=[0, "New Name"],
            seq_num=1,
            timestamp=time.time()
        )

        # Check metrics were recorded
        all_metrics = server.metrics.get_all_metrics()

        # Should have event received counter
        counters = all_metrics['counters']
        assert any('events.received' in key for key in counters.keys())

        # Should have timing metric
        timings = all_metrics['timings']
        assert any('event.processing.duration' in key for key in timings.keys())

    @pytest.mark.asyncio
    async def test_error_metrics(self):
        """Test that errors are tracked in metrics."""
        server = ASTServer(enable_websocket=False)

        # No AST loaded - should track as ignored
        server.metrics.reset()

        await server.process_live_event(
            event_path="/live/track/renamed",
            args=[0, "Name"],
            seq_num=1,
            timestamp=time.time()
        )

        # Should have ignored counter
        all_metrics = server.metrics.get_all_metrics()
        counters = all_metrics['counters']
        assert any('events.ignored.no_ast' in key for key in counters.keys())

    @pytest.mark.asyncio
    async def test_unhandled_event_metrics(self):
        """Test that unhandled events are tracked."""
        server = ASTServer(enable_websocket=False)

        # Create test AST
        root = ProjectNode(id="project_test")
        root.hash = "test_hash"
        server.current_ast = root

        server.metrics.reset()

        # Process unknown event
        await server.process_live_event(
            event_path="/live/unknown/event",
            args=[],
            seq_num=1,
            timestamp=time.time()
        )

        # Should have unhandled counter
        all_metrics = server.metrics.get_all_metrics()
        counters = all_metrics['counters']
        assert any('events.unhandled' in key for key in counters.keys())


class TestMetricsPerformance:
    """Test that metrics don't significantly impact performance."""

    def test_overhead_is_minimal(self):
        """Test that metrics collection overhead is minimal."""
        metrics = MetricsCollector()

        # Measure overhead
        iterations = 10000

        # Time with metrics
        start = time.time()
        for i in range(iterations):
            metrics.increment('test.counter')
            metrics.gauge('test.gauge', float(i))
        with_metrics = time.time() - start

        # Overhead should be reasonable (< 100ms for 10k operations)
        # This is very generous - actual overhead is much lower
        assert with_metrics < 0.1, f"Metrics overhead too high: {with_metrics:.4f}s for {iterations} operations"

    def test_disabled_has_no_overhead(self):
        """Test that disabled metrics have essentially no overhead."""
        metrics = MetricsCollector(enabled=False)

        iterations = 10000

        start = time.time()
        for i in range(iterations):
            metrics.increment('test.counter')
            metrics.gauge('test.gauge', float(i))
            metrics.timing('test.timing', 0.001)
        elapsed = time.time() - start

        # Should be very fast (< 10ms for 10k operations)
        assert elapsed < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
