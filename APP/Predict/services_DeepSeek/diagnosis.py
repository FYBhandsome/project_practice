# diagnosis.py 优化版本
import json
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Any
from APP.Predict.services_DeepSeek.medical_advisor import MedicalRequest  # 导入请求模型
from pydantic import ValidationError

from APP.Predict.services_DeepSeek.medical_advisor import MedicalAdvisor
from APP.Predict.ali_api_yunapi_predict import detect_by_upload

# 初始化路由器和日志
router = APIRouter(prefix="/api/medical", tags=["医疗诊断"])
logger = logging.getLogger("diagnosis")
from dotenv import load_dotenv

load_dotenv()

async def validate_diagnosis_data(data: Dict[str, Any]) -> Dict[str, Any]:
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
             description="整合图像诊断和医疗建议生成的完整流程",
             response_model=Dict[str, Any])
async def full_diagnosis( file: UploadFile = File(..., description="需要分析的图片文件（支持JPEG/PNG）"),
        org_id: str = "default_org") -> Dict[str, Any]:
    """
    完整诊断流程：
    1. 图片上传 -> 2. 皮肤病检测 -> 3. 生成医疗建议

    参数:
    - file: 皮肤病变图像文件（JPEG/PNG格式，≤5MB）

    返回:
    {
        "diagnosis": 诊断结果,
        "medical_advice": 治疗建议,
        "metadata": 流程元数据
    }
    """
    advisor = MedicalAdvisor()
    metadata = {"stages": {}}

    try:
        # 阶段1：调用皮肤病检测
        logger.info("Starting image diagnosis")
        diagnosis_response = await detect_by_upload(file, org_id)
        raw_data = json.loads(diagnosis_response.body)

        # 验证并提取诊断结果
        diagnosis = validate_diagnosis_data(raw_data)
        metadata["stages"]["diagnosis"] = {"status": "success", "request_id": raw_data.get("RequestId")}

        # 阶段2：生成医疗建议
        logger.info(f"Generating advice for {diagnosis['disease']}")

        try:
            # 将字典转换为Pydantic模型实例
            request_data = MedicalRequest(
                disease=diagnosis["disease"],
                confidence=diagnosis["confidence"]
            )
            advice = await advisor.generate_advice(request_data)
        except ValidationError as e:
            logger.error(f"请求数据验证失败: {str(e)}")
            raise HTTPException(
                status_code=422,
                detail={
                    "type": "INVALID_DIAGNOSIS_DATA",
                    "message": "诊断数据格式异常",
                    "details": e.errors()
                }
            )

        # 合并最终结果
        return {
            "diagnosis": diagnosis,
            "medical_advice": advice,
            "metadata": metadata,
            "disclaimer": "本结果仅供参考，具体诊疗请遵医嘱"
        }

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败：{str(e)}")
        raise HTTPException(502, "诊断服务返回数据格式异常")
    except ValueError as e:
        logger.warning(f"数据验证失败：{str(e)}")
        raise HTTPException(502, f"诊断数据异常：{str(e)}")
    except HTTPException as he:
        raise he  # 传递已知异常
    except Exception as e:
        logger.error(f"未处理异常：{str(e)}", exc_info=True)
        raise HTTPException(500, "系统处理异常")


# 示例响应文档
@router.get("/response-example", include_in_schema=False, tags=["示例响应文档"])
async def get_response_example():
    """接口响应结构示例"""
    return {
        "diagnosis": {
            "disease": "痤疮",
            "confidence": 96.47,
            "raw_data": {"...": "..."}
        },
        "medical_advice": {
            "analysis": "...",
            "treatment_plan": {"...": "..."},
            # ...其他字段
        },
        "metadata": {
            "stages": {
                "diagnosis": {
                    "status": "success",
                    "request_id": "E0278DEE-1F14-52A6-88D2-E7AADFBF1C32"
                }
            }
        }
    }