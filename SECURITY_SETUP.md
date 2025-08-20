# 🔐 安全配置指南

## ⚠️ 重要安全提醒

您的代码中包含敏感信息，请按照以下步骤进行安全配置：

## 1. 立即需要处理的问题

### 发现的敏感信息：
- 阿里云API密钥（在 `environment_variables.bat` 中）
- DeepSeek API密钥（在 `environment_variables.bat` 中）
- 讯飞星火API密钥（在多个Python文件中硬编码）

## 2. 安全配置步骤

### 步骤1：创建环境变量文件
创建 `.env` 文件（已在 `.gitignore` 中忽略）：

```bash
# 阿里云配置
ALIBABA_CLOUD_ACCESS_KEY_ID=your_aliyun_access_key_id_here
ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_aliyun_access_key_secret_here
OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
OSS_BUCKET_NAME=your_bucket_name_here

# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_URL=https://api.deepseek.com/v1/chat/completions
DEEPSEEK_MODEL=deepseek-medical-1.3b

# 讯飞星火API配置
SPARKAI_APP_ID=your_sparkai_app_id_here
SPARKAI_API_SECRET=your_sparkai_api_secret_here
SPARKAI_API_KEY=your_sparkai_api_key_here
SPARKAI_URL=wss://spark-api.xf-yun.com/v4.0/chat
SPARKAI_DOMAIN=4.0Ultra

# JWT配置
SECRET_KEY=your_jwt_secret_key_here
ALGORITHM=HS256
```

### 步骤2：修改代码中的硬编码密钥

需要修改以下文件中的硬编码API密钥：

1. `APP/Predict/services_xunfeixinghuo/communicate.py`
2. `APP/Predict/services_xunfeixinghuo/sparkAPI.py`

将这些硬编码的密钥替换为环境变量：

```python
import os
from dotenv import load_dotenv

load_dotenv()

SPARKAI_APP_ID = os.getenv('SPARKAI_APP_ID')
SPARKAI_API_SECRET = os.getenv('SPARKAI_API_SECRET')
SPARKAI_API_KEY = os.getenv('SPARKAI_API_KEY')
```

### 步骤3：删除或重命名敏感文件

1. 删除或重命名 `environment_variables.bat` 文件
2. 确保 `.env` 文件不会被提交到Git

## 3. 验证配置

运行以下命令验证环境变量是否正确加载：

```python
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('环境变量加载成功' if os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID') else '环境变量未正确配置')"
```

## 4. 安全最佳实践

1. **永远不要**将API密钥提交到Git仓库
2. **永远不要**在代码中硬编码敏感信息
3. 使用环境变量或配置文件来管理敏感信息
4. 定期轮换API密钥
5. 使用最小权限原则配置API密钥

## 5. 如果密钥已泄露

如果您的API密钥已经泄露到GitHub：

1. 立即在相应的服务提供商控制台中撤销/重新生成密钥
2. 更新本地环境变量文件
3. 检查Git历史记录，考虑是否需要清理提交历史

## 6. 部署注意事项

在生产环境中：
- 使用环境变量管理系统
- 考虑使用密钥管理服务（如AWS KMS、Azure Key Vault等）
- 定期审计API密钥的使用情况
