"""Performance benchmarking for ETL pipeline."""

import logging
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.config import get_config
from src.extract.extract_data import extract_csv
from src.transform.transform_data import transform

logger = logging.getLogger(__name__)


class PipelineBenchmark:
    """Benchmarks pipeline performance."""

    def __init__(self):
        self.results: List[Dict] = []
        self.output_file = Path("benchmark_results.csv")

    def benchmark_extract(self, csv_file: Path, iterations: int = 3) -> Dict:
        """Benchmark extraction phase."""
        logger.info(f"Benchmarking extraction from {csv_file}")

        times = []
        for _ in range(iterations):
            start = time.time()
            df = extract_csv(csv_file)
            elapsed = time.time() - start
            times.append(elapsed)

        result = {
            "phase": "extract",
            "file": str(csv_file),
            "avg_time_sec": sum(times) / len(times),
            "min_time_sec": min(times),
            "max_time_sec": max(times),
            "rows_processed": len(df) if "df" in locals() else 0,
        }

        logger.info(f"Extract benchmark: {result['avg_time_sec']:.3f}s avg")
        self.results.append(result)
        return result

    def benchmark_transform(self, df: pd.DataFrame, iterations: int = 3) -> Dict:
        """Benchmark transform phase."""
        logger.info(f"Benchmarking transform on {len(df)} rows")

        times = []
        for _ in range(iterations):
            start = time.time()
            result_df = transform(df.copy())
            elapsed = time.time() - start
            times.append(elapsed)

        result = {
            "phase": "transform",
            "input_rows": len(df),
            "output_rows": len(result_df) if "result_df" in locals() else 0,
            "avg_time_sec": sum(times) / len(times),
            "min_time_sec": min(times),
            "max_time_sec": max(times),
            "throughput_rows_sec": len(df) / (sum(times) / len(times)) if times else 0,
        }

        logger.info(
            f"Transform benchmark: {result['avg_time_sec']:.3f}s avg, "
            f"{result['throughput_rows_sec']:.0f} rows/sec"
        )
        self.results.append(result)
        return result

    def benchmark_memory(self, df: pd.DataFrame) -> Dict:
        """Benchmark memory usage."""
        import sys

        memory_bytes = df.memory_usage(deep=True).sum()
        memory_mb = memory_bytes / (1024 * 1024)

        result = {
            "phase": "memory",
            "rows": len(df),
            "columns": len(df.columns),
            "memory_mb": memory_mb,
            "bytes_per_row": memory_bytes / len(df) if len(df) > 0 else 0,
        }

        logger.info(f"Memory benchmark: {memory_mb:.2f}MB for {len(df)} rows")
        self.results.append(result)
        return result

    def save_results(self):
        """Save benchmark results to CSV."""
        results_df = pd.DataFrame(self.results)
        results_df.to_csv(self.output_file, index=False)
        logger.info(f"Benchmark results saved to {self.output_file}")

    def print_summary(self):
        """Print benchmark summary."""
        print("\n" + "=" * 80)
        print("PIPELINE PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 80)

        for result in self.results:
            print(f"\nPhase: {result.get('phase', 'unknown').upper()}")
            for key, value in result.items():
                if key != "phase":
                    if isinstance(value, float):
                        print(f"  {key}: {value:.3f}")
                    else:
                        print(f"  {key}: {value}")


def generate_test_data(rows: int, cols: int = 10) -> pd.DataFrame:
    """Generate test data for benchmarking."""
    import numpy as np

    data = {}
    for i in range(cols):
        data[f"col_{i}"] = np.random.randint(0, 1000, rows)

    return pd.DataFrame(data)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    benchmark = PipelineBenchmark()

    # Generate test data
    test_df = generate_test_data(100000, 15)

    # Run benchmarks
    benchmark.benchmark_transform(test_df)
    benchmark.benchmark_memory(test_df)
    benchmark.save_results()
    benchmark.print_summary()
