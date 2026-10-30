from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.deps import REFRESH_COOKIE, DbDep, SettingsDep
from app.core.ratelimit import client_ip, hit, ip_limit

from . import service
from .schemas import LoginRequest, RegisterRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=UserOut, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ip_limit("register", 10, 3600))],
)
async def register(body: RegisterRequest, db: DbDep) -> UserOut:
    user = await service.register(db, body.email, body.password, body.display_name)
    return UserOut.model_validate(user)


@router.post("/login", response_model=UserOut, dependencies=[Depends(ip_limit("login", 30, 300))])
async def login(body: LoginRequest, request: Request, response: Response, db: DbDep, settings: SettingsDep) -> UserOut:
    await hit(f"login:email:{body.email.lower()}:{client_ip(request)}", 8, 300)
    user, access, refresh = await service.login(db, settings, body.email, body.password)
    service.set_auth_cookies(response, settings, access, refresh)
    return UserOut.model_validate(user)


@router.post("/refresh", response_model=UserOut, dependencies=[Depends(ip_limit("refresh", 60, 300))])
async def refresh(request: Request, response: Response, db: DbDep, settings: SettingsDep) -> UserOut:
    user, access, new_refresh = await service.refresh(db, settings, request.cookies.get(REFRESH_COOKIE))
    service.set_auth_cookies(response, settings, access, new_refresh)
    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, db: DbDep) -> None:
    await service.logout(db, request.cookies.get(REFRESH_COOKIE))
    service.clear_auth_cookies(response)
