from extra_function import search_patient, search_doctor
import logging
# 导入自定义模型模块
from models import (
    User, DoctorPatientForm, MedicalRecord,
    Patient, Doctor
)
from tortoise.exceptions import DBConnectionError

from fastapi import Depends, APIRouter, HTTPException, status
from models import User, Patient, DoctorPatientForm, PatientInfo, DoctorInfo
from extra_function import get_current_user

router = APIRouter()


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建多对多关系的，创建医患就诊单的路由，依赖于 get_current_user 函数
@router.post("/create_doctor_patient_form/", summary="医患单")
async def create_doctor_patient_form(current_patient: Patient = Depends(search_patient),
                                     current_doctor: Doctor = Depends(search_doctor),
                                     time_record:str = None):
    """
    创建医患单信息接口，根据当前用户信息查询医患单信息
    :param current_patient: 当前患者信息
    :param current_doctor: 当前医生
    :return: 创建结果消息
    """
    try:
        # 创建医患单记录
        data = await DoctorPatientForm.create(
            patient=current_patient,
            doctor=current_doctor,
            time_record=time_record
        )
        return {"code": 200, "data": {"message": "DoctorPatientForm created successfully", "data": data}}
    except Exception as e:
        # 若创建失败，返回 400 错误
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))



@router.put("/update_doctor_patient_form/", summary="修改医患单")
async def update_doctor_patient_form(user: User = Depends(get_current_user), phone_number: str = None, time_record: str = None,
                                     cure_suggestion: str = None):
    # 检查用户是否为医生，只有医生可以修改医患单
    if not user.doctor_status:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only doctors can update doctor-patient forms.")
    try:
        patient = await Patient.get(phone_number=phone_number)
        doctor = user.doctor
        # 使用 filter 方法获取所有满足条件的记录
        doctor_patient_forms = await DoctorPatientForm.filter(patient=patient, doctor=doctor, time_record=time_record).order_by('-id')
        if not doctor_patient_forms:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DoctorPatientForm not found")
        # 选择最新的记录
        doctor_patient_form = doctor_patient_forms[0]

        # 更新治疗建议
        doctor_patient_form.cure_suggestion = cure_suggestion
        # 保存更新后的医患单记录
        await doctor_patient_form.save()
        return {"code": 200, "data": {"message": "DoctorPatientForm updated successfully"}}
    except Exception as e:
        # 处理其他异常，返回 500 错误
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))



# 获取医患就诊单详情记录
@router.get("/doctor_patient_form/{form_id}/detail", summary="获取医患就诊单详情")
async def get_doctor_patient_form_detail(form_id: int):
    try:
        # 通过预加载关联的患者和医生信息
        doctor_patient_form = await DoctorPatientForm.get(id=form_id).prefetch_related('patient', 'doctor')
        patient = doctor_patient_form.patient
        doctor = doctor_patient_form.doctor

        form_data = {
            "id": doctor_patient_form.id,
            "patient_id": patient.id,
            "patient_name": patient.name,
            "patient_phone_number": patient.phone_number,
            "doctor_id": doctor.id,
            "doctor_name": doctor.name,
            "doctor_phone_number": doctor.phone_number,
            "cure_suggestion": doctor_patient_form.cure_suggestion,
            "created_at": doctor_patient_form.created_at,
            "updated_at": doctor_patient_form.updated_at
        }
        return {"code": 200, "data": form_data}
    except DoctorPatientForm.DoesNotExist:
        logger.error(f"DoctorPatientForm not found with ID: {form_id}")
        raise HTTPException(status_code=404, detail=f"DoctorPatientForm not found with ID: {form_id}")
    except Exception as e:
        logger.error(f"Error retrieving doctor-patient form detail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving doctor-patient form detail: {str(e)}")

# 获取医患就诊单列表
@router.get("/doctor_patient_forms/list", summary="获取医患就诊单列表")
async def get_doctor_patient_forms_list():
    try:
        # 通过预加载关联的患者和医生信息获取所有医患就诊单
        doctor_patient_forms = await DoctorPatientForm.all().prefetch_related('patient', 'doctor')
        form_list = []
        for form in doctor_patient_forms:
            patient = form.patient
            doctor = form.doctor
            form_data = {
                "id": form.id,
                "patient_id": patient.id,
                "patient_name": patient.name,
                "patient_phone_number": patient.phone_number,
                "doctor_id": doctor.id,
                "doctor_name": doctor.name,
                "doctor_phone_number": doctor.phone_number,
                "cure_suggestion": form.cure_suggestion,
                "created_at": form.created_at,
                "updated_at": form.updated_at
            }
            form_list.append(form_data)
        return {"code": 200, "data": form_list}
    except Exception as e:
        logger.error(f"Error retrieving doctor-patient forms list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving doctor-patient forms list: {str(e)}")

# 删除医患单
@router.delete('/doctor_patient_forms/delete', summary='删除医患单')
async def delete_doctor_patient_forms(patient: PatientInfo = None, doctor: DoctorInfo = None, time_record:str = None):
    if (not patient) or (not doctor) or (not time_record):
        raise HTTPException(status_code=404, detail="该医患单参数不完整，或者该医患单不存在！")
    doctorpatientform = await DoctorPatientForm.get(patient=patient, doctor=doctor, time_record=time_record)
    await doctorpatientform.delete()
    return {"code":200, "data": {'message':'Successfully deleted doctor-patient'}}


