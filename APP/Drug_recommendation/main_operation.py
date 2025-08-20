import openpyxl
from models import DrugInfo
from drug_operate import DrugManager, DiseaseDrugRecommendationManager
import asyncio
import logging
from main import TORTOISE_ORM
from tortoise import Tortoise

# 初始化日志
logging.basicConfig(level=logging.DEBUG)


# 初始化数据库的异步函数
async def init_db():
    await Tortoise.init(
        config=TORTOISE_ORM
    )
    # 使用 safe=True 参数避免重复创建已存在的表
    await Tortoise.generate_schemas(safe=True)


# 异步处理单条药物数据的函数
async def process_data_async(drug_info):
    # 确保字典的键都是字符串类型
    drug_info = {str(key): value for key, value in drug_info.items()}
    # 确保 manualId 是字符串类型
    if 'manualId' in drug_info:
        drug_info['manualId'] = str(drug_info['manualId'])
    # 确保 strength 是字符串类型
    if 'strength' in drug_info:
        drug_info['strength'] = str(drug_info['strength'])
    # 将字典转换为 DrugInfo 对象
    drug_obj = DrugInfo(**drug_info)

    try:
        # 异步添加药物信息
        added_drug = await DrugManager.add_drug(drug_obj)
        print("Added drug:", added_drug)
    except Exception as e:
        logging.error(f"Error adding drug: {e}", exc_info=True)


# 异步加载 Excel 数据的函数
async def load_data_async(file_path):
    logging.debug("Loading data...")
    try:
        # 加载 Excel 文件
        workbook = openpyxl.load_workbook(file_path)
        # 获取活动工作表
        sheet = workbook.active
        # 获取表头（第一行）作为字典的键
        headers = [cell.value for cell in sheet[1]]
        logging.debug("process one data...")
        tasks = []
        # 遍历除第一行之外的每一行
        for row in sheet.iter_rows(min_row=3, values_only=True):
            if row[0] is None:
                break
            # 将每一行数据与表头组合成一个字典
            row_dict = dict(zip(headers, row))
            # 创建协程任务并添加到任务列表中
            task = asyncio.create_task(process_data_async(row_dict))
            tasks.append(task)
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        logging.debug("process two data...")

    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        return "Error"
    return "Successfully loaded"


async def main():
    try:
        # 初始化数据库
        await init_db()
        # 异步加载数据
        message = await load_data_async("药物.xlsx")
        logging.info(message)
    finally:
        # 关闭数据库连接
        await Tortoise.close_connections()


if __name__ == "__main__":
    # 使用 asyncio.run() 简化事件循环管理
    asyncio.run(main())
