from dotenv import load_dotenv
load_dotenv()  # 从项目根目录的.env文件加载配置
import uvicorn
import logging
import asyncio
import os
import base64
import sys
# 导入 FastAPI 相关模块
from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm

# 导入 Tortoise-ORM 相关模块
from tortoise.contrib.fastapi import register_tortoise

# 导入自定义模型模块
from models import (
    User, UserCreate, Token, PatientInfo, DoctorInfo
)

# 导入其他自定义模块
# from process_photo import process_uploaded_file
from password_hash import get_password_hash
from extra_function import authenticate_user, create_access_token, get_current_user, search_related_object, examine_status
# 重定向路由
from APP.home_page import router as home_router
from APP.appoint import router as appoint_router
from APP.add_patients_doctors import router as add_patients_doctors_router, create_patient_info, create_doctor_info
from APP.Comment import router as comment_router
from APP.doctor_operate import router as doctor_operate_router
from APP.patient_operate import router as patient_operate_router
from APP.doctor_patient_form import router as doctor_patient_form_router
from APP.MedicalRecord import router as medical_record_router
from APP.Drug_recommendation.drug_operate import router as drug_recommend_router
from APP.Predict.ali_api_yunapi_predict import router as aliyun_predict_router
# from APP.Predict.services_DeepSeek.diagnosis import router as diagnosis_router
from APP.Predict.services_xunfeixinghuo.sparkAPI import router as sparkapi_router
from APP.Predict.services_xunfeixinghuo.diagnose import router as diagnose_router
from APP.Predict.services_xunfeixinghuo.AI_chat import router as AI_chat_router

# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 将 APP 目录添加到 Python 搜索路径
app_dir = os.path.join(current_dir, 'APP')
sys.path.append(app_dir)

# 配置日志
logging.basicConfig(level=logging.DEBUG)

# 创建 FastAPI 应用实例
app = FastAPI()

# 优化后的 Tortoise-ORM 配置
TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.mysql",
            "credentials": {
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "qwertyuioP1@",
                "database": "mytestdb"
            }
        }
    },
    "apps": {
        "models": {
            "models": ["models"],
            "default_connection": "default"
        },
        "aerich": {
            "models": ["aerich.models"],
            "default_connection": "default"
        }
    }
}

# 将分路由挂到子路由上
app.include_router(home_router, prefix="/home", tags=["主页"])
app.include_router(appoint_router, prefix="/appoint", tags=["预约"])
app.include_router(add_patients_doctors_router, prefix="/add_patients_doctors", tags=["对医生或者患者进行增删改查"])
app.include_router(comment_router, prefix="/comment", tags=["社区功能"])
app.include_router(doctor_operate_router, prefix="/doctor_operate", tags=["医生就诊"])
app.include_router(patient_operate_router, prefix="/patient_operate", tags=["病人看诊"])
app.include_router(drug_recommend_router, prefix="/drug_recommend", tags=["药物推荐（暂不使用，因为太垃圾了）"])
app.include_router(doctor_patient_form_router, prefix="/doctor_patient_form", tags=["医患单"])
app.include_router(medical_record_router, prefix="/medical_record", tags=["病历"])
app.include_router(aliyun_predict_router, prefix="/aliyun_predict", tags=["阿里云预测病症（只得出结果）"])
# app.include_router(diagnosis_router, prefix="/diagnosis", tags=["医疗诊断病症分析"])
app.include_router(sparkapi_router, prefix="/sparkapi", tags=["病症分析（输入病症名称，进行病症分析）"])
app.include_router(diagnose_router, prefix="/diagnose", tags=["预测病症＋生成病历（诊病＋分析病＋个性化药物推荐）"])
app.include_router(AI_chat_router, prefix="/ai_chat", tags=["AI助手智能问答"])

# 注册用户
@app.post("/register", operation_id="unique_register_user_operation", tags=["注册账号"])
async def register_user(user_in: UserCreate):
    """
        用户注册接口，接收用户创建信息，对密码进行哈希处理后存入数据库
        :param user_in: 用户创建信息
        :return: 用户信息
        """
    try:
        # 计算一个加密的密码，把这个加密后的密码，存入数据库
        hashed_password = get_password_hash(user_in.password)
        user_obj = User(phone_number=user_in.phone_number, hashed_password=hashed_password)
        await user_obj.save()
        phone_number = user_obj.phone_number
        user_id = user_obj.id
        user_1 = {"phone_number": phone_number, "id": user_id}

        return {"code": 200, "data": user_1}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 用户登录路由，接收 OAuth2PasswordRequestForm 类型的数据，返回 Token 类型的响应
@app.post("/token", response_model=Token, tags=["登录账号"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
       用户登录接口，接收用户名和密码进行验证，验证通过后生成并返回访问令牌
       :param form_data: OAuth2 密码请求表单数据
       :return: 访问令牌和令牌类型
       """
    try:
        # 对用户进行身份验证
        user = await authenticate_user(form_data.username, form_data.password)
        # 如果用户验证失败，抛出 401 错误
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect phone_number or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # 创建访问令牌，将用户名存储在令牌的 "sub" 字段中
        access_token = create_access_token(data={"sub": user.phone_number})  # 修改为 user.phone_number
        # 返回访问令牌和令牌类型
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))




async def process_uploaded_file(file: UploadFile) -> bytes:
    try:
        # 直接读取文件内容为bytes
        content = await file.read()
        return content
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件处理失败: {str(e)}"
        )


@app.post("/user_image", tags=["添加或更新账户头像"])
async def update_user_image(
    user: User = Depends(get_current_user),
    image: UploadFile = File(...)
):
    try:
        image_content = await image.read()  # 直接读取二进制内容
        image_base64 = base64.b64encode(image_content).decode('utf-8')

        user.image = image_content
        await user.save()

        user_data = {
            "id": user.id,
            "phone_number": user.phone_number,
            "image": image_base64
        }

        return {"code": 200, "data": user_data}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"服务器内部错误: {str(e)}"
        )

# 选择身份路由
@app.post("/select_identity/", tags=["选择身份"])
async def select_identity(current_user: User = Depends(get_current_user), identity: str = None):
    """
    选择身份接口，根据用户选择的身份类型，返回相应的信息
    :param current_user: 当前用户信息
    :param identity: 用户选择的身份类型
    :return: 相应的信息
    """

    if identity == "patient":
        print(f"create_patient_info executing!")
        if current_user.patient:
            filter_condition1 = {'phone_number': current_user.phone_number} if current_user.phone_number else None
            result = await search_related_object(current_user, 'patient', filter_condition1)
            current_user.patient_status = True
            current_user.doctor_status = False
            await current_user.save()
            return {"code": 200, "data": result}
        # 创建一条病人信息
        ex = PatientInfo()
        await create_patient_info(current_user, ex)
        filter_condition1 = {'phone_number': current_user.phone_number} if current_user.phone_number else None
        result = await search_related_object(current_user, 'patient', filter_condition1)
        current_user.patient_status = True
        current_user.doctor_status = False
        await current_user.save()
        return {"code": 200, "data": result}
    elif identity == "doctor":
        if current_user.doctor:
            filter_condition1 = {'phone_number': current_user.phone_number} if current_user.phone_number else None
            result = await search_related_object(current_user, 'doctor', filter_condition1)
            current_user.patient_status = False
            current_user.doctor_status = True
            await current_user.save()
            return {"code": 200, "data": result}
        # 创建一条医生信息
        ex1 = DoctorInfo()
        await create_doctor_info(current_user, ex1)
        filter_condition = {'phone_number': current_user.phone_number} if current_user.phone_number else None
        result = await search_related_object(current_user, 'doctor', filter_condition)
        current_user.patient_status = False
        current_user.doctor_status = True
        await current_user.save()
        return {"code": 200, "data": result}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid identity type")


# 切换身份接口
@app.post("/switch_identity/", tags=["切换身份"])
async def switch_identity(current_user: User = Depends(get_current_user)):
    """
    切换身份接口，将用户的身份从患者切换到医生，或者从医生切换到患者
    :param current_user: 当前用户信息
    :return: 切换后的身份信息
    """
    result = examine_status(current_user)
    if not result:
        return {"code": 400, "data": "Invalid status"}
    current_user.patient_status = not current_user.patient_status
    current_user.doctor_status = not current_user.doctor_status
    await current_user.save()
    if current_user.patient_status:
        filter_condition1 = {'phone_number': current_user.phone_number} if current_user.phone_number else None
        result = await search_related_object(current_user, 'patient', filter_condition1)
    else:
        filter_condition2 = {'phone_number': current_user.phone_number} if current_user.phone_number else None
        result = await search_related_object(current_user, 'doctor', filter_condition2)
    return {"code": 200, "data": result}


# 退出登录接口
@app.post("/logout", tags=["退出登录"])
async def logout(current_user: User = Depends(get_current_user)):
    """
    退出登录接口，将用户的身份状态重置为默认值
    :param current_user: 当前用户信息
    :return: 退出登录成功信息
    """
    current_user.patient_status = False
    current_user.doctor_status = False
    await current_user.save()
    return {"code": 200, "data": "Logged out successfully"}


register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=False,
    add_exception_handlers=True,
)
if __name__ == "__main__":
    try:
        uvicorn.run(app=app, host="0.0.0.0",port=8000)
    except KeyboardInterrupt:
        print("Server is shutting down...")
    except asyncio.exceptions.CancelledError:
        pass  # 忽略取消异常