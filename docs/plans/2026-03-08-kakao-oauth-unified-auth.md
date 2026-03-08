# Kakao OAuth + Telegram Login + 통합 유저 시스템 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** SyncWatt과 RESync 두 서비스에 Kakao OAuth 회원가입, Telegram 연동, 통합 유저 시스템을 구현한다.

**Architecture:** FastAPI 백엔드에 Kakao OAuth REST API 엔드포인트와 JWT 세션을 추가한다. 프론트엔드는 Next.js 안정 버전으로 업그레이드하고 shadcn/ui Dialog로 "3월 중 오픈 예정" 모달을 띄운다. Telegram 봇 유저와 Kakao 유저는 auth code 방식으로 연결하여 통합 유저로 관리한다.

**Tech Stack:** FastAPI, SQLModel, PyJWT, httpx (Kakao API), Next.js 14.2.x / 15.1.x, shadcn/ui, Tailwind CSS

---

## 사전 준비 (수동)

### Kakao Developers 앱 등록

1. [developers.kakao.com](https://developers.kakao.com) → 내 애플리케이션 → 앱 추가
2. 앱 이름: `SyncWatt` (RESync도 동일 앱으로 가능, 또는 별도 등록)
3. 플랫폼 → Web → 사이트 도메인 추가:
   - `https://syncwatt.dog-foot.com`
   - `https://resync.dog-foot.com`
   - `http://localhost:3000`
4. 카카오 로그인 → 활성화 설정: ON
5. Redirect URI 등록:
   - `https://syncwatt.dog-foot.com/auth/kakao/callback`
   - `https://resync.dog-foot.com/auth/kakao/callback`
   - `http://localhost:3000/auth/kakao/callback`
6. 동의항목: `profile_nickname`, `account_email` (선택)
7. 앱 키 확인: REST API 키 → `KAKAO_CLIENT_ID`, 보안 → Client Secret → `KAKAO_CLIENT_SECRET`

---

## Phase 1: 백엔드 — SyncWatt

### Task 1: 의존성 추가

**Files:**
- Modify: `requirements.txt`

**Step 1: requirements.txt에 패키지 추가**

```
# requirements.txt에 아래 추가
PyJWT==2.9.0
cryptography==44.0.0
```

> `httpx`는 이미 설치되어 있음 (telegram_client.py에서 사용 중). `cryptography`는 PyJWT RS256 지원용.

**Step 2: 로컬에서 설치 확인**

Run: `cd /Users/kkh/works/dog-foot/SyncWatt/SyncWatt-Backend && pip install PyJWT==2.9.0 cryptography==44.0.0`
Expected: Successfully installed

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add PyJWT and cryptography dependencies"
```

---

### Task 2: Config에 Kakao + JWT 설정 추가

**Files:**
- Modify: `app/core/config.py`

**Step 1: config.py에 Kakao + JWT 환경변수 추가**

`app/core/config.py`의 Settings 클래스에 추가:

```python
# Kakao OAuth
KAKAO_CLIENT_ID: str = ""
KAKAO_CLIENT_SECRET: str = ""
KAKAO_REDIRECT_URI: str = "http://localhost:3000/auth/kakao/callback"

# JWT
JWT_SECRET_KEY: str = "dev-secret-change-in-production"
JWT_ALGORITHM: str = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7일
```

**Step 2: .env.example 업데이트**

`.env.example`에 추가:

```
KAKAO_CLIENT_ID=your_kakao_rest_api_key
KAKAO_CLIENT_SECRET=your_kakao_client_secret
KAKAO_REDIRECT_URI=https://syncwatt.dog-foot.com/auth/kakao/callback
JWT_SECRET_KEY=your-secret-key-min-32-chars
```

**Step 3: Commit**

```bash
git add app/core/config.py .env.example
git commit -m "feat: add Kakao OAuth and JWT config settings"
```

---

### Task 3: User 모델 업데이트

**Files:**
- Modify: `app/models/user.py`

**Step 1: User 모델에 Kakao 필드 추가**

현재 모델:
```python
class User(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)
    telegram_chat_id: str = Field(unique=True, index=True)
    kakao_id: Optional[str] = None
    phone: Optional[str] = None
    plan: str = Field(default="free")
    plant_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

변경:
```python
class User(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)
    telegram_chat_id: Optional[str] = Field(default=None, unique=True, index=True)  # Optional로 변경
    kakao_id: Optional[str] = Field(default=None, unique=True, index=True)  # unique+index 추가
    kakao_nickname: Optional[str] = None
    kakao_email: Optional[str] = None
    phone: Optional[str] = None
    plan: str = Field(default="free")
    plant_count: int = Field(default=0)
    link_code: Optional[str] = Field(default=None, unique=True)  # Telegram-Kakao 연동 코드
    link_code_expires: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

핵심 변경:
- `telegram_chat_id`: `str` → `Optional[str]` (Kakao만으로 가입 가능)
- `kakao_id`: `unique=True, index=True` 추가
- `kakao_nickname`, `kakao_email`: Kakao 프로필 정보 저장
- `link_code`, `link_code_expires`: 텔레그램-카카오 계정 연동용 6자리 코드

**Step 2: Commit**

```bash
git add app/models/user.py
git commit -m "feat: update User model for Kakao OAuth and account linking"
```

---

### Task 4: JWT 유틸리티 작성

**Files:**
- Create: `app/core/security.py`
- Create: `tests/test_security.py`

**Step 1: 테스트 작성**

```python
# tests/test_security.py
from app.core.security import create_access_token, verify_token

def test_create_and_verify_token():
    token = create_access_token(user_id=1)
    payload = verify_token(token)
    assert payload["user_id"] == 1
    assert payload["type"] == "access"

def test_invalid_token_returns_none():
    payload = verify_token("invalid.token.here")
    assert payload is None

def test_expired_token_returns_none():
    token = create_access_token(user_id=1, expire_minutes=-1)
    payload = verify_token(token)
    assert payload is None
```

**Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/test_security.py -v`
Expected: FAIL (모듈 없음)

**Step 3: 구현**

```python
# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from app.core.config import settings


def create_access_token(user_id: int, expire_minutes: Optional[int] = None) -> str:
    if expire_minutes is None:
        expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {
        "user_id": user_id,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
```

**Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/test_security.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add app/core/security.py tests/test_security.py
git commit -m "feat: add JWT token create/verify utilities"
```

---

### Task 5: 현재 유저 의존성 (FastAPI Depends)

**Files:**
- Create: `app/api/deps.py`

**Step 1: 구현**

```python
# app/api/deps.py
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from app.core.security import verify_token
from app.db.session import get_session
from app.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: Session = Depends(get_session),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = session.exec(select(User).where(User.user_id == payload["user_id"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: Session = Depends(get_session),
) -> Optional[User]:
    if not credentials:
        return None
    payload = verify_token(credentials.credentials)
    if not payload:
        return None
    return session.exec(select(User).where(User.user_id == payload["user_id"])).first()
```

**Step 2: Commit**

```bash
git add app/api/deps.py
git commit -m "feat: add FastAPI auth dependencies (get_current_user)"
```

---

### Task 6: Kakao OAuth 엔드포인트

**Files:**
- Create: `app/api/auth.py`
- Modify: `app/main.py`

**Step 1: Kakao OAuth 라우터 구현**

```python
# app/api/auth.py
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import httpx
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_session
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_URL = "https://kapi.kakao.com/v2/user/me"


@router.get("/kakao/login")
async def kakao_login():
    """프론트엔드에서 리다이렉트할 Kakao 인증 URL 반환"""
    auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={settings.KAKAO_CLIENT_ID}"
        f"&redirect_uri={settings.KAKAO_REDIRECT_URI}"
        f"&response_type=code"
    )
    return {"auth_url": auth_url}


@router.post("/kakao/callback")
async def kakao_callback(code: str, session: Session = Depends(get_session)):
    """Kakao authorization code → access token → 유저 정보 → JWT 발급"""
    # 1. code → Kakao access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(KAKAO_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "client_id": settings.KAKAO_CLIENT_ID,
            "client_secret": settings.KAKAO_CLIENT_SECRET,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "code": code,
        })
    if token_resp.status_code != 200:
        logger.error(f"Kakao token error: {token_resp.text}")
        raise HTTPException(status_code=400, detail="Kakao 인증 실패")
    kakao_token = token_resp.json()["access_token"]

    # 2. Kakao access token → 유저 정보
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(KAKAO_USER_URL, headers={
            "Authorization": f"Bearer {kakao_token}"
        })
    if user_resp.status_code != 200:
        logger.error(f"Kakao user info error: {user_resp.text}")
        raise HTTPException(status_code=400, detail="Kakao 유저 정보 조회 실패")

    kakao_data = user_resp.json()
    kakao_id = str(kakao_data["id"])
    nickname = kakao_data.get("properties", {}).get("nickname")
    email = kakao_data.get("kakao_account", {}).get("email")

    # 3. 기존 유저 확인 or 신규 생성
    user = session.exec(select(User).where(User.kakao_id == kakao_id)).first()
    if not user:
        user = User(kakao_id=kakao_id, kakao_nickname=nickname, kakao_email=email)
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info(f"New Kakao user created: {user.user_id} ({nickname})")
    else:
        # 닉네임/이메일 업데이트
        user.kakao_nickname = nickname
        user.kakao_email = email
        session.add(user)
        session.commit()

    # 4. JWT 발급
    token = create_access_token(user_id=user.user_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "nickname": user.kakao_nickname,
            "is_telegram_linked": user.telegram_chat_id is not None,
        },
    }


@router.get("/me")
async def get_me(
    user: User = Depends(__import__("app.api.deps", fromlist=["get_current_user"]).get_current_user),
):
    """현재 로그인 유저 정보"""
    return {
        "user_id": user.user_id,
        "nickname": user.kakao_nickname,
        "is_telegram_linked": user.telegram_chat_id is not None,
        "plan": user.plan,
    }
```

**Step 2: main.py에 auth 라우터 등록**

`app/main.py`에 추가:

```python
from app.api.auth import router as auth_router
# ...
app.include_router(auth_router)
```

**Step 3: Commit**

```bash
git add app/api/auth.py app/main.py
git commit -m "feat: add Kakao OAuth login/callback endpoints"
```

---

### Task 7: Telegram-Kakao 계정 연동 엔드포인트

**Files:**
- Modify: `app/api/auth.py`

**Step 1: 연동 코드 발급/검증 엔드포인트 추가**

`app/api/auth.py`에 추가:

```python
import secrets
from datetime import datetime, timedelta, timezone
from app.api.deps import get_current_user


@router.post("/link/generate-code")
async def generate_link_code(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Kakao 로그인된 유저가 Telegram 연동용 6자리 코드 발급"""
    if user.telegram_chat_id:
        return {"message": "이미 텔레그램이 연결되어 있습니다", "linked": True}

    code = secrets.token_hex(3).upper()  # 6자리 hex (예: A3F2B1)
    user.link_code = code
    user.link_code_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    session.add(user)
    session.commit()

    return {"code": code, "expires_in": 600}


@router.post("/link/verify")
async def verify_link_code(
    telegram_chat_id: str,
    code: str,
    session: Session = Depends(get_session),
):
    """Telegram 봇에서 호출 — 코드로 계정 연동"""
    # 코드로 Kakao 유저 찾기
    kakao_user = session.exec(
        select(User).where(User.link_code == code.upper())
    ).first()

    if not kakao_user or not kakao_user.link_code_expires:
        raise HTTPException(status_code=400, detail="유효하지 않은 코드입니다")

    if datetime.now(timezone.utc) > kakao_user.link_code_expires:
        raise HTTPException(status_code=400, detail="만료된 코드입니다")

    # 기존 Telegram 유저가 있으면 병합
    telegram_user = session.exec(
        select(User).where(User.telegram_chat_id == telegram_chat_id)
    ).first()

    if telegram_user and telegram_user.user_id != kakao_user.user_id:
        # Telegram 유저의 데이터를 Kakao 유저로 병합
        kakao_user.telegram_chat_id = telegram_chat_id
        kakao_user.phone = kakao_user.phone or telegram_user.phone
        kakao_user.plan = max(kakao_user.plan, telegram_user.plan, key=lambda p: ["free", "standard", "pro"].index(p))
        kakao_user.plant_count = max(kakao_user.plant_count, telegram_user.plant_count)
        # 기존 Telegram-only 유저 삭제
        session.delete(telegram_user)
    else:
        kakao_user.telegram_chat_id = telegram_chat_id

    # 코드 초기화
    kakao_user.link_code = None
    kakao_user.link_code_expires = None
    session.add(kakao_user)
    session.commit()

    return {"message": "계정이 연동되었습니다", "user_id": kakao_user.user_id}
```

**Step 2: Telegram 봇에서 /link 명령어 핸들러 추가**

`app/api/webhook.py` 또는 해당 핸들러 파일에 `/link XXXXXX` 텍스트 메시지 처리 추가:

```python
# /link 명령어 처리 (webhook 핸들러 내에서)
if text.startswith("/link "):
    code = text.split(" ", 1)[1].strip()
    # 내부적으로 verify_link_code 호출
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:8000/auth/link/verify",
            params={"telegram_chat_id": str(chat_id), "code": code},
        )
    if resp.status_code == 200:
        await telegram_client.send_message(chat_id, "✅ 카카오 계정과 연동되었습니다!")
    else:
        error = resp.json().get("detail", "연동 실패")
        await telegram_client.send_message(chat_id, f"❌ {error}")
```

**Step 3: Commit**

```bash
git add app/api/auth.py app/api/webhook.py
git commit -m "feat: add Telegram-Kakao account linking via auth code"
```

---

## Phase 2: 백엔드 — RESync

### Task 8: RESync 백엔드에 동일 auth 시스템 적용

RESync 백엔드는 SyncWatt과 동일한 구조이므로 같은 파일들을 추가/수정한다.

**Files:**
- Modify: `requirements.txt` (SyncWatt과 동일 — PyJWT, cryptography)
- Modify: `app/core/config.py` (Kakao + JWT 설정 추가)
- Modify: `app/models/user.py` (동일 변경)
- Create: `app/core/security.py` (SyncWatt과 동일)
- Create: `app/api/deps.py` (SyncWatt과 동일)
- Create: `app/api/auth.py` (SyncWatt과 동일, redirect URI만 다름)
- Modify: `app/main.py` (auth 라우터 + CORS 미들웨어 추가)

**RESync main.py 특이사항 — CORS 추가 필요:**

```python
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth import router as auth_router

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://resync.dog-foot.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
```

**Config 차이:**
```python
KAKAO_REDIRECT_URI: str = "http://localhost:3000/auth/kakao/callback"
# prod: https://resync.dog-foot.com/auth/kakao/callback
```

**Step: 전부 적용 후 Commit**

```bash
git add -A
git commit -m "feat: add Kakao OAuth and account linking to RESync backend"
```

---

## Phase 3: 프론트엔드 — SyncWatt

### Task 9: Next.js 버전 확인 및 업그레이드

**Files:**
- Modify: `package.json`

현재: Next.js `14.2.35` (React 18)

> Next.js 14.2.x 최신 안정 버전으로 업그레이드. 14.2.x 라인은 이미 안정적이므로 최신 패치만 적용.

**Step 1: 최신 14.2.x 패치 확인**

Run: `npm view next@14.2 version`

**Step 2: 업그레이드**

Run: `cd /Users/kkh/works/dog-foot/SyncWatt/SyncWatt-Frontend && npm install next@14.2`
Expected: 14.2.x 최신 패치로 업그레이드

**Step 3: 빌드 확인**

Run: `npm run build`
Expected: 성공

**Step 4: Commit**

```bash
git add package.json package-lock.json
git commit -m "chore: upgrade Next.js to latest 14.2.x stable"
```

---

### Task 10: shadcn/ui Dialog 컴포넌트 추가

SyncWatt은 이미 shadcn 일부 컴포넌트가 있음 (button, card, accordion, label, input).

**Files:**
- Create: `src/components/ui/dialog.tsx` (shadcn CLI로 생성)

**Step 1: shadcn dialog 추가**

Run: `cd /Users/kkh/works/dog-foot/SyncWatt/SyncWatt-Frontend && npx shadcn@latest add dialog`

> 이미 shadcn 설정이 되어 있으므로 바로 추가 가능.

**Step 2: Commit**

```bash
git add src/components/ui/dialog.tsx
git commit -m "feat: add shadcn Dialog component"
```

---

### Task 11: Kakao OAuth 콜백 페이지 + 오픈 예정 모달

**Files:**
- Create: `src/app/auth/kakao/callback/page.tsx`
- Create: `src/components/KakaoLoginButton.tsx`
- Create: `src/components/OpeningSoonModal.tsx`

**Step 1: 환경변수 설정**

`.env.local` (또는 `.env.example`):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_KAKAO_CLIENT_ID=your_kakao_rest_api_key
NEXT_PUBLIC_KAKAO_REDIRECT_URI=http://localhost:3000/auth/kakao/callback
```

**Step 2: Kakao OAuth 콜백 페이지**

```tsx
// src/app/auth/kakao/callback/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { OpeningSoonModal } from '@/components/OpeningSoonModal'

export default function KakaoCallbackPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [showModal, setShowModal] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const code = searchParams.get('code')
    if (!code) {
      setError('인증 코드가 없습니다')
      return
    }

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/kakao/callback?code=${code}`, {
      method: 'POST',
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.access_token) {
          localStorage.setItem('access_token', data.access_token)
          setShowModal(true)
        } else {
          setError('로그인 실패')
        }
      })
      .catch(() => setError('서버 연결 실패'))
  }, [searchParams])

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-red-500">{error}</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      {!showModal && <p>로그인 처리 중...</p>}
      <OpeningSoonModal open={showModal} onClose={() => router.push('/')} />
    </div>
  )
}
```

**Step 3: 오픈 예정 모달**

```tsx
// src/components/OpeningSoonModal.tsx
'use client'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

interface Props {
  open: boolean
  onClose: () => void
}

export function OpeningSoonModal({ open, onClose }: Props) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>가입이 완료되었습니다!</DialogTitle>
          <DialogDescription>
            SyncWatt은 3월 중 정식 오픈 예정입니다.
            오픈 시 카카오톡으로 알림을 보내드리겠습니다.
          </DialogDescription>
        </DialogHeader>
        <Button onClick={onClose} className="w-full mt-4">
          확인
        </Button>
      </DialogContent>
    </Dialog>
  )
}
```

**Step 4: 카카오 로그인 버튼 컴포넌트**

```tsx
// src/components/KakaoLoginButton.tsx
'use client'

interface Props {
  className?: string
  children?: React.ReactNode
}

export function KakaoLoginButton({ className, children }: Props) {
  const handleLogin = () => {
    const kakaoAuthUrl =
      `https://kauth.kakao.com/oauth/authorize` +
      `?client_id=${process.env.NEXT_PUBLIC_KAKAO_CLIENT_ID}` +
      `&redirect_uri=${process.env.NEXT_PUBLIC_KAKAO_REDIRECT_URI}` +
      `&response_type=code`
    window.location.href = kakaoAuthUrl
  }

  return (
    <button onClick={handleLogin} className={className}>
      {children || '카카오로 시작하기'}
    </button>
  )
}
```

**Step 5: Header.tsx의 "카카오 가입" 버튼을 KakaoLoginButton으로 교체**

현재 Header.tsx에서 `<a href="#cta">카카오 가입</a>` → `<KakaoLoginButton>카카오 가입</KakaoLoginButton>` 으로 변경.

**Step 6: Commit**

```bash
git add src/app/auth/kakao/callback/page.tsx src/components/KakaoLoginButton.tsx src/components/OpeningSoonModal.tsx src/components/Header.tsx
git commit -m "feat: add Kakao OAuth flow with opening-soon modal"
```

---

## Phase 4: 프론트엔드 — RESync

### Task 12: Next.js 버전 확인 및 업그레이드

**Files:**
- Modify: `package.json`

현재: Next.js `15.2.4` (React 19)

> Next.js 15.1.x 안정 버전으로 다운그레이드는 비권장. 15.2.x 최신 패치 적용.

**Step 1: 최신 15.2.x 패치 확인**

Run: `npm view next@15.2 version`

**Step 2: 업그레이드**

Run: `cd /Users/kkh/works/dog-foot/RESync/RESync-Frontend && npm install next@15.2`

**Step 3: 빌드 확인**

Run: `npm run build`

**Step 4: Commit**

```bash
git add package.json package-lock.json
git commit -m "chore: upgrade Next.js to latest 15.2.x stable"
```

---

### Task 13: RESync에 shadcn/ui 초기 설정

RESync는 shadcn/ui가 전혀 없으므로 초기화부터 진행.

**Files:**
- Create: `components.json`
- Modify: `tailwind.config.ts` (CSS 변수 추가)
- Modify: `app/globals.css` (shadcn CSS 변수 추가)
- Create: `lib/utils.ts`

**Step 1: shadcn 초기화**

Run: `cd /Users/kkh/works/dog-foot/RESync/RESync-Frontend && npx shadcn@latest init`

선택지:
- Style: Default
- Base color: Slate
- CSS variables: Yes
- Tailwind config path: `tailwind.config.ts`
- Components alias: `@/components`
- Utils alias: `@/lib/utils`

> 주의: RESync의 기존 커스텀 색상(teal, ink, smoke 등)이 유지되는지 확인. shadcn CSS 변수가 globals.css에 추가되더라도 기존 `:root` 변수와 충돌하지 않도록 한다.

**Step 2: shadcn Dialog + Button 추가**

Run:
```bash
npx shadcn@latest add dialog
npx shadcn@latest add button
```

**Step 3: globals.css 머지 확인**

기존 RESync globals.css의 `:root` 변수(--teal, --ink 등)와 shadcn CSS 변수(--background, --foreground 등)가 공존하는지 확인. 충돌 시 shadcn 변수를 RESync 색상에 맞게 조정:

```css
:root {
  /* 기존 RESync 변수 유지 */
  --teal: #115E59;
  --teal-dark: #134E4A;
  --teal-light: #F0FDFA;
  --ink: #0F172A;
  --smoke: #334155;
  --muted: #64748B;
  --border: #E2E8F0;

  /* shadcn 변수 — RESync 색상에 맞춤 */
  --background: 0 0% 100%;
  --foreground: 215 28% 11%;  /* ink 색상 */
  --primary: 175 70% 22%;     /* teal 색상 */
  --primary-foreground: 0 0% 100%;
  /* ... 기타 shadcn 변수 */
}
```

**Step 4: Commit**

```bash
git add components.json tailwind.config.ts app/globals.css lib/utils.ts components/ui/
git commit -m "feat: initialize shadcn/ui with Dialog and Button components"
```

---

### Task 14: RESync Kakao OAuth 콜백 + 모달

SyncWatt Task 11과 동일한 구조. 색상/문구만 RESync에 맞춤.

**Files:**
- Create: `app/auth/kakao/callback/page.tsx`
- Create: `components/KakaoLoginButton.tsx`
- Create: `components/OpeningSoonModal.tsx`
- Modify: `components/Nav.tsx`

**Step 1: 환경변수**

`.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_KAKAO_CLIENT_ID=your_kakao_rest_api_key
NEXT_PUBLIC_KAKAO_REDIRECT_URI=http://localhost:3000/auth/kakao/callback
```

**Step 2: 콜백 페이지**

SyncWatt과 동일한 구조의 `app/auth/kakao/callback/page.tsx` 생성.

**Step 3: 오픈 예정 모달 (RESync 버전)**

```tsx
// components/OpeningSoonModal.tsx
'use client'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

interface Props {
  open: boolean
  onClose: () => void
}

export function OpeningSoonModal({ open, onClose }: Props) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>가입이 완료되었습니다!</DialogTitle>
          <DialogDescription>
            RESync은 3월 중 정식 오픈 예정입니다.
            오픈 시 카카오톡으로 알림을 보내드리겠습니다.
          </DialogDescription>
        </DialogHeader>
        <Button onClick={onClose} className="w-full mt-4 bg-teal hover:bg-teal-dark">
          확인
        </Button>
      </DialogContent>
    </Dialog>
  )
}
```

**Step 4: Nav.tsx의 "카카오 가입" 버튼을 KakaoLoginButton으로 교체**

**Step 5: Commit**

```bash
git add app/auth/kakao/callback/page.tsx components/KakaoLoginButton.tsx components/OpeningSoonModal.tsx components/Nav.tsx
git commit -m "feat: add Kakao OAuth flow with opening-soon modal for RESync"
```

---

## Phase 5: 배포

### Task 15: 환경변수 K8s Secret 업데이트

**수동 작업:**

각 서비스의 K8s Secret에 환경변수 추가:

```bash
# SyncWatt
kubectl -n syncwatt-prod create secret generic syncwatt-secrets \
  --from-literal=KAKAO_CLIENT_ID=xxx \
  --from-literal=KAKAO_CLIENT_SECRET=xxx \
  --from-literal=KAKAO_REDIRECT_URI=https://syncwatt.dog-foot.com/auth/kakao/callback \
  --from-literal=JWT_SECRET_KEY=xxx \
  --dry-run=client -o yaml | kubectl apply -f -

# RESync
kubectl -n resync-prod create secret generic resync-secrets \
  --from-literal=KAKAO_CLIENT_ID=xxx \
  --from-literal=KAKAO_CLIENT_SECRET=xxx \
  --from-literal=KAKAO_REDIRECT_URI=https://resync.dog-foot.com/auth/kakao/callback \
  --from-literal=JWT_SECRET_KEY=xxx \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Task 16: 프론트엔드 환경변수

각 프론트엔드 Deployment에 환경변수 추가 (또는 ConfigMap):

```yaml
env:
  - name: NEXT_PUBLIC_API_URL
    value: "https://syncwatt-api.dog-foot.com"  # 또는 resync-api.dog-foot.com
  - name: NEXT_PUBLIC_KAKAO_CLIENT_ID
    valueFrom:
      secretKeyRef:
        name: syncwatt-secrets
        key: KAKAO_CLIENT_ID
  - name: NEXT_PUBLIC_KAKAO_REDIRECT_URI
    value: "https://syncwatt.dog-foot.com/auth/kakao/callback"
```

### Task 17: 코드 푸시 및 배포

1. 각 레포 main에 push → GitHub Actions → GHCR → k8s manifests 자동 업데이트
2. ArgoCD가 sync하여 새 이미지 배포

---

## 유저 플로우 요약

### 시나리오 1: Kakao 가입 (신규)
1. 랜딩페이지 → "카카오 가입" 클릭
2. Kakao 인증 → 콜백 → 서버에서 JWT 발급 + 유저 생성
3. "3월 중 오픈 예정입니다" 모달 표시
4. 오픈 후 → Kakao 알림톡으로 공지

### 시나리오 2: Telegram 봇 유저 (기존)
1. 텔레그램 봇과 대화 → `telegram_chat_id`로 유저 자동 생성 (이미 구현)
2. 나중에 웹에서 Kakao 가입 → 별도 유저 생성
3. 연동: 웹에서 "텔레그램 연동" → 6자리 코드 발급 → 텔레그램 봇에 `/link XXXXXX` 입력 → 계정 병합

### 시나리오 3: Kakao 가입 후 Telegram 연동
1. 웹에서 Kakao 가입 → 유저 생성
2. "텔레그램 연동" 버튼 → 6자리 코드 표시
3. 텔레그램 봇에서 `/link XXXXXX` → 같은 유저에 `telegram_chat_id` 추가
