from fastapi import Depends, APIRouter, HTTPException
from models import Appointment, User, Doctor, DoctorPatientForm, Patient, MedicalRecord
from extra_function import get_current_user
from tortoise.exceptions import DoesNotExist
from .doctor_patient_form import create_doctor_patient_form, update_doctor_patient_form
import logging
from .MedicalRecord import update_medicalrecord_info

# 配置日志
logging.basicConfig(level=logging.ERROR)

# 创建一个 APIRouter 实例，用于组织和管理路由
router = APIRouter()


@router.get("/kanzhen/", summary="医生看诊")
async def cure_patients(user: User = Depends(get_current_user), cure_description: str = None):
    """
    该接口用于医生处理患者预约，按预约时间顺序处理第一个预约。

    业务逻辑：
    1. 验证当前用户是否为医生。
    2. 获取该医生的所有预约列表，按预约时间排序。
    3. 取出第一个预约（最早地预约）。
    4. 如果有预约，删除该预约，表示该预约已处理。
    5. 创建医患就诊单。
    6. 修改医患就诊单，添加看诊建议。
    7. 减少医生的预约量。
    8. 根据不同情况返回相应的消息，包含反关联模型的信息。

    参数:
    - user (User): 当前登录的用户，通过 get_current_user 依赖注入获取。
    - cure_description (str): 医生的看诊建议。

    返回:
    - dict: 包含处理结果的消息和相关信息。
    """
    if not user.doctor_status:
        return {"code": 403, "data": {"message": "Only doctors can edit and delete appointments."}}
    try:
        # 检查当前用户是否关联了医生信息
        if not user.doctor:
            return {"code": 404, "data": {"message": "Doctor not found for this user."}}

        # 获取医生的 ID
        doctor_id = user.doctor.id
        logging.info(f"Doctor ID: {doctor_id}")

        # 创建查询集，筛选出该医生的所有预约，并按预约时间排序
        patients_reserve_queue = Appointment.filter(doctor_id=doctor_id).order_by("appointment_time")
        logging.info(f"Patients reserve queue: {patients_reserve_queue}")

        # 异步获取最早的预约
        appointment = await patients_reserve_queue.first()
        appointment_time = appointment.appointment_time
        logging.info(f"Earliest appointment: {appointment}")

        if appointment:
            logging.info(f"Found appointment: {appointment.id}")
            patient = await Patient.get(id=appointment.patient_id)
            logging.info(f"Found patient: {patient.id}")

            # 创建医患就诊单
            doctor_patient_form = await create_doctor_patient_form(current_patient=patient, current_doctor=user.doctor, time_record=appointment_time)
            doctor_patient_form = doctor_patient_form["data"]["data"]
            logging.info(f"Created doctor-patient form: {doctor_patient_form.id}")
            print(f"cure_description:{cure_description}")
            print(f"patient.phone_number:{patient.phone_number}")

            # 修改医患就诊单，添加看诊建议
            try:
                data1 = await update_doctor_patient_form(user=user, phone_number=patient.phone_number, time_record=appointment_time,
                                                         cure_suggestion=cure_description)
                print("data1: ", data1)
                logging.info("Updated doctor-patient form with cure description")
                # 修改参数名，将 cure_description 改为 cure_suggestion
                print("patient.phone_number: ", patient.phone_number)
                print("cure_suggestion: ", cure_description)
                # 去掉 await 关键字
                update_medicalrecord_info(current_user=user, phone_number=patient.phone_number, time_record = appointment_time, doctor_id=doctor_id, cure_suggestion = cure_description)


            except Exception as update_error:
                # 打印详细的异常信息
                logging.error(f"Error in update_doctor_patient_form: {type(update_error).__name__} - {str(update_error)}")
                raise

            # 减少医生的预约量
            doctor = await Doctor.get(id=doctor_id)
            logging.info(f"Found doctor: {doctor.id}")
            if doctor.appointment_count >= 1:
                doctor.appointment_count -= 1
                await doctor.save()
                logging.info("Reduced doctor's appointment count")

            # 异步删除该预约
            await Appointment.filter(appointment_number=appointment.appointment_number).delete()
            logging.info("Deleted appointment")

            # 构建包含反关联模型信息的响应数据
            response_data = {
                "message": "Appointment processed successfully.",
                "doctor": {
                    "id": doctor.id,
                    "name": doctor.name,
                    "phone_number": doctor.phone_number
                },
                "patient": {
                    "id": patient.id,
                    "name": patient.name,
                    "phone_number": patient.phone_number
                },
                "cure_description": cure_description
            }

            return {"code": 200, "data": response_data}
        else:
            return {"code": 404, "data": {"message": "No appointments found for this doctor."}}
    except DoesNotExist:
        return {"code": 404, "data": {"message": "Doctor or patient not found."}}
    except Exception as e:
        # 打印详细的异常信息
        logging.error(f"General error in cure_patients: {type(e).__name__} - {str(e)}")
        return {"code": 500, "data": {"message": f"An error occurred: {str(e)}"}}