import os
from models import User
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, Depends, status
from dotenv import load_dotenv

load_dotenv()
# 从环境变量中获取密钥，若未获取到则使用默认的 "your_secret_key"，用于 JWT 的签名
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
# 从环境变量中获取算法，若未获取到则使用默认的 "HS256"，JWT 签名和验证使用的算法
ALGORITHM = os.getenv("ALGORITHM", "HS256")
# 定义访问令牌的过期时间为 30 分钟
ACCESS_TOKEN_EXPIRE_MINUTES = 3600
# 创建密码加密的上下文，使用 bcrypt 算法，并自动处理过时的加密算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# OAuth2 密码授权模式，指定获取令牌的 URL 为 "token"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# 对用户进行身份验证，检查用户名和密码是否正确
async def authenticate_user(phone_number: str, password: str):
    user = await User.get_or_none(phone_number=phone_number)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


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
        phone_number: str = payload.get("sub")
        # 如果用户名不存在，抛出异常
        if phone_number is None:
            raise credentials_exception
        # 根据用户名查找用户，并预加载关联的 doctor 和 patient 对象
        user = await User.filter(phone_number=phone_number).prefetch_related('doctor', 'patient').first()
        # 如果用户不存在，抛出异常
        if user is None:
            raise credentials_exception
        # 返回用户对象
        return user
    # 处理 JWT 解码错误，抛出异常
    except JWTError:
        raise credentials_exception


# 封装日期转换函数
# def convert_date(date_str):
#     """
#     将日期字符串转换为日期对象
#     :param date_str: 日期字符串，格式为 'YYYY年MM月DD日'
#     :return: 日期对象
#     """
#     try:
#         if date_str is None:
#             date_str = "2000年01月01日"
#         return datetime.strptime(date_str, '%Y年%m月%d日').date()
#     except ValueError:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
#                             detail="Invalid date format. Please use 'YYYY年MM月DD日'.")



# 封装搜索关联对象函数
async def search_related_object(user, relation_name, filter_condition):
    print(f"User object: {user}\nuser.phone_number:{user.phone_number}")  # 打印 user 对象信息
    relation_name = relation_name.lower()
    print(f"Relation name: {relation_name}")  # 打印关联关系名称

    # 获取关联属性
    related_attr = getattr(user, relation_name, None)
    if related_attr is None:
        error_msg = f"{relation_name.capitalize()} relation not found for user"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)

    # 异步获取关联对象
    related_obj = await related_attr

    print(f"Related object: {related_obj}")  # 打印关联对象信息
    if related_obj and filter_condition:
        for key, value in filter_condition.items():
            if getattr(related_obj, key, None) != value:
                related_obj = None
                break
    if not related_obj:
        error_msg = f"{relation_name.capitalize()} not found"
        if filter_condition:
            error_msg += f" with conditions {filter_condition}"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
    return related_obj

# 搜索病人信息函数
async def search_patient(user: User = Depends(get_current_user), phone_number: str = None):
    """
    搜索病人信息接口，根据当前用户信息查询患者信息
    :param user: 当前用户信息
    :param phone_number: 患者电话号码
    :return: 患者信息
    """
    if not phone_number:
        phone_number = user.phone_number
    filter_condition = {'phone_number': phone_number} if phone_number else None
    print(f"filter_condition: {filter_condition}")
    return await search_related_object(user, 'patient', filter_condition)


async def search_doctor(user: User = Depends(get_current_user), phone_number: str = None):
    """
    搜索医生信息接口，根据当前用户信息查询医生信息
    :param user: 当前用户信息
    :param phone_number: 医生电话号码
    :return: 医生信息
    """
    if not phone_number:
        phone_number = user.phone_number
    return await search_related_object(user, 'doctor', {'phone_number': phone_number})

async def recogonise_identity(user: User = Depends(get_current_user)):
    if user.patient_status:
        return await search_patient(user)

    if user.doctor_status:
        return await search_doctor(user)

# 检查登录状态
async def examine_status(user: User = Depends(get_current_user)):
    if (user.patient_status != user.doctor_status):
        return True
    else:
        return False