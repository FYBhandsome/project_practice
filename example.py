# 代码教程
'''
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

# 创建一个 FastAPI 应用实例
app = FastAPI()

# 从环境变量中获取密钥，若未获取到则使用默认的 "your_secret_key"，用于 JWT 的签名
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
# 从环境变量中获取算法，若未获取到则使用默认的 "HS256"，JWT 签名和验证使用的算法
ALGORITHM = os.getenv("ALGORITHM", "HS256")
# 定义访问令牌的过期时间为 30 分钟
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 创建密码加密的上下文，使用 bcrypt 算法，并自动处理过时的加密算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 定义用户数据模型，包含用户名和加密后的密码
class User(BaseModel):
    username: str
    hashed_password: str

# 定义用户创建时的数据模型，包含用户名和明文密码
class UserCreate(BaseModel):
    username: str
    password: str

# 定义用户登录成功后返回的令牌数据模型，包含访问令牌和令牌类型
class Token(BaseModel):
    access_token: str
    token_type: str

# OAuth2 密码授权模式，指定获取令牌的 URL 为 "token"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 验证明文密码和加密后的密码是否匹配
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# 对明文密码进行加密操作
def get_password_hash(password):
    return pwd_context.hash(password)

# 创建访问令牌，包含用户信息和过期时间
def create_access_token(data: dict):
    # 复制传入的数据，避免修改原始数据
    to_encode = data.copy()
    # 计算令牌的过期时间
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # 将过期时间添加到要编码的数据中
    to_encode.update({"exp": expire})
    # 使用 jwt 模块对数据进行编码，生成 JWT 令牌
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 从数据库中查找用户，这里仅为简单示例，实际应用中应从数据库中查询
async def get_user(username: str):
    # 如果用户名是 "test_user"，则创建一个示例用户，对其密码进行加密存储
    if username == "test_user":
        return User(username=username, hashed_password=pwd_context.hash("test_password"))
    # 未找到用户，返回 None
    return None

# 对用户进行身份验证，检查用户名和密码是否正确
async def authenticate_user(username: str, password: str):
    # 调用 get_user 函数查找用户
    user = await get_user(username)
    # 如果用户不存在，返回 False
    if not user:
        return False
    # 验证密码是否正确，如果不正确返回 False
    if not verify_password(password, user.hashed_password):
        return False
    # 用户名和密码都正确，返回用户对象
    return user

# 用户注册路由，接收 UserCreate 类型的数据，返回 User 类型的响应
@app.post("/register", response_model=User)
async def register(user: UserCreate):
    # 对用户输入的密码进行加密
    hashed_password = get_password_hash(user.password)
    # 创建一个新用户对象，包含用户名和加密后的密码
    new_user = User(username=user.username, hashed_password=hashed_password)
    # 这里应将新用户存储到数据库中，目前仅为示例，未进行存储操作
    return new_user

# 用户登录路由，接收 OAuth2PasswordRequestForm 类型的数据，返回 Token 类型的响应
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # 对用户进行身份验证
    user = await authenticate_user(form_data.username, form_data.password)
    # 如果用户验证失败，抛出 401 错误
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 创建访问令牌，将用户名存储在令牌的 "sub" 字段中
    access_token = create_access_token(data={"sub": user.username})
    # 返回访问令牌和令牌类型
    return {"access_token": access_token, "token_type": "bearer"}

# 获取当前用户信息，依赖于 oauth2_scheme 获取令牌
async def get_current_user(token: str = Depends(oauth2_scheme)):
    # 定义异常，当无法验证凭据时抛出
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解码 JWT 令牌
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # 获取存储在令牌 "sub" 字段中的用户名
        username: str = payload.get("sub")
        # 如果用户名不存在，抛出异常
        if username is None:
            raise credentials_exception
        # 根据用户名查找用户
        user = await get_user(username)
        # 如果用户不存在，抛出异常
        if user is None:
            raise credentials_exception
        # 返回用户对象
        return user
    # 处理 JWT 解码错误，抛出异常
    except JWTError:
        raise credentials_exception

# 获取当前用户信息的路由，依赖于 get_current_user 函数
@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    # 返回当前用户信息
    return current_user
'''