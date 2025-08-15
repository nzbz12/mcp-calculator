from datetime import datetime, timedelta
from typing import Optional
import uuid
import random
import string
from io import BytesIO
import base64

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from PIL import Image, ImageDraw, ImageFont
import sqlalchemy.orm as orm

from config import settings
from database import get_db, User, CaptchaSession

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Token Bearer
security = HTTPBearer()

# 密码验证和哈希
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

# JWT Token处理
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None

# 用户认证
def authenticate_user(db: orm.Session, username: str, password: str) -> Optional[User]:
    """认证用户"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: orm.Session = Depends(get_db)
) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return user

def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前管理员用户"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

# 验证码生成
class CaptchaGenerator:
    """图形验证码生成器"""
    
    def __init__(self):
        self.width = settings.captcha_width
        self.height = settings.captcha_height
        self.length = settings.captcha_length
        
    def generate_code(self) -> str:
        """生成验证码字符串"""
        # 使用数字和大写字母，排除容易混淆的字符
        chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
        return ''.join(random.choices(chars, k=self.length))
    
    def create_image(self, code: str) -> str:
        """创建验证码图片，返回base64编码"""
        # 创建图片
        image = Image.new('RGB', (self.width, self.height), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # 尝试加载字体，如果失败使用默认字体
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
        
        # 绘制干扰线
        for _ in range(5):
            x1 = random.randint(0, self.width)
            y1 = random.randint(0, self.height)
            x2 = random.randint(0, self.width)
            y2 = random.randint(0, self.height)
            draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200), width=1)
        
        # 绘制字符
        char_width = self.width // self.length
        for i, char in enumerate(code):
            x = i * char_width + random.randint(5, 15)
            y = random.randint(5, 15)
            color = (
                random.randint(0, 150),
                random.randint(0, 150),
                random.randint(0, 150)
            )
            draw.text((x, y), char, fill=color, font=font)
        
        # 添加噪点
        for _ in range(100):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
        
        # 转换为base64
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"

def create_captcha_session(db: orm.Session, ip_address: str) -> tuple[str, str]:
    """创建验证码会话"""
    generator = CaptchaGenerator()
    code = generator.generate_code()
    session_id = str(uuid.uuid4())
    
    # 清除过期的验证码会话
    expired_time = datetime.utcnow()
    db.query(CaptchaSession).filter(CaptchaSession.expires_at < expired_time).delete()
    
    # 创建新的验证码会话
    captcha_session = CaptchaSession(
        id=session_id,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=5),  # 5分钟过期
        ip_address=ip_address
    )
    db.add(captcha_session)
    db.commit()
    
    # 生成图片
    image_data = generator.create_image(code)
    
    return session_id, image_data

def verify_captcha(db: orm.Session, session_id: str, code: str, ip_address: str) -> bool:
    """验证验证码"""
    # 查找验证码会话
    session = db.query(CaptchaSession).filter(
        CaptchaSession.id == session_id,
        CaptchaSession.ip_address == ip_address
    ).first()
    
    if not session:
        return False
    
    # 检查是否过期
    if session.expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()
        return False
    
    # 检查是否已使用
    if session.used:
        return False
    
    # 验证码码（不区分大小写）
    is_valid = session.code.upper() == code.upper()
    
    if is_valid:
        # 标记为已使用
        session.used = True
        db.commit()
    
    return is_valid