# CloudPulse CLI image. Separate from simulation/app/Dockerfile, which builds the
# throwaway demo service used only by the local failure-simulation lab.
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir .

FROM python:3.12-slim
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin cloudpulse
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
USER cloudpulse
WORKDIR /home/cloudpulse
ENTRYPOINT ["cloudpulse"]
CMD ["--help"]
