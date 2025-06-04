FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /python-docker
COPY . .

RUN uv sync

EXPOSE 5000

CMD [ "uv", "run", "flask", "--app" , "gs", "run", "--host=0.0.0.0"]
