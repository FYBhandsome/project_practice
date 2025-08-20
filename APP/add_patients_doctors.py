import traceback
import os
from extra_function import get_current_user, search_patient, search_doctor
from fastapi import Depends, Body, File, UploadFile
# 导入自定义模型模块
from models import (
    User, PatientInfo, DoctorInfo
)
from fastapi import APIRouter, HTTPException, status
from tortoise.contrib.pydantic import pydantic_model_creator
from models import Doctor, Patient
import logging
import base64
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from models import Patient, Doctor
from extra_function import search_patient, search_doctor
# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 创建 Pydantic 模型用于序列化 Patient 对象
Patient_Pydantic = pydantic_model_creator(Patient, name="Patient")
# 创建 Pydantic 模型用于序列化 Doctor 对象
Doctor_Pydantic = pydantic_model_creator(Doctor, name="Doctor")
# 封装函数，处理文件上传并返回二进制数据
async def process_uploaded_file(file: UploadFile):
    if not allowed_file(file.filename):
        raise HTTPException(400, "文件类型不支持")
    try:
        content = await file.read()
        return content
    except Exception as e:
        raise HTTPException(500, f"读取文件时出错: {str(e)}")


# 创建病人信息的路由，依赖于 get_current_user 函数和 select_identity 函数
@router.post("/create_patient_info/", summary="添加患者信息")
async def create_patient_info(current_user: User = Depends(get_current_user),
                              patientinfo: PatientInfo = Body(...)):
    """
    创建患者信息接口，根据用户信息和传入的患者信息创建患者记录
    :param current_user: 当前用户信息
    :param patientinfo: 患者信息
    :return: 创建的患者记录信息
    """
    try:
        # 日志记录请求体信息，方便调试
        # logging.debug(f"Received patient info: {patientinfo.dict()}")
        patient = await Patient.create(
            name=patientinfo.name,
            age=patientinfo.age,
            gender=patientinfo.gender,
            id_card=patientinfo.id_card,
            marital_status=patientinfo.marital_status,
            ethnicity=patientinfo.ethnicity,
            residence=patientinfo.residence,
            birth_date=patientinfo.birth_date,
            phone_number=current_user.phone_number
        )
        current_user.patient = patient
        await current_user.save()
        return {"code": 200, "data": patient}
    except Exception as e:
        logging.error(f"Error creating patient info: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 创建医生信息的路由，依赖于 get_current_user 函数和 select_identity 函数
@router.post("/create_doctor_info/", summary="添加医生信息")
async def create_doctor_info(current_user: User = Depends(get_current_user),
                             doctorinfo: DoctorInfo = Body(...)):
    """
    创建医生信息接口，根据用户信息和传入的医生信息创建医生记录
    :param current_user: 当前用户信息
    :param doctorinfo: 医生信息
    :return: 创建的医生记录信息
    """
    profession_number = f"{current_user.phone_number}{doctorinfo.working_years}"
    doctor = await Doctor.create(
        name=doctorinfo.name,
        profession_number=profession_number,
        working_years=doctorinfo.working_years,
        phone_number=current_user.phone_number,
        gender=doctorinfo.gender,
        hospital=doctorinfo.hospital,
        title=doctorinfo.title,
        registration_fee=doctorinfo.registration_fee,
        introduction=doctorinfo.introduction,
        expertise=doctorinfo.expertise,
        payment_qr_code=doctorinfo.payment_qr_code
    )
    current_user.doctor = doctor
    await current_user.save()
    return {"code": 200, "data": doctor}


# 获取病人信息的路由，依赖于 search_patient 函数，默认获取当前病人信息路由
@router.get("/patient_info/", summary="获取患者信息")
async def get_current_patient_info(current_patient: Patient = Depends(search_patient)):
    """
    获取当前病人信息接口，根据当前用户信息查询患者信息
    :param current_patient: 当前患者信息
    :return: 患者信息
    """
    try:
        # 将 Patient 对象转换为 Pydantic 模型实例
        result = await Patient_Pydantic.from_tortoise_orm(current_patient)
        data_dict = {"id": result.id, "name": result.name, "age": result.age,
                     "id_card": result.id_card, "gender": result.gender,
                     "marital_status": result.marital_status, "ethnicity": result.ethnicity,
                     "residence": result.residence, "birth_date": result.birth_date,
                     "phone_number": result.phone_number, "image": result.image}
        return {"code": 200, "data": data_dict}
    except Exception as e:
        # 记录详细的错误信息
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Error serializing patient information: {str(e)}")


# 获取当前医生信息的路由，依赖于 get_current_user 函数
@router.post("/doctor_info/", summary="添加医生信息", response_model=DoctorInfo)
async def get_current_doctor_info(current_doctor: Doctor = Depends(search_doctor)):
    """
    获取当前医生信息接口，根据当前用户信息查询医生信息
    :param current_doctor: 当前医生信息
    :return: 医生信息
    """

    return {"code": 200, "data": current_doctor}


# 获取当前医生信息的路由，依赖于 get_current_user 函数
@router.get("/doctor/{doctor_id}/", summary="添加医生信息")
async def get_current_doctor_info(current_user: User = Depends(get_current_user), doctor_id: int = None):
    """
    获取当前医生信息接口，根据当前用户信息查询医生信息
    :param current_user: 当前用户信息
    :return: 医生信息
    """
    try:
        # 根据 doctor_id 获取医生信息
        result = await Doctor.get(id=doctor_id)

        # 使用点号访问属性来构建数据字典
        data_dict = {
            "id": result.id,
            "name": result.name,
            "profession_number": result.profession_number,
            "working_years": result.working_years,
            "phone_number": result.phone_number,
            "gender": result.gender,
            "hospital": result.hospital,
            "title": result.title,
            "registration_fee": result.registration_fee,
            "introduction": result.introduction,
            "expertise": result.expertise,
            "payment_qr_code": result.payment_qr_code,
            "image": result.image,
            "appointment_count": result.appointment_count
        }

        return {"code": 200, "data": data_dict}
    except Doctor.DoesNotExist:
        # 若医生信息不存在，返回 404 错误
        return {"code": 404, "data": {"message": "Doctor not found"}}
    except Exception as e:
        # 处理其他异常，返回 500 错误
        return {"code": 500, "data": {"message": f"An error occurred: {str(e)}"}}


# 更新患者信息的路由
@router.put("/update_patient_info/", summary="更新患者信息")
async def update_patient_info(current_user: User = Depends(get_current_user),
                              patientinfo: PatientInfo = Body(...)):
    """
    更新患者信息接口，根据用户信息和传入的患者信息更新患者记录
    :param current_user: 当前用户信息
    :param patientinfo: 患者信息
    :return: 更新后的患者记录信息
    """
    try:
        patient = await current_user.patient
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

        # 遍历传入的患者信息，只更新有值的字段
        for field, value in patientinfo.dict(exclude_unset=True).items():
            if value is not None:
                setattr(patient, field, value)

        await patient.save()
        return {"code": 200, "data": patient}
    except Exception as e:
        print(f"Error updating patient info: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 更新医生信息的路由
@router.put("/update_doctor_info/", summary="更新患者信息")
async def update_doctor_info(current_user: User = Depends(get_current_user),
                             doctorinfo: DoctorInfo = Body(...)):
    """
    更新医生信息接口，根据用户信息和传入的医生信息更新医生记录
    :param current_user: 当前用户信息
    :param doctorinfo: 医生信息
    :return: 更新后的医生记录信息
    """
    try:
        doctor = await current_user.doctor
        if not doctor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

        # 遍历传入的医生信息，只更新有值的字段
        for field, value in doctorinfo.dict(exclude_unset=True).items():
            if field == 'profession_number' and field != 'image':
                value = f"{doctorinfo.phone_number}{doctorinfo.working_years}"
            if field == 'image':
                # 将二进制图片数据转换为 Base64 编码的字符串
                value = base64.b64encode(value).decode('utf-8')
            setattr(doctor, field, value)

        await doctor.save()
        return {"code": 200, "data": doctor}
    except Exception as e:
        print(f"Error updating doctor info: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 封装将 Doctor_Pydantic 对象转换为字典的函数
def doctor_to_dict(doctor):
    return {
        "id": doctor.id,
        "name": doctor.name,
        "hospital": doctor.hospital,
        "title": doctor.title,
        "introduction": doctor.introduction,
        "expertise": doctor.expertise,
        "image": doctor.image
    }


# 获取所有医生信息的列表
@router.get("/doctors_list/", summary="获取所有医生信息")
async def get_doctor_list(hospital: str = None, grade: str = None, phone_number: str = None, id: str = None):
    try:
        query_conditions = {}
        if hospital:
            query_conditions["hospital"] = hospital
        if grade:
            query_conditions["grade"] = grade
        if phone_number:
            query_conditions["phone_number"] = phone_number
        if id:
            query_conditions["id"] = id

        if not query_conditions:
            doctor_list = await Doctor.all()
        else:
            doctor_list = await Doctor.filter(**query_conditions)

        serialized_doctor_list = [await Doctor_Pydantic.from_tortoise_orm(doctor) for doctor in doctor_list]
        data_list = [doctor_to_dict(item) for item in serialized_doctor_list]
        return {"code": 200, "data": data_list}
    except Exception as e:
        logger.error(f"Error retrieving doctor list: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 获取所有患者列表的路由
@router.get("/patients_list/", summary="获取所有患者信息")
async def get_patients_list():
    """
    获取所有患者列表接口
    :return: 所有患者信息列表
    """
    try:
        patients = await Patient.all()
        serialized_patients = [await Patient_Pydantic.from_tortoise_orm(patient) for patient in patients]
        return {"code": 200, "data": serialized_patients}
    except Exception as e:
        logger.error(f"Error retrieving patient list: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 假设这是允许的文件类型检查函数
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS




# 更新病人头像
@router.put("/patient_image", summary="更新患者头像")
async def update_user_image(current_patient: Patient = Depends(search_patient), image: UploadFile = File(...)):
    """
        更新用户头像接口，接收用户信息和头像数据，更新用户的头像信息
        :param current_patient: 用户信息
        :param image: 头像数据
        :return: 更新后的用户信息
        """
    try:
        image_content = await process_uploaded_file(image)
        current_patient.image = image_content
        await current_patient.save()

        # 将二进制图片数据转换为 Base64 编码的字符串
        image_base64 = base64.b64encode(image_content).decode('utf-8')

        # 构建返回的用户信息，使用 Base64 编码的图片数据
        patient_data = {
            "id": current_patient.id,
            # 假设患者模型还有其他字段，根据实际情况添加
            "name": current_patient.name,
            "image": image_base64
        }

        return {"code": 200, "data": patient_data}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 更新医生头像
@router.put("/doctor_image", summary="更新医生头像")
async def update_user_image(current_doctor: Doctor = Depends(search_doctor), image: UploadFile = File(...)):
    """
        更新用户头像接口，接收用户信息和头像数据，更新用户的头像信息
        :param current_doctor: 用户信息
        :param image: 头像数据
        :return: 更新后的用户信息
        """
    try:
        image_content = await process_uploaded_file(image)
        current_doctor.image = image_content
        await current_doctor.save()

        # 将二进制图片数据转换为 Base64 编码的字符串
        image_base64 = base64.b64encode(image_content).decode('utf-8')

        # 构建返回的用户信息，使用 Base64 编码的图片数据
        doctor_data = {
            "id": current_doctor.id,
            # 假设医生模型还有其他字段，根据实际情况添加
            "name": current_doctor.name,
            "image": image_base64
        }

        return {"code": 200, "data": doctor_data}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
