from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import timedelta

from database import get_db, User
from auth import (
    authenticate_user, create_access_token, get_password_hash,
    create_captcha_session, verify_captcha, get_current_user
)
from schemas import (
    UserCreate, UserLogin, UserResponse, Token, CaptchaResponse, MessageResponse
)
from config import settings

router = APIRouter()

def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

@router.get("/captcha", response_model=CaptchaResponse)
async def get_captcha(request: Request, db: Session = Depends(get_db)):
    """获取图形验证码"""
    client_ip = get_client_ip(request)
    session_id, image_data = create_captcha_session(db, client_ip)
    
    return CaptchaResponse(
        session_id=session_id,
        image_data=image_data
    )

@router.post("/register", response_model=UserResponse)
async def register_user(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """用户注册"""
    client_ip = get_client_ip(request)
    
    # 验证验证码
    if not verify_captcha(db, user_data.captcha_session_id, user_data.captcha_code, client_ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid captcha code"
        )
    
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.post("/login", response_model=Token)
async def login_user(
    request: Request,
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """用户登录"""
    client_ip = get_client_ip(request)
    
    # 验证验证码
    if not verify_captcha(db, user_data.captcha_session_id, user_data.captcha_code, client_ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid captcha code"
        )
    
    # 认证用户
    user = authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        user=UserResponse.from_orm(user)
    )

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user

@router.post("/logout", response_model=MessageResponse)
async def logout_user():
    """用户登出（前端处理token删除）"""
    return MessageResponse(message="Successfully logged out")

@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    email: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户资料"""
    # 检查邮箱是否已被其他用户使用
    existing_user = db.query(User).filter(
        User.email == email,
        User.id != current_user.id
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use by another user"
        )
    
    current_user.email = email
    db.commit()
    db.refresh(current_user)
    
    return current_user