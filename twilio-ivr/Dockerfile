# syntax=docker/dockerfile:1

# Pinned to a specific Debian base so rebuilds are reproducible. Floating on
# :slim would silently change the OS underneath us; let Dependabot bump this.
FROM python:3.12-slim-bookworm

# Baked in by CI so /healthz can report exactly which commit is running. That is
# what lets a deploy prove the new code actually went live, rather than trusting
# that a push succeeded.
ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies in their own layer so editing app code does not reinstall them.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --system --create-home --uid 10001 appuser
COPY --chown=appuser:appuser . .
USER appuser

EXPOSE 8000

# Uses the stdlib rather than curl so the image carries no extra packages.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"

# EXACTLY ONE WORKER — this is load-bearing, not a default.
#
# Call state lives in an in-process dict keyed by CallSid (ivr/state.py). With a
# second worker, a caller's webhooks would land on whichever process the load
# balancer picked, and a process that has never seen that CallSid restarts the
# decision tree from the beginning — mid-call, for someone who was just hit by
# a car. Concurrency comes from --threads instead, which is safe because the
# session store is guarded by a threading.Lock.
#
# NOTE: twilio-ivr/README.md suggests `gunicorn -w 4` for production. That is
# wrong for this app, and the README says so itself two paragraphs later.
CMD ["gunicorn", \
     "--workers", "1", \
     "--threads", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
