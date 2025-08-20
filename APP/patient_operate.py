from fastapi import Depends, APIRouter
from models import User, DoctorPatientForm, Doctor, MedicalRecord
from extra_function import get_current_user
from tortoise.exceptions import DoesNotExist
import logging
from dotenv import load_dotenv

load_dotenv()
# 配置日志
logging.basicConfig(level=logging.ERROR)

# 创建一个 APIRouter 实例，用于组织和管理路由
router = APIRouter()


@router.get("/jiuzhen/", summary="患者就诊")
async def cure_doctors(user: User = Depends(get_current_user), doctor_id: int = None, time_record: str = None):
    """
    该接口用于患者处理预约，按预约时间顺序处理第一个预约。

    业务逻辑：
    1. 验证当前用户是否为患者。
    2. 获取该患者的所有预约列表，按预约时间排序。
    3. 取出第一个预约（最早地预约）。
    4. 如果有预约，删除该预约，表示该预约已处理。
    5. 获取医生的诊断建议。
    6. 获取医生的相关信息，如姓名、职称等。
    7. 根据不同情况返回相应的消息，包含患者、医生和诊断建议的信息。

    参数:
    - user (User): 当前登录的用户，通过 get_current_user 依赖注入获取。
    - doctor_id (int): 医生的 ID

    返回:
    - dict: 包含处理结果的消息，采用 {"code": 状态码, "data": {...}} 格式，其中 data 包含详细信息。
    """
    try:
        # 检查当前用户是否关联了患者信息
        if not user.patient:
            return {"code": 404, "data": {"message": "Patient not found for this user."}}

        # 获取患者的 ID
        patient_id = user.patient.id

        # 检查 doctor_id 是否有效
        if doctor_id is None:
            return {"code": 400, "data": {"message": "doctor_id is required."}}

        # 创建查询集，筛选出该患者的所有预约，并按预约时间排序
        doctor_patient_form = await DoctorPatientForm.filter(patient_id=patient_id, doctor_id=doctor_id, time_record=time_record).order_by("id").last()

        # 异步获取最早的预约
        doctor = await Doctor.get(id=doctor_id)

        if doctor_patient_form:
            diagnosis = doctor_patient_form.cure_suggestion
            response_data = {
                "message": "Appointment processed successfully.",
                "patient": {
                    "id": user.patient.id,
                    "name": user.patient.name,
                    "phone_number": user.patient.phone_number
                },
                "doctor": {
                    "id": doctor.id,
                    "name": doctor.name,
                    "title": doctor.title
                },
                "diagnosis": diagnosis
            }
            return {"code": 200, "data": response_data}
        else:
            response_data = {
                "message": "Appointment processed successfully, but no diagnosis found.",
                "patient": {
                    "id": user.patient.id,
                    "name": user.patient.name,
                    "phone_number": user.patient.phone_number
                },
                "doctor": {
                    "id": doctor.id,
                    "name": doctor.name,
                    "title": doctor.title
                }
            }
            return {"code": 200, "data": response_data}
    except DoesNotExist:
        return {"code": 404, "data": {"message": "Patient, appointment, or doctor not found."}}
    except Exception as e:
        # 记录异常信息
        logging.error(f"An error occurred in cure_doctors: {str(e)}")
        return {"code": 500, "data": {"message": f"An error occurred: {str(e)}"}}