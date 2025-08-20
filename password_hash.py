
from passlib.context import CryptContext
# 创建密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def get_password_hash(password):
    # 生成密码的哈希值
    return pwd_context.hash(password)
def verify_password(plain_password, hashed_password):
    # 验证密码是否匹配
    return pwd_context.verify(plain_password, hashed_password)


if __name__ == "__main__":
    # 生成密码 '123456' 的哈希值
    hashed_password_1 = get_password_hash('123456')
    print(hashed_password_1)
    # 验证密码 '123456' 是否与生成的哈希值匹配
    print(verify_password('123456', hashed_password_1))
    # 生成密码 'abc123' 的哈希值
    hashed_password_2 = get_password_hash('abc123')
    print(hashed_password_2)
    # 验证密码 'abc123' 是否与生成的哈希值匹配
    print(verify_password('abc123', hashed_password_2))

