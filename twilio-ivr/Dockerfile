# syntax=docker/dockerfile:1

# Pinned to a specific Python AND Debian release so rebuilds are reproducible.
# A bare :slim tag would move both underneath us silently; let Dependabot bump
# this deliberately. Keep it current: 3.14 is the current Python and trixie the
# current Debian stable. Whoever touches this next should check both, since a
# pin is only a good idea while somebody is still maintaining it.
FROM python:3.14-slim-trixie

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

# Not --system: that flag expects to allocate from the system range (below
# SYS_UID_MAX, normally 999), so combining it with an explicit high UID makes
# useradd warn on every build.
RUN useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser . .
USER appuser

EXPOSE 8000

# Uses the stdlib rather than curl so the image carries no extra packages.
#
# NOTE: HEALTHCHECK is a Docker image-config field with no equivalent in the
# OCI image spec. Docker/buildx keeps it; Podman defaults to OCI format and
# silently DROPS it, so a local build needs:
#     podman build --format docker ...
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
