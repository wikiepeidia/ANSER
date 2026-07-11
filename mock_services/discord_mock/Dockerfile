# anser/discord-mock 0.1.0 — stdlib only, không deps
FROM python:3.11-slim
WORKDIR /app
COPY app.py .
EXPOSE 9099
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:9099/health',timeout=3).status==200 else 1)"
CMD ["python", "app.py"]
