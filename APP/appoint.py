from models import Reservation
from extra_function import get_current_user
from fastapi import APIRouter
from .doctor_patient_form import create_doctor_patient_form, delete_doctor_patient_forms
from typing import Any
import logging
from fastapi import Depends, Body, HTTPException, status
from models import User, Doctor, Appointment
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.exceptions import DoesNotExist, IntegrityError
from dotenv import load_dotenv

load_dotenv()
# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 创建 Pydantic 模型用于序列化 Appointment 对象
Appointment_Pydantic = pydantic_model_creator(Appointment, name="Appointment")


# 添加预约订单
@router.post("/appoint/", summary="添加预约订单")
async def appoint(user: User = Depends(get_current_user), reserveinfo: Reservation = Body(...)):
    if not user.patient_status:
        return {"code": 403, "data": {"message": "Only patients can make appointments."}}
    try:
        # 仅患者可以添加预约
        if not user.patient:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Only patients can make appointments.The patient_id is None.")

        # 根据手机号获取医生实例
        try:
            doctor = await Doctor.get(id=reserveinfo.doctor_id)
            doctor.appointment_count += 1
            await doctor.save()
        except DoesNotExist:
            logger.error("Doctor not found with the given profession number.")
            raise HTTPException(status_code=404, detail="Doctor not found with the given profession number.")

        patient = user.patient

        reserve_time = reserveinfo.appointment_time
        # 生成预约单号：预约医生的id＋自己手机号
        appointment_number = f"{reserveinfo.doctor_id}{user.phone_number}"

        # 检查预约单号是否已经存在
        existing_appointment = await Appointment.filter(appointment_number=appointment_number).first()
        if existing_appointment:
            logger.error(f"Appointment number {appointment_number} already exists.")
            raise HTTPException(status_code=409, detail="Appointment number already exists.")

        # 创建预约实例
        appointment = await Appointment.create(
            doctor=doctor,
            patient=patient,
            appointment_number=appointment_number,
            appointment_time=reserve_time
        )
        # 创建医患单
        await create_doctor_patient_form(current_patient=patient, current_doctor=doctor, time_record=reserve_time)

        logger.info(f"Appointment created successfully: {appointment.id}")
        appointment_data = await Appointment_Pydantic.from_tortoise_orm(appointment)
        return {"code": 200, "data": appointment_data}
    except IntegrityError:
        logger.error("Integrity error occurred while creating appointment.")
        raise HTTPException(status_code=409, detail="Integrity error occurred while creating appointment.")
    except Exception as e:
        logger.error(f"Error creating appointment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating appointment: {str(e)}")


# 删除预约订单
@router.delete("/appoint/{doctor_id}/", summary="删除预约订单")
async def appointment_delete(user: User = Depends(get_current_user), doctor_id: Any = None,
                             appointment_number: str = None):
    if not user.patient_status:
        return {"code": 403, "data": {"message": "Only patients can delete appointments."}}
    try:
        appointment = None
        print(f"user.patient: {user.patient}")
        print(f"user.doctor: {user.doctor}")

        if appointment_number:
            appointment_number = appointment_number

        doctor = await Doctor.get(id=doctor_id)
        if doctor.appointment_count >= 1:
            doctor.appointment_count -= 1
            await doctor.save()
        else:
            doctor.appointment_count = 0
            await doctor.save()

        if (not appointment_number) and doctor_id:
            # 生成预约单号：预约医生的id＋自己手机号
            appointment_number = f"{doctor_id}{user.phone_number}"

        if user.patient:
            try:
                # 预加载 patient 和 doctor 对象
                appointment = await Appointment.filter(appointment_number=appointment_number).prefetch_related(
                    'patient', 'doctor').first()
            except Appointment.DoesNotExist:
                appointment = None
        elif user.doctor:
            # 预加载 patient 和 doctor 对象
            appointment = await Appointment.filter(doctor=user.doctor,
                                                   appointment_number=appointment_number).prefetch_related('patient',
                                                                                                           'doctor').first()
        print(f"Appointment deleted: {appointment}")

        if not appointment:
            # 打印查询使用的预约单号
            logger.error(f"Appointment not found with the given appointment number: {appointment_number}")
            stored_appointments = await Appointment.all()
            for stored_appointment in stored_appointments:
                logger.info(f"Stored appointment number: {stored_appointment.appointment_number}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Appointment not found with the given appointment number.")
        time_record = appointment.appointment_time
        # 检查权限，医生和患者都可以删除自己相关的预约
        if (user.patient and appointment.patient.id != user.patient.id) or (
                user.doctor and appointment.doctor.id != user.doctor.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You do not have permission to delete this appointment.")

        patient_obj = appointment.patient
        doctor_obj = appointment.doctor
        # 删除预约
        await appointment.delete()
        logger.info(f"Appointment deleted successfully: {appointment_number}")
        await delete_doctor_patient_forms(patient=patient_obj, doctor=doctor_obj, time_record=time_record)
        return {"code": 200, "data": {"message": "Appointment deleted successfully."}}

    except Exception as e:
        logger.error(f"Error deleting appointment: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Error deleting appointment: {str(e)}")


# 修改订单
@router.put("/appoint/{doctor_id}/", summary="修改预约订单")
async def appointment_update(user: User = Depends(get_current_user), doctor_id: int = None,
                             appointment_number: str = None,
                             reserveinfo: Reservation = Body(...)):
    if not user.patient_status:
        return {"code": 403, "data": {"message": "Only patients can update appointments."}}
    try:
        appointment = None
        if appointment_number:
            appointment_number = appointment_number
        if (not appointment_number) and doctor_id:
            # 生成预约单号：预约医生的id＋自己手机号
            appointment_number = f"{doctor_id}{user.phone_number}"
        if user.patient:
            appointment = await Appointment.filter(appointment_number=appointment_number).first()
        elif user.doctor:
            appointment = await Appointment.filter(appointment_number=appointment_number).first()
        if not appointment:
            logger.error(f"Appointment not found with the given appointment number: {appointment_number}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Appointment not found with the given appointment number.")
        # 获取新的医生
        try:
            doctor = await Doctor.get(id=reserveinfo.doctor_id)
        except DoesNotExist:
            logger.error("Doctor not found with the given ID.")
            raise HTTPException(status_code=404, detail="Doctor not found with the given ID.")
        # 手动解析日期字符串
        try:
            reserve_time = reserveinfo.appointment_time
        except ValueError:
            logger.error("Invalid date format. Please use 'YYYY年MM月DD日'.")
            raise HTTPException(status_code=400, detail="Invalid date format. Please use 'YYYY年MM月DD日'.")
        # 更新预约订单信息
        appointment.doctor = doctor
        appointment.appointment_time = reserve_time
        # 生成预约单号：预约医生的id＋自己手机号
        appointment.appointment_number = f"{reserveinfo.doctor_id}{user.phone_number}"
        # 保存更新后的预约订单
        await appointment.save()
        logger.info(f"Appointment updated successfully: {appointment.id}")
        appointment_data = await Appointment_Pydantic.from_tortoise_orm(appointment)
        return {"code": 200, "data": appointment_data}
    except Exception as e:
        logger.error(f"Error updating appointment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating appointment: {str(e)}")


# 获取预约列表的路由
@router.get("/appoint/list/", summary="获取预约列表")
async def get_appointment_list(user: User = Depends(get_current_user)):
    try:
        appointments = []
        if user.patient_status:
            if user.patient:
                logger.info(f"User {user.id} is a patient. Querying appointments by patient ID {user.patient.id}.")
                appointments = await Appointment.filter(patient=user.patient).all()
            else:
                logger.warning(f"User {user.id} is a patient, but patient object is None.")
        elif user.doctor_status:
            if user.doctor:
                logger.info(f"User {user.id} is a doctor. Querying appointments by doctor ID {user.doctor.id}.")
                appointments = await Appointment.filter(doctor=user.doctor).all()
            else:
                logger.warning(f"User {user.id} is a doctor, but doctor object is None.")
        else:
            logger.warning(f"User {user.id} has neither patient nor doctor status.")
        serialized_appointments = [await Appointment_Pydantic.from_tortoise_orm(appointment) for appointment in
                                   appointments]
        logger.info(f"Successfully retrieved {len(serialized_appointments)} appointments.")
        return {"code": 200, "data": serialized_appointments}
    except Exception as e:
        logger.error(f"Error retrieving appointment list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving appointment list: {str(e)}")


# 检查时间段是否可预约
@router.get("/doctor/{doctor_id}/time-slots/check", summary="检查时间段是否可预约")
async def check_time_slot_availability(doctor_id: int, date: str):
    try:
        # 统计该医生在指定日期和时间段内的已有预约数量
        existing_appointments = await Appointment.filter(
            doctor_id=doctor_id,
            appointment_time=date,
        ).all()

        # 判断是否可预约，根据医生的预约量来判断
        is_available = len(existing_appointments) < 20

        return {"code": 200, "data": {"is_available": is_available}}
    except Exception as e:
        logger.error(f"Error checking time slot availability: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking time slot availability: {str(e)}")


# 获取预约详情
@router.get("/appoint/{appointment_id}/detail", summary="获取预约详情")
async def get_appointment_detail(appointment_id: int):
    try:
        appointment = await Appointment.get(id=appointment_id).prefetch_related('patient', 'doctor')
        patient = appointment.patient
        doctor = appointment.doctor
        appointment_data = {
            "id": appointment.id,
            "patient_id": patient.id,
            "patient_name": patient.name,
            "patient_phone_number": patient.phone_number,
            "doctor_id": doctor.id,
            "doctor_name": doctor.name,
            "doctor_phone_number": doctor.phone_number,
            "appointment_time": appointment.appointment_time,
            "appointment_number": appointment.appointment_number,
        }
        # appointment_data = await Appointment_Pydantic.from_tortoise_orm(appointment)
        return {"code": 200, "data": appointment_data}
    except DoesNotExist:
        logger.error(f"Appointment not found with ID: {appointment_id}")
        raise HTTPException(status_code=404, detail=f"Appointment not found with ID: {appointment_id}")
    except Exception as e:
        logger.error(f"Error retrieving appointment detail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving appointment detail: {str(e)}")
