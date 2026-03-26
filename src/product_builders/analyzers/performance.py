"""Performance Analyzer — Dimension 18 (MEDIUM IMPACT).

Detects caching strategies, lazy loading, code splitting,
bundle size config, image optimization, N+1 prevention, and monitoring.
"""

from __future__ import annotations

from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer, SKIP_DIRS
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, PerformanceResult


class PerformanceAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Performance Analyzer"

    @property
    def dimension(self) -> str:
        return "performance"

    def analyze(self, repo_path: Path, *, index=None) -> PerformanceResult:
        caching = self._detect_caching(repo_path)
        lazy_loading = self._detect_lazy_loading(repo_path)
        code_splitting = self._detect_code_splitting(repo_path)
        bundle_config = self._detect_bundle_config(repo_path)
        image_opt = self._detect_image_optimization(repo_path)
        n_plus_one = self._detect_n_plus_one(repo_path)
        monitoring = self._detect_monitoring(repo_path)

        deps = self.collect_dependency_names(repo_path)

        # C15: Web vitals / performance monitoring
        web_vitals = None
        vitals_deps = {
            "web-vitals": "web-vitals",
            "@vercel/analytics": "vercel-analytics",
            "@lhci/cli": "lighthouse-ci",
        }
        for dep, name in vitals_deps.items():
            if dep in deps:
                web_vitals = name
                break
        if not web_vitals:
            for rc in (".lighthouserc.js", ".lighthouserc.json", ".lighthouserc.yml"):
                if (repo_path / rc).exists():
                    web_vitals = "lighthouse-ci"
                    break

        # C15: Service worker detection
        sw_detected = False
        for sw_file in ("sw.js", "service-worker.js", "sw.ts", "service-worker.ts"):
            if (repo_path / "public" / sw_file).exists() or (repo_path / sw_file).exists():
                sw_detected = True
                break
        if not sw_detected:
            sw_deps = ["next-pwa", "workbox-webpack-plugin", "@vite-pwa/vite-plugin"]
            if any(d in deps for d in sw_deps):
                sw_detected = True

        return PerformanceResult(
            status=AnalysisStatus.SUCCESS,
            caching_strategy=caching,
            lazy_loading=lazy_loading,
            code_splitting=code_splitting,
            bundle_size_config=bundle_config,
            image_optimization=image_opt,
            n_plus_one_prevention=n_plus_one,
            performance_monitoring=monitoring,
            web_vitals_monitoring=web_vitals,
            service_worker_detected=sw_detected,
        )

    def _detect_caching(self, repo_path: Path) -> str | None:
        deps = self.collect_dependency_names(repo_path)
        if "redis" in deps or "ioredis" in deps or "bull" in deps or "bullmq" in deps:
            return "redis"
        if "memcached" in deps or "node-cache" in deps:
            return "in-memory"
        if "django-redis" in deps:
            return "django-cache"
        if "lru-cache" in deps:
            return "lru-cache"
        if "@upstash/redis" in deps:
            return "upstash-redis"
        if "keyv" in deps:
            return "keyv"
        return None

    def _detect_lazy_loading(self, repo_path: Path) -> bool:
        src = repo_path / "src"
        scan = src if src.is_dir() else repo_path
        count = 0
        for ext in ("*.tsx", "*.jsx", "*.ts", "*.js"):
            for f in scan.rglob(ext):
                if count >= 30:
                    break
                if any(s in f.parts for s in SKIP_DIRS):
                    continue
                content = self.read_file(f)
                if not content:
                    continue
                count += 1
                if "React.lazy" in content or "lazy(" in content or "dynamic(" in content:
                    return True
                if "loadable(" in content or "@loadable" in content:
                    return True
        return False

    def _detect_code_splitting(self, repo_path: Path) -> bool:
        src = repo_path / "src"
        scan = src if src.is_dir() else repo_path
        count = 0
        for ext in ("*.tsx", "*.jsx", "*.ts", "*.js"):
            for f in scan.rglob(ext):
                if count >= 30:
                    break
                if any(s in f.parts for s in SKIP_DIRS):
                    continue
                content = self.read_file(f)
                if not content:
                    continue
                count += 1
                if "import(" in content and "/*" in content:
                    return True
                if "React.lazy" in content or "dynamic(" in content:
                    return True
        next_config = repo_path / "next.config.js"
        if next_config.exists():
            return True
        return False

    def _detect_bundle_config(self, repo_path: Path) -> str | None:
        candidates = [
            ("webpack.config.js", "webpack"),
            ("webpack.config.ts", "webpack"),
            ("vite.config.ts", "vite"),
            ("vite.config.js", "vite"),
            ("rollup.config.js", "rollup"),
            ("rollup.config.mjs", "rollup"),
            ("esbuild.config.js", "esbuild"),
            ("turbopack.json", "turbopack"),
        ]
        for filename, bundler in candidates:
            if (repo_path / filename).exists():
                return bundler
        next_config = repo_path / "next.config.js"
        if next_config.exists() or (repo_path / "next.config.mjs").exists() or (repo_path / "next.config.ts").exists():
            return "next.js (built-in)"
        return None

    def _detect_image_optimization(self, repo_path: Path) -> str | None:
        deps = self.collect_dependency_names(repo_path)
        if "sharp" in deps:
            return "sharp"
        if "next" in deps:
            return "next/image"
        if "imagemin" in deps:
            return "imagemin"
        if "Pillow" in deps or "pillow" in deps:
            return "Pillow"
        return None

    def _detect_n_plus_one(self, repo_path: Path) -> str | None:
        deps = self.collect_dependency_names(repo_path)
        if "dataloader" in deps:
            return "DataLoader"
        if "django-auto-prefetch" in deps:
            return "django-auto-prefetch"
        if "nplusone" in deps:
            return "nplusone"
        if "bullet" in deps:
            return "bullet"
        return None

    def _detect_monitoring(self, repo_path: Path) -> str | None:
        deps = self.collect_dependency_names(repo_path)
        if "@sentry/browser" in deps or "@sentry/node" in deps or "sentry-sdk" in deps:
            return "sentry"
        if "newrelic" in deps or "newrelic-agent" in deps:
            return "new-relic"
        if "dd-trace" in deps or "ddtrace" in deps:
            return "datadog"
        if "@opentelemetry/api" in deps or "opentelemetry-api" in deps:
            return "opentelemetry"
        if "prom-client" in deps:
            return "prometheus"
        if "@vercel/analytics" in deps:
            return "vercel-analytics"
        if "web-vitals" in deps:
            return "web-vitals"
        if "@lhci/cli" in deps:
            return "lighthouse-ci"
        if "@datadog/browser-rum" in deps:
            return "datadog-rum"
        return None


register(PerformanceAnalyzer())
