import base64
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body
from tortoise.contrib.pydantic import pydantic_model_creator
from models import (
    User, Patient, Doctor, MedicalRecordInfo, MedicalRecord, DoctorPatientForm
)
from extra_function import get_current_user, search_patient
from fastapi import UploadFile, File
from process_photo import process_uploaded_file

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 Pydantic 模型
Doctor_Pydantic = pydantic_model_creator(Doctor, name="Doctor")
MedicalRecord_Pydantic = pydantic_model_creator(MedicalRecord)

# 自定义 Pydantic 模型，用于处理查询结果中的 image 字段
class MedicalRecordResponse(MedicalRecord_Pydantic):
    image: Optional[str] = None

    @classmethod
    def from_orm(cls, obj):
        # 先将 image 字段转换为 Base64 编码的字符串
        if obj.image:
            try:
                obj.image = base64.b64encode(obj.image).decode('utf-8')
            except Exception as e:
                logger.error(f"Base64 编码图片数据时出错: {e}")
                obj.image = None

        # 再调用父类的 from_orm 方法
        record = super().from_orm(obj)
        return record

router = APIRouter()


# 提取创建病历信息的通用逻辑
async def create_medical_record(user_model, user_type, result: MedicalRecordInfo, image_content: bytes = None):
    """
    创建病历信息的通用逻辑
    :param user_model: 用户模型（Patient 或 Doctor）
    :param user_type: 用户类型（"patient" 或 "doctor"）
    :param result: 病历信息
    :param image_content: 病历图片二进制内容
    :return: 创建结果
    """
    user_kwargs = {
        "patient": user_model if user_type == "patient" else None,
        "doctor": user_model if user_type == "doctor" else None,
        "name": user_model.name if user_type == "patient" else None,
        "age": user_model.age if user_type == "patient" else None,
        "gender": user_model.gender,
        "phone_number": user_model.phone_number if user_type == "patient" else None,
        "symptoms_description": result.symptoms_description,
        "detailed_description": result.detailed_description,
        "condition_analysis": result.condition_analysis,
        "drug_recommendation": result.drug_recommendation,
        "image": image_content
    }
    record = await MedicalRecord.create(**user_kwargs)
    medicalrecord_data = MedicalRecordResponse.from_orm(record)
    return {"code": 200, "data": {"message": "MedicalRecord created successfully", "result": medicalrecord_data}}


# 创建病历信息的路由
@router.post("/create_medicalrecord_info/", summary="添加病历信息")
async def create_medical_record_route(user: User = Depends(get_current_user), doctor_id: Any = None,
                                      result: MedicalRecordInfo = Body(...), image: UploadFile = File(None)):
    """
    创建病历信息的路由
    :param user: 当前用户
    :param doctor_id: 医生 ID
    :param result: 病历信息
    :param image: 病历图片
    :return: 创建结果
    """
    if user.patient_status:
        user_model = user.patient
        user_type = "patient"
    elif user.doctor_status:
        user_model = user.doctor
        user_type = "doctor"
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have patient or doctor status")

    if image:
        # 将 image 转换为字节类型
        try:
            image_content = await process_uploaded_file(image)
        except Exception as e:
            logger.error(f"处理上传文件时出错: {e}")
            raise HTTPException(status_code=500, detail="处理上传文件时出错")
    else:
        image_content = None

    return await create_medical_record(user_model, user_type, result, image_content)


# 更新病历信息的路由
@router.put("/update_medicalrecord_info/", summary="修改病历信息")
async def update_medicalrecord_info(
        current_user: User = Depends(get_current_user),
        medicalrecordinfo: Optional[MedicalRecord_Pydantic] = None,
        time_record: str = None,
        phone_number: str = None,
        cure_suggestion: str = None,
        doctor_id: int = None
):
    """
    更新病历信息的路由
    :param current_user: 当前用户
    :param medicalrecordinfo: 病历信息，可选参数
    :return: 更新结果
    """
    doctor_status = current_user.doctor_status
    if not doctor_status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    try:
        patient_obj = await Patient.get(phone_number=phone_number)
    except Patient.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    if cure_suggestion:
        patient = await DoctorPatientForm.filter(doctor=current_user.doctor, patient=patient_obj,
                                                 time_record=time_record).order_by("-id").first()
        if patient is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DoctorPatientForm not found")

        medicalrecord = await MedicalRecord.filter(patient_id=patient.patient_id).order_by('-id').first()
        if medicalrecord:
            medicalrecord.condition_analysis = cure_suggestion
    else:
        medicalrecord = await MedicalRecord.filter(patient=patient_obj).order_by('created_at').last()
        if medicalrecord:
            medicalrecord.condition_analysis = None

    if not medicalrecord:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical record not found")

    # 如果 medicalrecordinfo 不为 None，则使用其更新病历信息
    if medicalrecordinfo:
        await medicalrecord.update_from_dict(medicalrecordinfo.model_dump(exclude_unset=True))

    await medicalrecord.save()
    print("Medical record updated successfully.")
    medicalrecord_data = await MedicalRecordResponse.from_orm(medicalrecord)
    return {"code": 200, "data": medicalrecord_data}


# 获取某一个病人的所有病历信息的路由
@router.get("/get_medicalrecord_info/", summary="查询某一个病人的所有病历信息")
async def get_medicalrecord_info(user: User = Depends(get_current_user), patient: Patient = Depends(search_patient)):
    """
    获取病历信息接口，根据用户信息查询病历信息
    :param user: 当前用户信息
    :param patient: 当前患者信息
    :return: 查询结果消息
    """
    if not user.patient_status:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have patient status")

    medical_records = await MedicalRecord.filter(phone_number=patient.phone_number).all()
    serialized_medical_records = [MedicalRecordResponse.from_orm(record) for record in medical_records]
    return {"code": 200, "data": serialized_medical_records}


# 获取所有病历信息的路由
@router.get("/medical_records_list/", summary="查询所有病历信息")
async def get_medical_records_list():
    """
    获取所有病历信息列表接口
    :return: 所有病历信息列表
    """
    medical_records = await MedicalRecord.all()
    serialized_medical_records = [MedicalRecordResponse.from_orm(record) for record in medical_records]
    return {"code": 200, "data": serialized_medical_records}