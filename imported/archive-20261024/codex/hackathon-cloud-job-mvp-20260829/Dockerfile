FROM python:3.13-slim AS build

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip wheel --no-deps --wheel-dir /wheels .

FROM python:3.13-slim

ARG SOURCE_REVISION
LABEL org.opencontainers.image.revision=$SOURCE_REVISION
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN groupadd --system --gid 65532 fiction-forks \
    && useradd --system --uid 65532 --gid 65532 --home-dir /nonexistent \
       --no-create-home fiction-forks \
    && mkdir /outputs \
    && chown 65532:65532 /outputs

COPY --from=build /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl \
    && rm -rf /wheels

COPY --chown=65532:65532 scenarios /app/scenarios
COPY --chown=65532:65532 interventions /app/interventions
COPY --chown=65532:65532 fixtures /app/fixtures
RUN case "$SOURCE_REVISION" in (*[!0-9a-f]*|'') exit 1;; esac \
    && test "${#SOURCE_REVISION}" -eq 40 \
    && printf '%s\n' "$SOURCE_REVISION" > /app/.source-revision \
    && chmod 0444 /app/.source-revision

USER 65532:65532
WORKDIR /app
ENTRYPOINT ["fiction-forks-job"]
CMD ["--worldline", "haruhi-world-observation", "--output-dir", "/outputs"]
