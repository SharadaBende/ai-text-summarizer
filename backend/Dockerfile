FROM python:3.11-slim
WORKDIR /app
# Set to "true" to bake the transformer stack into the image (much larger, enables abstractive/hybrid)
ARG WITH_ML=false
COPY requirements.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && if [ "$WITH_ML" = "true" ]; then pip install --no-cache-dir -r requirements-ml.txt; fi
COPY app ./app
ENV HF_HOME=/models DB_PATH=/data/history.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
