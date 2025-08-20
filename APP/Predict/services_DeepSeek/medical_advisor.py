"""
医疗顾问服务模块（优化版）
功能：整合皮肤病诊断与智能建议生成，包含药品安全验证
核心优化点：
1. 增强错误处理机制
2. 配置化管理API参数
3. 改进响应解析可靠性
4. 增加请求重试机制
5. 完善类型注解和文档
"""

# 标准库导入
import os
import json
import logging
from typing import Dict, Any, List, Optional
import re  # 新增正则表达式模块

# 第三方库导入
import aiohttp
from dotenv import load_dotenv
from pydantic import BaseModel, Field  # 新增数据验证模型

# 环境变量加载
load_dotenv()

# 初始化日志
logger = logging.getLogger(__name__)


class MedicalRequest(BaseModel):
    """医疗建议请求参数模型"""
    disease: str = Field(..., min_length=2, description="确诊疾病名称")
    confidence: float = Field(..., ge=0, le=100, description="诊断置信度百分比")


class MedicationConflict(BaseModel):
    """药物冲突信息模型"""
    drug: str
    conflicted_with: List[str]
    severity: str


class MedicalAdvisor:
    """
    增强版医疗顾问系统
    功能扩展：
    - 带重试机制的API调用
    - 基于正则的响应解析
    - 可配置的药品冲突规则
    - 完整的错误跟踪
    """

    def __init__(self):
        """
        初始化方法（配置驱动）
        环境变量需求：
        - DEEPSEEK_API_KEY: API认证密钥
        - DEEPSEEK_MODEL: 模型名称（默认：deepseek-medical-1.3b）
        - API_MAX_RETRIES: 最大重试次数（默认：3）
        """
        self.deepseek_url = os.getenv("DEEPSEEK_URL", "https://api.deepseek.com/v1/chat/completions")
        self.model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-medical-1.3b")
        self.max_retries = int(os.getenv("API_MAX_RETRIES", 3))

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}"
        }

        # 可配置的冲突规则（可从文件加载）
        self.conflict_rules = json.loads(
            os.getenv("CONFLICT_RULES", json.dumps({
                "阿维A": {"conflicts": ["四环素类抗生素", "甲氨蝶呤"], "severity": "高危"},
                "环孢素": {"conflicts": ["辛伐他汀"], "severity": "中危"}
            }))
        )

    async def generate_advice(self, disease_info: MedicalRequest) -> Dict[str, Any]:
        """
        生成医疗建议（带重试机制）
        参数:
            disease_info: 经校验的诊断信息对象
        返回:
            {
                "analysis": 疾病分析,
                "treatment": 治疗方案,
                "medication": 药品建议,
                "warnings": 安全警告
            }
        异常:
            APIConnectionError: API连接失败
            ValidationError: 响应解析失败
        """
        prompt = self._build_medical_prompt(disease_info)

        async with aiohttp.ClientSession(headers=self.headers) as session:
            for attempt in range(self.max_retries):
                try:
                    return await self._call_deepseek_api(session, prompt)
                except (aiohttp.ClientError, json.JSONDecodeError) as e:
                    if attempt == self.max_retries - 1:
                        logger.error(f"API请求失败，已达最大重试次数: {str(e)}")
                        raise
                    logger.warning(f"API请求失败，正在重试({attempt + 1}/{self.max_retries})")

    def _build_medical_prompt(self, request: MedicalRequest) -> str:
        """
        构建结构化提示模板
        使用三重引号保持格式清晰，包含：
        - 明确的章节标记（##）
        - 严格的格式要求
        - 示例说明
        """
        return f"""
        ## 患者诊断信息
        确诊疾病：{request.disease}
        置信度：{request.confidence}%

        ## 请求内容
        请按以下结构生成专业诊疗建议：

        ### 疾病简介
        - 通俗解释（不超过100字）
        - 常见症状

        ### 阶段治疗方案
        [按急性期、缓解期、康复期分阶段说明]

        ### 药物建议
        [表格形式，包含：
        | 药品名称（通用名） | 商品名 | 类型（OTC/Rx） | 用法用量 | 注意事项 |
        ]

        ### 生活建议
        - 饮食禁忌
        - 日常护理
        - 康复锻炼

        ### 复诊指导
        - 复诊时间
        - 必要检查项目

        ## 格式要求
        1. 使用Markdown语法
        2. 药品图片使用Unsplash关键词：
           ![药品名](https://source.unsplash.com/featured/?[关键词])
        3. 重要内容用**加粗**显示
        """

    async def _call_deepseek_api(self, session: aiohttp.ClientSession, prompt: str) -> Dict[str, Any]:
        """执行DeepSeek API调用"""
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "您是三甲医院皮肤科主任医师，需提供专业可靠的诊疗建议"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }

        try:
            async with session.post(self.deepseek_url, json=payload) as resp:
                resp.raise_for_status()
                response_data = await resp.json()
                return self._parse_response(response_data["choices"][0]["message"]["content"])
        except KeyError as e:
            logger.error("API响应结构异常", exc_info=True)
            raise ValueError("无效的API响应格式") from e

    def _parse_response(self, raw_text: str) -> Dict[str, Any]:
        """
        使用正则表达式解析响应内容
        改进点：
        - 不依赖固定标题顺序
        - 容错性更强的模式匹配
        """
        patterns = {
            "analysis": r"## 疾病简介\n+(.*?)(?=\n## |$)",
            "treatment": r"## 阶段治疗方案\n+(.*?)(?=\n## |$)",
            "medication": r"## 药物建议\n+(.*?)(?=\n## |$)",
            "lifestyle": r"## 生活建议\n+(.*?)(?=\n## |$)",
            "follow_up": r"## 复诊指导\n+(.*?)(?=\n## |$)"
        }

        result = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, raw_text, re.DOTALL)
            result[key] = match.group(1).strip() if match else "未提供相关信息"

        # 自动提取药品列表用于冲突检查
        medications = self._extract_medications(result.get("medication", ""))
        result["warnings"] = self.check_contraindications(medications)

        return result

    def _extract_medications(self, medication_text: str) -> List[str]:
        """从药物建议中提取药品名称"""
        return re.findall(r"\|\s*(.*?)\s*\|", medication_text)

    def check_contraindications(self, medications: List[str]) -> List[MedicationConflict]:
        """增强版冲突检查（返回结构化数据）"""
        conflicts = []
        for drug in medications:
            if drug in self.conflict_rules:
                conflicts.append(MedicationConflict(
                    drug=drug,
                    conflicted_with=self.conflict_rules[drug]["conflicts"],
                    severity=self.conflict_rules[drug]["severity"]
                ))
        return conflicts

    async def validate_medication(self, drug_name: str) -> Optional[Dict]:
        """药品验证（预留接口）"""
        # 实际实现需对接药品数据库API
        return {
            "name": drug_name,
            "valid": True,
            "message": "验证功能需配置专业数据库"
        }