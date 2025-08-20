from dotenv import load_dotenv
load_dotenv()
from fastapi import APIRouter
from extra_function import get_current_user, search_patient
# 修改main函数支持异步
from threading import Thread

# 修改FastAPI路由
from fastapi import Depends, HTTPException
from models import User, Patient
import logging
import asyncio

logger = logging.getLogger(__name__)



# 从环境变量加载配置
import os
from dotenv import load_dotenv

load_dotenv()

# 星火认知大模型Spark Max的URL值，其他版本大模型URL值请前往文档（https://www.xfyun.cn/doc/spark/Web.html）查看
SPARKAI_URL = os.getenv('SPARKAI_URL', 'wss://spark-api.xf-yun.com/v4.0/chat')
# 星火认知大模型调用秘钥信息，请前往讯飞开放平台控制台（https://console.xfyun.cn/services/bm35）查看
SPARKAI_APP_ID = os.getenv('SPARKAI_APP_ID')
SPARKAI_API_SECRET = os.getenv('SPARKAI_API_SECRET')
SPARKAI_API_KEY = os.getenv('SPARKAI_API_KEY')
# 星火认知大模型Spark Max的domain值，其他版本大模型domain值请前往文档（https://www.xfyun.cn/doc/spark/Web.html）查看
SPARKAI_DOMAIN = os.getenv('SPARKAI_DOMAIN', '4.0Ultra')

# -*- coding: utf-8 -*-
"""
讯飞星火大模型API调用模块（WebSocket版）
功能：实现与讯飞星火大模型的对话交互
特点：
1. 模块化设计，各功能独立
2. 详细注释说明
3. 完善的错误处理
4. 支持多版本API配置
"""

# ---------- 基础库导入 ----------
import base64
import hashlib
import hmac
from datetime import datetime
from time import mktime
from urllib.parse import urlparse, urlencode
from wsgiref.handlers import format_date_time

router = APIRouter()


# ---------- 配置参数类 ----------
class SparkConfig:
    """配置参数容器类"""

    def __init__(self, appid, api_key, api_secret, spark_url, domain):
        # 认证信息（控制台获取）
        self.appid = appid  # 应用ID
        self.api_key = api_key  # API密钥
        self.api_secret = api_secret  # API密钥密文

        # 服务配置
        self.spark_url = spark_url  # WebSocket连接地址
        self.domain = domain  # 模型领域配置

        # 对话参数
        self.temperature = 0.5  # 生成随机性（0-1）
        self.max_tokens = 4096  # 生成最大长度
        self.auditing = "default"  # 内容安全检测


# ---------- WebSocket参数生成器 ----------
class WsParamGenerator:
    """WebSocket连接参数生成器"""

    def __init__(self, config: SparkConfig):
        # 解析URL信息
        self.host = urlparse(config.spark_url).netloc  # 域名
        self.path = urlparse(config.spark_url).path  # 路径

        # 保存配置信息
        self.config = config

    def _generate_signature(self):
        """生成请求签名（HMAC-SHA256加密）"""
        # 生成RFC1123格式时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 构造签名原始字符串
        signature_origin = f"host: {self.host}\ndate: {date}\nGET {self.path} HTTP/1.1"

        # 使用HMAC-SHA256加密
        signature_sha = hmac.new(
            self.config.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()

        # Base64编码
        return base64.b64encode(signature_sha).decode('utf-8')

    def generate_url(self):
        """生成带鉴权参数的WebSocket连接URL"""
        signature = self._generate_signature()

        # 构造鉴权参数
        authorization_params = {
            "authorization": base64.b64encode(
                f'api_key="{self.config.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'.encode()
            ).decode(),
            "date": format_date_time(mktime(datetime.now().timetuple())),
            "host": self.host
        }
        final_url = f"{self.config.spark_url}?{urlencode(authorization_params)}"
        print("[DEBUG] 生成的WebSocket URL:", final_url)  # 调试输出
        return final_url


# ---------- 请求参数生成器 ----------
class RequestParamsGenerator:
    @staticmethod
    def generate(config: SparkConfig, query: str):
        # 修正后的参数结构（根据讯飞API 4.0文档）
        return json.dumps({
            "header": {
                "app_id": config.appid,
                "uid": "1234"
            },
            "parameter": {
                "chat": {
                    "domain": config.domain.split("：")[0],  # 移除中文冒号
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens,
                    # "auditing": config.auditing  # 该字段在4.0版本已废弃
                }
            },
            "payload": {
                "message": {
                    "text": [
                        {"role": "user", "content": query}
                    ]
                }
            }
        })


# ---------- WebSocket处理器 ----------
# 在SparkWebSocketHandler类中添加回调功能
# ---------- WebSocket处理器 ----------
# ---------- 关键修正代码 ----------
import websocket
import ssl
import json
from queue import Queue


class SparkWebSocketHandler:
    """重构后的WebSocket处理器（支持完整生命周期管理）"""

    def __init__(self, config: SparkConfig, query: str):
        self.config = config
        self.query = query
        self.ws = None
        self.response_queue = Queue()
        self.loop = asyncio.new_event_loop()
        self.request_params = RequestParamsGenerator.generate(config, query)

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            if data['header']['code'] != 0:
                error = f"API错误: {data['header']['code']}-{data['header']['message']}"
                self.response_queue.put(('error', error))
                ws.close()
                return

            content = data["payload"]["choices"]["text"][0]["content"]
            status = data["payload"]["choices"]["status"]

            self.response_queue.put(('message', content))

            if status == 2:  # 对话完成
                self.response_queue.put(('done', None))
                ws.close()

        except Exception as e:
            error = f"消息处理失败: {str(e)}"
            self.response_queue.put(('error', error))
            ws.close()

    def _on_error(self, ws, error):
        self.response_queue.put(('error', f"连接错误: {str(error)}"))

    def _on_close(self, ws, close_status_code, close_msg):
        if close_status_code != 1000:
            self.response_queue.put(('error', f"异常关闭: {close_status_code}-{close_msg}"))

    def _on_open(self, ws):
        print("[DEBUG] 发送请求参数:", self.request_params)
        ws.send(self.request_params)

    def start(self):
        """启动WebSocket连接（同步方法）"""
        ws_url = WsParamGenerator(self.config).generate_url()

        self.ws = websocket.WebSocketApp(
            ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )

        # 配置SSL并启动
        ssl_opt = {"cert_reqs": ssl.CERT_NONE, "ssl_version": ssl.PROTOCOL_TLS_CLIENT}
        self.ws.run_forever(sslopt=ssl_opt, ping_interval=30)


async def async_main(query: str):
    """异步主函数"""
    config = SparkConfig(
        appid=SPARKAI_APP_ID,
        api_key=SPARKAI_API_KEY,
        api_secret=SPARKAI_API_SECRET,
        spark_url=SPARKAI_URL,
        domain=SPARKAI_DOMAIN
    )

    handler = SparkWebSocketHandler(config, query)
    loop = asyncio.get_running_loop()
    result = []

    # 在独立线程中运行WebSocket客户端
    def run_handler():
        try:
            handler.start()
        except Exception as e:
            handler.response_queue.put(('error', str(e)))

    Thread(target=run_handler).start()

    # 异步处理响应队列
    while True:
        if not handler.response_queue.empty():
            msg_type, content = handler.response_queue.get()

            if msg_type == 'message':
                result.append(content)
            elif msg_type == 'error':
                raise Exception(content)
            elif msg_type == 'done':
                return ''.join(result)
        else:
            await asyncio.sleep(0.1)



def main(user_query_text):
    config = SparkConfig(appid=SPARKAI_APP_ID, api_key=SPARKAI_API_KEY, api_secret=SPARKAI_API_SECRET,
                         spark_url=SPARKAI_URL, domain=SPARKAI_DOMAIN)  # 保持原有配置

    # 创建事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 用于收集结果的Future
    future = loop.create_future()

    def callback(content, is_done=False):
        if is_done:
            loop.call_soon_threadsafe(future.set_result, content)

    handler = SparkWebSocketHandler(config, user_query_text, callback)

    # 在独立线程中运行WebSocket
    # 正确调用方式
    def run_handler():
        handler = SparkWebSocketHandler(config, user_query_text)
        handler.start()  # 调用存在的start方法

    Thread(target=run_handler).start()

    # 等待异步结果
    return loop.run_until_complete(future)

@router.post("/illness_analysis", summary="输入病症名称，然后病症分析")
async def illness_analysis_1(text: str, description: str = '请按照以下模板进行描述',
                             user: User = Depends(get_current_user),
                             current_patient: Patient = Depends(search_patient)):
    if not user.patient_status:
        return {"code": 403, "data": {"message": "Only patients can make appointments."}}
    print(f'user.patient_status: {user.patient_status}')
    # 构建问题模板
    gender = current_patient.gender
    if gender not in ['男', '女', '男生', '女生', '男性', '女性']:
        gender = '男'
    print(f"gender: {gender}")
    age = current_patient.age
    print(f"age: {age}")
    if age <= 0:
        age = 20
    user_query_text = f'''
    请作为资深皮肤科主任医师，为{age}岁{gender}性患者提供详细诊疗建议：
    针对{text},
    请为患者提供详细的诊疗建议。请按照以下结构组织回答：

    **1. 病症分析**
    - 初步判断的可能疾病
    - 典型症状描述
    - 与其他相似疾病的鉴别要点

    **2. 致病因素分析**
    - 主要致病原因（内因/外因）
    - 易感人群特征
    - 常见诱发/加重因素
    - 相关实验室检查建议

    **3. 治疗方案**
    〖核心方案〗
    - 分阶段治疗策略（急性期/缓解期/维持期）
    - 推荐治疗方案排序（首选/备选）

    〖药物治疗〗
    请按以下格式说明每种药物：
    ```text
    | 药品通用名 | 商品名举例 | 药物类别 | 作用机制 | 
    |------------|------------|----------|----------|
    | 阿达帕林   | 达芙文     | 维A酸类  | 调节角质代谢 |

    » 用药指导：
    - 剂型选择（乳膏/凝胶/溶液）
    - 标准剂量与用药频率
    - 具体使用方法（清洁后薄涂等）
    - 疗程建议
    - 特殊人群调整（孕妇/儿童/肝肾功能不全）

    » 安全警示：
    - 已知不良反应
    - 禁忌症（药物/疾病）
    - 药物相互作用
    - 储存条件与有效期

    **4. 辅助治疗建议**
    - 物理治疗选择（光疗等）
    - 中医辅助方案（需标注证据等级）
    - 生活管理建议（饮食/作息/皮肤护理）

    **5. 随访规划**
    - 复诊时间节点
    - 疗效评估标准
    - 病情恶化预警指征

    **6. 患者教育**
    - 疾病认知误区澄清
    - 日常注意事项清单
    - 推荐可靠信息来源
    最后，请按照一段文本来输出，不要带有任何不友好的符号和格式（比如*、|--|和换行），以文章形式给出，可以用双引号，句号或者逗号。字体都是大小一样，无特殊标记！  
        '''

    try:
        response = await async_main(user_query_text)
        return {
            "code": 200,
            "data": {
                "analysis": response,
                "disclaimer": "本建议仅供参考，具体诊疗请遵医嘱"
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"大模型服务异常：{str(e)}"
        )


async def illness_analysis(text: str, description: str = '请按照以下模板进行描述',
                           current_patient: Patient = None):
    # 构建问题模板
    gender = current_patient.gender
    if gender not in ['男', '女', '男生', '女生', '男性', '女性']:
        gender = '男'
    print(f"gender: {gender}")
    age = current_patient.age
    print(f"age: {age}")
    if age <= 0:
        age = 20

    user_query_text = f'''
    请作为资深皮肤科主任医师，为{age}岁{gender}性患者提供详细诊疗建议：
    针对{text},
    请为患者提供详细的诊疗建议。请按照以下结构组织回答：

    **1. 病症分析**
    - 初步判断的可能疾病
    - 典型症状描述
    - 与其他相似疾病的鉴别要点

    **2. 致病因素分析**
    - 主要致病原因（内因/外因）
    - 易感人群特征
    - 常见诱发/加重因素
    - 相关实验室检查建议

    **3. 治疗方案**
    〖核心方案〗
    - 分阶段治疗策略（急性期/缓解期/维持期）
    - 推荐治疗方案排序（首选/备选）

    〖药物治疗〗
    请按以下格式说明每种药物：
    ```text
    | 药品通用名 | 商品名举例 | 药物类别 | 作用机制 | 
    |------------|------------|----------|----------|
    | 阿达帕林   | 达芙文     | 维A酸类  | 调节角质代谢 |

    » 用药指导：
    - 剂型选择（乳膏/凝胶/溶液）
    - 标准剂量与用药频率
    - 具体使用方法（清洁后薄涂等）
    - 疗程建议
    - 特殊人群调整（孕妇/儿童/肝肾功能不全）

    » 安全警示：
    - 已知不良反应
    - 禁忌症（药物/疾病）
    - 药物相互作用
    - 储存条件与有效期

    **4. 辅助治疗建议**
    - 物理治疗选择（光疗等）
    - 中医辅助方案（需标注证据等级）
    - 生活管理建议（饮食/作息/皮肤护理）

    **5. 随访规划**
    - 复诊时间节点
    - 疗效评估标准
    - 病情恶化预警指征

    **6. 患者教育**
    - 疾病认知误区澄清
    - 日常注意事项清单
    - 推荐可靠信息来源
    最后，请按照一段文本来输出，不要带有任何不友好的符号和格式（比如*、|--|和换行），以文章形式给出，可以用双引号，句号或者逗号。字体都是大小一样，无特殊标记！  
        '''

    try:
        response = await async_main(user_query_text)
        return {
            "code": 200,
            "data": {
                "analysis": response,
                "disclaimer": "本建议仅供参考，具体诊疗请遵医嘱"
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"大模型服务异常：{str(e)}"
        )


# ---------- 修正FastAPI路由 ----------
@router.post("/communicate", summary='AI——Chat')
async def communicate(text: str):
    try:
        response = await async_main(text)
        return {"code": 200, "data": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 修改启动方式（确保异步兼容）
if __name__ == "__main__":
    main("你是讯飞星火大模型吗？")
