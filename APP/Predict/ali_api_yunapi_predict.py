# -*- coding: utf-8 -*-
"""
皮肤病检测API模块
功能：实现基于阿里云API的皮肤病检测服务，支持URL检测和图片上传检测
环境要求：Python 3.7+，需安装FastAPI及阿里云相关SDK
"""
# 核心依赖导入
# 加载环境变量（必须在其他导入之前执行）
from dotenv import load_dotenv

load_dotenv()  # 从项目根目录的.env文件加载配置
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os, logging
import hashlib
from typing import Dict, Any

# 阿里云SDK相关导入
from alibabacloud_imageprocess20200320.client import Client as ImageClient
from alibabacloud_imageprocess20200320 import models as viapi_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
import oss2  # 阿里云OSS SDK

# 初始化FastAPI路由
router = APIRouter()

# 环境变量配置检查
REQUIRED_ENV_VARS = [
    'ALIBABA_CLOUD_ACCESS_KEY_ID',
    'ALIBABA_CLOUD_ACCESS_KEY_SECRET',
    'OSS_ENDPOINT',
    'OSS_BUCKET_NAME'
]

# 检查必需环境变量
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"缺少必需环境变量: {', '.join(missing_vars)}")


class OSSClient:
    """阿里云OSS操作客户端"""

    # 使用单例模式初始化OSS客户端
    _auth = None
    _bucket = None

    @classmethod
    def _init_oss_client(cls):
        """初始化OSS客户端（内部方法）"""
        if not cls._bucket:
            # 从环境变量获取OSS配置
            endpoint = os.getenv('OSS_ENDPOINT')
            bucket_name = os.getenv('OSS_BUCKET_NAME')
            access_key_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
            access_key_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')

            # 创建鉴权对象和Bucket实例
            cls._auth = oss2.Auth(access_key_id, access_key_secret)
            cls._bucket = oss2.Bucket(cls._auth, endpoint, bucket_name)

    @classmethod
    async def upload_file(cls, file_content: bytes, filename: str) -> str:
        """
        上传文件到OSS
        :param file_content: 文件二进制内容
        :param filename: 原始文件名（用于扩展名提取）
        :return: 文件访问URL
        """
        cls._init_oss_client()  # 确保客户端已初始化

        try:
            # 生成唯一文件名（MD5哈希 + 时间戳）
            file_hash = hashlib.md5(file_content).hexdigest()
            file_ext = os.path.splitext(filename)[1].lower()
            object_name = f"uploads/{file_hash}{file_ext}"
            content_type = 'image/jpeg'
            # 上传文件到OSS（设置公共读权限）
            result = cls._bucket.put_object(
                object_name,
                file_content
            )


            if result.status == 200:
                expires = 3600  # 1小时有效
                signed_url = cls._bucket.sign_url('GET', object_name, expires)
                return signed_url
            raise RuntimeError("OSS上传失败")

        except oss2.exceptions.OssError as e:
            raise RuntimeError(f"OSS操作异常: {e}") from e


class AliCloudClient:
    """阿里云图像处理客户端工厂类"""

    @staticmethod
    def create_client() -> ImageClient:
        """
        创建阿里云图像处理客户端
        基于环境变量中的AccessKey进行认证
        返回: ImageClient实例
        异常: 当环境变量未配置时抛出RuntimeError
        """
        # 获取环境变量配置
        access_key_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
        access_key_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
        endpoint = 'imageprocess.cn-shanghai.aliyuncs.com'  # 服务固定端点

        # 配置校验
        if not all([access_key_id, access_key_secret]):
            raise RuntimeError("阿里云AccessKey未正确配置")

        # 构建SDK配置对象
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint=endpoint
        )

        return ImageClient(config)


async def handle_aliyun_exception(error: Exception) -> Dict[str, Any]:
    """统一处理阿里云API异常"""
    error_info = {
        "error_type": "ALIYUN_API_ERROR",
        "message": str(getattr(error, 'message', '未知错误')),
        "request_id": getattr(error, 'request_id', None),
        "recommend": getattr(error, 'data', {}).get("Recommend", None)
    }
    return error_info


def validate_diagnosis_data_1(data: Dict[str, Any]) -> Dict[str, Any]:
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


@router.post("/detect-by-url",
             summary="通过URL检测皮肤病",
             description="使用存储在互联网上的图片进行分析",
             response_model=Dict[str, Any])
async def detect_by_url(url: str, org_id: str = "default_org") -> JSONResponse:
    """
    通过图片URL进行皮肤病检测

    参数说明:
    - url: 图片的公开可访问URL（需包含http/https协议头）
    - org_id: 机构标识（用于使用统计，默认值即可）

    返回示例:
    {
        "data": {
            "results": [
                {
                    "disease": "湿疹",
                    "probability": 0.87,
                    "locations": [...]
                }
            ]
        }
    }
    """
    try:
        # 初始化阿里云客户端
        client = AliCloudClient.create_client()

        # 构建API请求参数
        request = viapi_models.DetectSkinDiseaseRequest(
            url=url,
            org_id=org_id,
            org_name="derm_api_server"  # 固定机构名称
        )

        # 配置运行时参数（保持默认）
        runtime = util_models.RuntimeOptions()

        # 发送异步检测请求
        response = await client.detect_skin_disease_with_options_async(request, runtime)

        # 将阿里云响应转换为字典格式
        return JSONResponse(content=response.body.to_map())

    except Exception as e:
        error_data = await handle_aliyun_exception(e)
        raise HTTPException(status_code=500, detail=error_data)


@router.post("/detect-by-upload",
             summary="上传图片检测皮肤病",
             description="支持JPG/PNG格式，图片大小不超过5MB",
             response_model=Dict[str, Any])
async def detect_by_upload(
        file: UploadFile = File(..., description="需要分析的图片文件（支持JPEG/PNG）"),
        org_id: str = "default_org"
):
    """
    完整检测流程：
    1. 接收上传文件 → 2. 验证文件 → 3. 上传OSS → 4. 调用检测API

    参数说明:
    - file: 通过表单上传的图片文件
    - org_id: 机构标识（默认值即可）

    返回结构同/detect-by-url接口
    """
    try:
        # 重置文件指针
        file.file.seek(0)
        # 这里添加更多日志，方便排查问题
        logging.info(f"Starting detect_by_upload with file: {file.filename}")
        # === 1. 文件验证 ===
        # 验证文件类型（同时检查MIME类型和文件扩展名）
        allowed_types = {"image/jpeg", "image/png"}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if (file.content_type not in allowed_types) or (file_ext not in [".jpg", ".jpeg", ".png"]):
            raise HTTPException(400, detail="仅支持JPEG/PNG格式")

        # === 2. 读取并验证文件 ===
        content = await file.read()

        # 验证文件大小（5MB限制）
        max_size = 5 * 1024 * 1024  # 5MB
        if len(content) > max_size:
            raise HTTPException(413, detail="文件大小超过5MB限制")

        # === 3. 上传到OSS ===
        oss_url = await OSSClient.upload_file(content, file.filename)
        print(f"文件上传成功，OSS地址: {oss_url}")

        # === 4. 调用检测API ===
        client = AliCloudClient.create_client()
        request = viapi_models.DetectSkinDiseaseRequest(
            url=oss_url,
            org_id=org_id,
            org_name="user_upload"
        )
        runtime = util_models.RuntimeOptions()
        response = await client.detect_skin_disease_with_options_async(request, runtime)
        print(f"response: {response}")
        result = response.body.to_map()
        print(f'result: {result}')
        result_1 = validate_diagnosis_data_1(result)
        print(f'result_1: {result_1}')

        return result_1

    except HTTPException as he:
        # 传递已知的HTTP异常
        raise he
    except Exception as e:
        # 处理其他未知异常
        error_data = {
            "error_type": type(e).__name__,
            "message": str(e),
            "request_id": getattr(e, 'request_id', None)
        }
        raise HTTPException(status_code=500, detail=error_data)


# 本地测试方法（生产环境请勿使用）
if __name__ == '__main__':
    import uvicorn
    from pathlib import Path

    # 环境变量文件检查
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        raise FileNotFoundError("缺少.env配置文件")

    # 启动测试服务器
    uvicorn.run(
        "ali_api_yunapi_predict:router",
        host="0.0.0.0",
        port=8000,
        reload=True,
        ssl_keyfile=os.getenv("SSL_KEY_PATH", None),
        ssl_certfile=os.getenv("SSL_CERT_PATH", None)
    )
