import os
from models import Photo, MedicalRecord, MedicalRecordInfo
from fastapi import File, UploadFile, APIRouter, Depends, HTTPException
from APP.Drug_recommendation.drug_operate import get_recommended_drug, Disease_Description
from models import User, Appointment
from extra_function import get_current_user
from tortoise.contrib.pydantic import pydantic_model_creator
from datetime import datetime
import logging
from process_photo import process_uploaded_file
import base64

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 Pydantic 模型用于序列化 Appointment 对象
Appointment_Pydantic = pydantic_model_creator(Appointment, name="Appointment")
# 创建 Pydantic 模型用于序列化 MedicalRecord 对象
MedicalRecord_Pydantic = pydantic_model_creator(MedicalRecord, name="MedicalRecord")

# 定义子路由对象
router = APIRouter()

# 定义静态文件存储目录
UPLOAD_DIR = "illness_photo"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# 保存上传的文件
async def save_uploaded_file(file: UploadFile):
    try:
        # 生成唯一的文件名
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_extension = os.path.splitext(file.filename)[1]
        new_filename = f"{timestamp}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, new_filename)

        # 保存文件到本地
        with open(file_path, "wb") as f:
            contents = await file.read()
            f.write(contents)
        return file_path
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

# 创建病历信息
async def create_medical_record(user: User, result: MedicalRecordInfo, image: UploadFile = File(None)):
    user_model = None
    try:
        if image:
            image_content1 = await process_uploaded_file(image)
            # 将二进制图片数据转换为 Base64 编码的字符串
            image_content = base64.b64encode(image_content1).decode('utf-8')
        else:
            image_content = None

        if user.patient_status:
            user_model = user.patient
            medical_record = await MedicalRecord.create(
                patient=user_model,
                name=user.patient.name,
                age=user.patient.age,
                gender=user.patient.gender,
                phone_number=user.patient.phone_number,
                symptoms_description=result.symptoms_description,
                detailed_description=result.detailed_description,
                condition_analysis=result.condition_analysis,
                drug_recommendation=result.drug_recommendation,
                image=image_content
            )
        elif user.doctor_status:
            user_model = user.doctor
            medical_record = await MedicalRecord.create(
                doctor=user_model,
                symptoms_description=result.symptoms_description,
                detailed_description=result.detailed_description,
                condition_analysis=result.condition_analysis,
                drug_recommendation=result.drug_recommendation,
                image=image_content
            )
        else:
            raise HTTPException(status_code=400, detail="User is neither a patient nor a doctor.")

        medicalrecord_data = await MedicalRecord_Pydantic.from_tortoise_orm(medical_record)
        medicalrecord_data.image = image_content
        return medicalrecord_data
    except Exception as e:
        logger.error(f"Error creating medical record: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating medical record: {str(e)}")

# 上传照片接口（增加功能）
# @router.post("/upload-photo/", summary="上传病症照片(这个功能暂时不使用，已经废弃)")
# async def upload_photo(
#         file: UploadFile = File(...),
#         user: User = Depends(get_current_user)
# ):
#     try:
#         # 保存上传的文件
#         file_path = await save_uploaded_file(file)
#
#         # 调用卷积神经网络来识别图像
#         # result = main(file_path)
#         logger.info(f"这是result的结果：\n{result}")
#
#         # # 处理识别结果
#         # if result:
#         #     first_item = result[0]
#         #     # table = {""}
#         #     symptoms_description_name = list(first_item.keys())[0]
#         #     symptoms_description_value = first_item[symptoms_description_name]
#         # else:
#         #     symptoms_description_name = None
#             symptoms_description_value = None
#         # patient = user.patient
#         # doctor_id = user.doctor.id
#         # example = await DoctorPatientForm.filter(doctor_id=doctor_id, patient=patient).order_by('id').last()
#
#         medicalrecordinfo = MedicalRecordInfo()
#         # medicalrecordinfo.symptoms_description = symptoms_description_name
#         # medicalrecordinfo.condition_analysis = example.description
#         medicalrecordinfo.condition_analysis = None
#         # medicalrecordinfo.drug_recommendation = await get_recommended_drug(symptoms_description_name)
#         # medicalrecordinfo.detailed_description = await Disease_Description(symptoms_description_name)
#
#         # 创建病历信息
#         medicalrecord_data = await create_medical_record(user, medicalrecordinfo, file)
#
#         return {"code": 200,
#                 "data": {"message": "Photo uploaded and MedicalRecord created successfully", "result": medicalrecord_data}}
#     except Exception as e:
#         logger.error(f"Error uploading photo: {e}")
#         raise HTTPException(status_code=500, detail=f"Error uploading photo: {str(e)}")


# 获取用户的所有照片接口（查询功能）
@router.get("/user-photos/", summary="查询所有照片")
async def get_user_photos(user: User = Depends(get_current_user)):
    try:
        photos = await Photo.filter(user=user).all()
        photo_list = []
        for photo in photos:
            if photo.image:
                image_base64 = base64.b64encode(photo.image).decode('utf-8')
            else:
                image_base64 = None
            photo_data = {
                "id": photo.id,
                "title": photo.title,
                "image": image_base64,
                "created_at": photo.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": photo.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            photo_list.append(photo_data)
        return {"code": 200, "data": photo_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user photos: {str(e)}")


# 获取单张照片信息接口（查询功能）
@router.get("/photo/{photo_id}", summary="查询单张照片")
async def get_single_photo(photo_id: int, user: User = Depends(get_current_user)):
    try:
        photo = await Photo.get(id=photo_id, user=user)
        if photo.image:
            image_base64 = base64.b64encode(photo.image).decode('utf-8')
        else:
            image_base64 = None
        photo_data = {
            "id": photo.id,
            "title": photo.title,
            "image": image_base64,
            "created_at": photo.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": photo.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        return {"code": 200, "data": photo_data}
    except Photo.DoesNotExist:
        raise HTTPException(status_code=404, detail="Photo not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting single photo: {str(e)}")


# 更新照片信息接口（修改功能）
@router.put("/photo/{photo_id}", summary="修改某张照片")
async def update_photo(
        photo_id: int,
        title: str = None,
        file: UploadFile = None,
        user: User = Depends(get_current_user)
):
    try:
        photo = await Photo.get(id=photo_id, user=user)

        if title:
            photo.title = title

        if file:
            image_contents = await process_uploaded_file(file)
            photo.image = image_contents

        await photo.save()
        if photo.image:
            image_base64 = base64.b64encode(photo.image).decode('utf-8')
        else:
            image_base64 = None
        return {"code": 200, "data": {"message": "Photo updated successfully", "photo_id": photo.id, "image": image_base64}}
    except Photo.DoesNotExist:
        raise HTTPException(status_code=404, detail="Photo not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating photo: {str(e)}")


# 删除照片接口（删除功能）
@router.delete("/photo/{photo_id}", summary="删除某张照片")
async def delete_photo(photo_id: int, user: User = Depends(get_current_user)):
    try:
        photo = await Photo.get(id=photo_id, user=user)
        # 删除数据库记录
        await photo.delete()
        return {"code": 200, "data": {"message": "Photo deleted successfully"}}
    except Photo.DoesNotExist:
        raise HTTPException(status_code=404, detail="Photo not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting photo: {str(e)}")


# 显示预约信息
@router.get("/appointments/", summary="显示所有预约信息")
async def get_appointments_info(user: User = Depends(get_current_user)):
    try:
        # 判断用户是医生还是患者
        print(f"user: {user}")
        if user.doctor:
            print(f"user.doctor type: {type(user.doctor)}")
            doctor_id = user.doctor.id if hasattr(user.doctor, 'id') else None
            print(f"doctor_id: {doctor_id}")
            if doctor_id:
                # 如果用户是医生，获取该医生的所有预约
                appointments = await Appointment.filter(doctor_id=doctor_id).all().prefetch_related('patient')
            else:
                print("doctor return []")
                return {"code": 200, "data": []}
        elif user.patient:
            patient_id = user.patient.id if hasattr(user.patient, 'id') else None
            print(f"patient_id: {patient_id}")
            if patient_id:
                # 如果用户是患者，获取该患者的所有预约
                appointments = await Appointment.filter(patient_id=patient_id).all().prefetch_related('doctor')
            else:
                print("patient return []")
                return {"code": 200, "data": []}
        else:
            # 如果用户既不是医生也不是患者，返回空列表
            return {"code": 200, "data": []}

        appointments_list = []
        for appointment in appointments:
            appointment_data = {
                # 预约单号
                "appointment_number": appointment.appointment_number,
                # 预约时间
                "appointment_time": appointment.appointment_time.strftime(
                    '%Y-%m-%d') if appointment.appointment_time else None,
                # 就诊时间
                "patient_visit_time": appointment.patient_visit_time.strftime(
                    '%Y-%m-%d') if appointment.patient_visit_time else None,
            }

            if user.doctor:
                # 如果用户是医生，添加患者信息
                patient = appointment.patient
                appointment_data.update({
                    # 病人信息
                    "patient_name": patient.name,
                    "patient_age": patient.age,
                    "patient_gender": patient.gender,
                })
            elif user.patient:
                # 如果用户是患者，添加医生信息
                doctor = appointment.doctor
                appointment_data.update({
                    # 医生信息
                    "doctor_name": doctor.user.username if hasattr(doctor, 'user') else None,
                    "doctor_working_years": doctor.working_years,
                    "doctor_gender": doctor.gender,
                    "doctor_hospital": doctor.hospital,
                    "doctor_title": doctor.title,
                    "doctor_appointment_count": doctor.appointment_count,
                    "registration_fee": doctor.registration_fee,
                    "introduction": doctor.introduction,
                    "expertise": doctor.expertise
                })

            appointments_list.append(appointment_data)

        return {"code": 200, "data": appointments_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting appointments info: {str(e)}")
