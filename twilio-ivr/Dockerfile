# syntax=docker/dockerfile:1

# Pinned deliberately; bump via Dependabot. Only the base is pinned —
# requirements.txt uses version ranges.
FROM python:3.14-slim-trixie

# Reported by /healthz so a deploy can confirm which commit is live.
ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Separate layer so editing app code does not reinstall dependencies.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser . .
USER appuser

EXPOSE 8000

# Podman defaults to OCI format, which has no HEALTHCHECK field and drops this
# silently. A local build needs `--format docker`.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"

# ONE worker, deliberately: call state is an in-process dict keyed by CallSid
# (ivr/state.py), so a second worker restarts a caller's decision tree mid-call.
# Threads are safe — the store is lock-guarded. Keep README.md in sync.
CMD ["gunicorn", \
     "--workers", "1", \
     "--threads", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
