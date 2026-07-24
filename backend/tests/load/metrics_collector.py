"""Background metrics collector for server CPU and memory."""

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class MetricsSnapshot:
    timestamp: float
    cpu_percent: float
    memory_rss_mb: float


@dataclass
class MetricsSummary:
    samples: list[MetricsSnapshot] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def avg_cpu(self) -> float:
        if not self.samples:
            return 0.0
        return sum(s.cpu_percent for s in self.samples) / len(self.samples)

    @property
    def max_cpu(self) -> float:
        return max((s.cpu_percent for s in self.samples), default=0.0)

    @property
    def memory_delta_mb(self) -> float:
        if len(self.samples) < 2:
            return 0.0
        return self.samples[-1].memory_rss_mb - self.samples[0].memory_rss_mb


class MetricsCollector:
    """Samples server process CPU/memory at fixed interval."""

    def __init__(self, pid: int, interval: float = 5.0):
        self.pid = pid
        self.interval = interval
        self._task: asyncio.Task | None = None
        self.summary = MetricsSummary()
        self._process = None

    async def start(self) -> None:
        import psutil

        self._process = psutil.Process(self.pid)
        # Prime cpu_percent()
        self._process.cpu_percent(interval=None)
        self.summary.start_time = time.time()
        self._task = asyncio.create_task(self._sample_loop())

    async def stop(self) -> MetricsSummary:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.summary.end_time = time.time()
        return self.summary

    async def _sample_loop(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            if self._process and self._process.is_running():
                cpu = self._process.cpu_percent(interval=None)
                rss_mb = self._process.memory_info().rss / (1024 * 1024)
                self.summary.samples.append(
                    MetricsSnapshot(
                        timestamp=time.time(),
                        cpu_percent=cpu,
                        memory_rss_mb=rss_mb,
                    )
                )

    def get_summary(self) -> MetricsSummary:
        return self.summary


async def test_collector() -> None:
    import os

    c = MetricsCollector(os.getpid(), interval=0.1)
    await c.start()
    await asyncio.sleep(0.5)
    summary = await c.stop()
    print(
        f"Samples: {len(summary.samples)}, "
        f"Avg CPU: {summary.avg_cpu:.1f}%, "
        f"Mem delta: {summary.memory_delta_mb:.1f}MB"
    )


if __name__ == "__main__":
    asyncio.run(test_collector())
