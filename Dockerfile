# 1단계: 베이스 이미지
FROM python:3.11-slim

# 환경변수: .pyc 파일 생성 방지 및 버퍼링 없는 로그
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 필수 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 보안: Non-root 사용자(appuser) 생성 및 전환
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

# 포트 개방
EXPOSE 8000

# uvicorn 실행 (k8s proxy 설정을 위해 forwarded-allow-ips 추가)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
