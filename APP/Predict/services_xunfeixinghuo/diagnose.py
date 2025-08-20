from dotenv import load_dotenv
import logging, base64
logger = logging.getLogger(__name__)
load_dotenv()
from process_photo import process_uploaded_file
from APP.Predict.services_xunfeixinghuo.sparkAPI import illness_analysis
from models import MedicalRecord, Patient, MedicalRecordInfo, User
from extra_function import search_patient, get_current_user
import traceback
from datetime import datetime
from PIL import Image  # 用于图像验证
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from typing import Dict, Any
# diagnose.py
from APP.Predict.ali_api_yunapi_predict import detect_by_upload
from APP.MedicalRecord import create_medical_record_route
# from APP.Predict.services_DeepSeek.diagnosis import validate_diagnosis_data, logger
router = APIRouter()

# 配置常量
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

async def validate_image_file(file: UploadFile) -> None:
    """验证上传文件是否符合要求"""
    # 检查文件类型
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(400, detail="仅支持JPEG/PNG格式")

    # 检查文件大小
    file.file.seek(0, 2)  # 移动到文件末尾
    file_size = file.file.tell()
    file.file.seek(0)  # 重置文件指针
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(413, detail="文件大小超过5MB限制")

    # 验证是否为有效图像
    try:
        with Image.open(file.file) as img:
            img.verify()  # 验证图像完整性
    except Exception as e:
        raise HTTPException(400, detail=f"无效的图片文件: {str(e)}")
    finally:
        file.file.seek(0)  # 再次重置文件指针


async def update_medical_record(patient: Patient, disease_name:str = None, confidence:str=None, recommendation: str=None, image_content:UploadFile = None) -> None:
    """更新医疗记录（添加事务处理）"""
    try:
        medicalrecord = await MedicalRecord.filter(
            phone_number=patient.phone_number
        ).order_by('-id').first()
        medicalrecord.drug_recommendation = recommendation
        medicalrecord.update_at = datetime.now()
        await medicalrecord.save()
    except Exception as e:
        logger.error(f"更新医疗记录失败: {str(e)}")
        raise HTTPException(500, detail="医疗记录更新失败")

async def validate_diagnosis_data_1(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证并提取阿里云诊断结果
    :param data: 原始诊断数据
    :return: 标准化诊断结果
    :raises ValueError: 数据格式错误时抛出
    """
    try:
        results = data["Data"]["Results"]
        if not results:
            raise ValueError("诊断结果为空")

        # 获取置信度最高的疾病
        max_disease = max(results.items(), key=lambda x: x[1])
        return {
            "disease": max_disease[0],
            "confidence": round(max_disease[1] * 100, 2),  # 转换为百分比
            "raw_data": data  # 保留原始数据用于调试
        }
    except KeyError as e:
        raise ValueError(f"无效的数据结构，缺少关键字段：{str(e)}")

@router.post("/full-diagnosis",
             summary="端到端皮肤病诊断",
             response_model=Dict[str, Any])
async def full_diagnosis(
        user: User = Depends(get_current_user),
        file: UploadFile = File(..., description="皮肤病变图像文件（JPEG/PNG，≤5MB）"),
        description: str = None,
        patient: Patient = Depends(search_patient)
) -> Dict[str, Any]:
    try:
        # ===== 阶段1：文件验证 =====
        await validate_image_file(file)
        if file:
            image_content = await process_uploaded_file(file)
        else:
            print("已执行")
            image_content = None
        # 将二进制图片数据转换为 Base64 编码的字符串
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        # ===== 阶段2：皮肤病诊断 =====
        logger.info("Starting image diagnosis for patient: %s", patient.phone_number)
        diagnosis = await detect_by_upload(file)  # 直接获取解析后的字典
        print(f'Diagnosis: {diagnosis}')
        disease_name = diagnosis['disease']
        confidence = diagnosis['confidence']
        logger.info("disease_name: %s", disease_name)
        logger.info("confidence: %s", confidence)
        analysis_result = None

        # ===== 阶段3：生成医疗建议 =====
        if not description:
            analysis_result = await illness_analysis(text=disease_name, current_patient=patient)
        if description:
            analysis_result = await illness_analysis(text=disease_name, current_patient=patient, description=description)

        logger.info("analysis_result: %s", analysis_result)
        if analysis_result.get('code') != 200:
            raise HTTPException(502, detail="医疗建议生成服务异常")

        recommendation = analysis_result['data']['analysis']
        logger.info("recommendation: %s", recommendation)

        # ===== 阶段4：创建医疗记录 =====
        result_1 = MedicalRecordInfo()
        result_1.symptoms_description = disease_name
        result_1.detailed_description = confidence
        result_1.drug_recommendation = recommendation
        await create_medical_record_route(user=user, result=result_1, image=file)

        # ===== 构建响应 =====
        return {
            "diagnosis": {
                "disease": disease_name,
                "confidence": confidence,
                "methodology": "基于深度学习的图像分析"
            },
            "image": image_base64,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat(),
            "disclaimer": "本结果仅供参考，具体诊疗请遵医嘱"
        }
    except Exception as e:
        logger.error(f"完整诊断流程失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(500, detail="完整诊断流程失败")
