import logging
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlmodel import Session, select
import httpx
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_session
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_URL = "https://kapi.kakao.com/v2/user/me"

PLAN_HIERARCHY = ["free", "standard", "pro"]


class KakaoCallbackRequest(BaseModel):
    code: str


class LinkVerifyRequest(BaseModel):
    telegram_chat_id: str
    code: str


@router.get("/kakao/login")
async def kakao_login():
    auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={settings.KAKAO_CLIENT_ID}"
        f"&redirect_uri={settings.KAKAO_REDIRECT_URI}"
        f"&response_type=code"
    )
    return {"auth_url": auth_url}


@router.post("/kakao/callback")
async def kakao_callback(body: KakaoCallbackRequest, session: Session = Depends(get_session)):
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(KAKAO_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "client_id": settings.KAKAO_CLIENT_ID,
            "client_secret": settings.KAKAO_CLIENT_SECRET,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "code": body.code,
        })
        if token_resp.status_code != 200:
            logger.error(f"Kakao token error: {token_resp.text}")
            raise HTTPException(status_code=400, detail="Kakao 인증 실패")
        kakao_token = token_resp.json()["access_token"]

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

    user = session.exec(select(User).where(User.kakao_id == kakao_id)).first()
    if not user:
        user = User(kakao_id=kakao_id, kakao_nickname=nickname, kakao_email=email)
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info(f"New Kakao user created: {user.user_id} ({nickname})")
    else:
        user.kakao_nickname = nickname
        user.kakao_email = email
        session.add(user)
        session.commit()

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
async def get_me(user: User = Depends(get_current_user)):
    return {
        "user_id": user.user_id,
        "nickname": user.kakao_nickname,
        "is_telegram_linked": user.telegram_chat_id is not None,
        "plan": user.plan,
    }


@router.post("/link/generate-code")
async def generate_link_code(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user.telegram_chat_id:
        return {"message": "이미 텔레그램이 연결되어 있습니다", "linked": True}

    # 충돌 시 재시도 (unique constraint)
    for _ in range(3):
        code = secrets.token_hex(6).upper()  # 12자리 hex
        existing = session.exec(select(User).where(User.link_code == code)).first()
        if not existing:
            break
    else:
        raise HTTPException(status_code=500, detail="코드 생성 실패, 다시 시도해주세요")

    user.link_code = code
    user.link_code_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    session.add(user)
    session.commit()
    return {"code": code, "expires_in": 600}


@router.post("/link/verify")
async def verify_link_code(
    body: LinkVerifyRequest,
    x_webhook_secret: str = Header(alias="X-Webhook-Secret"),
    session: Session = Depends(get_session),
):
    # Telegram 봇에서만 호출 가능하도록 시크릿 검증
    if x_webhook_secret != settings.WEBHOOK_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    kakao_user = session.exec(
        select(User).where(User.link_code == body.code.upper())
    ).first()
    if not kakao_user or not kakao_user.link_code_expires:
        raise HTTPException(status_code=400, detail="유효하지 않은 코드입니다")
    if datetime.now(timezone.utc) > kakao_user.link_code_expires.replace(tzinfo=timezone.utc):
        raise HTTPException(status_code=400, detail="만료된 코드입니다")

    telegram_user = session.exec(
        select(User).where(User.telegram_chat_id == body.telegram_chat_id)
    ).first()
    if telegram_user and telegram_user.user_id != kakao_user.user_id:
        # 계정 병합: Kakao 유저로 통합
        kakao_user.telegram_chat_id = body.telegram_chat_id
        kakao_user.phone = kakao_user.phone or telegram_user.phone

        # plan 병합 — 방어적으로 처리
        kakao_idx = PLAN_HIERARCHY.index(kakao_user.plan) if kakao_user.plan in PLAN_HIERARCHY else 0
        tg_idx = PLAN_HIERARCHY.index(telegram_user.plan) if telegram_user.plan in PLAN_HIERARCHY else 0
        kakao_user.plan = PLAN_HIERARCHY[max(kakao_idx, tg_idx)]

        kakao_user.plant_count = max(kakao_user.plant_count, telegram_user.plant_count)

        # TODO: 향후 FK 연결된 테이블(Plant, Settlement 등) 추가 시
        # 여기서 telegram_user.user_id → kakao_user.user_id 로 레코드 이관 필요
        # 예: session.exec(update(Plant).where(Plant.user_id == telegram_user.user_id).values(user_id=kakao_user.user_id))

        session.delete(telegram_user)
    else:
        kakao_user.telegram_chat_id = body.telegram_chat_id

    kakao_user.link_code = None
    kakao_user.link_code_expires = None
    session.add(kakao_user)
    session.commit()
    return {"message": "계정이 연동되었습니다", "user_id": kakao_user.user_id}
