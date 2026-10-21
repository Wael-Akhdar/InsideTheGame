# GamePulse web app: FastAPI + agents + MCP endpoint (/mcp/). Real-match data (Wyscout, CC BY 4.0) is downloaded at build time.
FROM python:3.10-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LAB_WORKERS=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY gamepulse ./gamepulse
COPY tools ./tools
COPY web ./web
# public Wyscout dataset (Pappalardo et al. 2019, CC BY 4.0), split per match so that one real match needs a few MB of memory
RUN python tools/fetch_wyscout.py && python tools/split_wyscout.py && rm data/external/wyscout/events.zip
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "gamepulse.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
