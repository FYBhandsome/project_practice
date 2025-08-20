from fastapi import APIRouter, Form, File, UploadFile, HTTPException
from models import Post, User
from fastapi import Depends
import os
import logging
from datetime import datetime
from extra_function import get_current_user
import base64

router = APIRouter()
UPLOAD_DIR = "uploads"

# 假设这是允许的文件类型检查函数
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 封装函数，处理文件上传并返回二进制数据
async def process_uploaded_file(file: UploadFile):
    """
    处理上传的文件，进行格式检验并返回二进制内容
    :param file: 上传的文件
    :return: 文件的二进制内容
    """
    if not allowed_file(file.filename):
        raise HTTPException(400, "文件类型不支持")
    try:
        # 获取文件大小
        file.file.seek(0, 2)  # 移动到文件末尾
        file_size = file.file.tell()
        if file_size == 0:
            raise HTTPException(400, "上传的文件为空")
        # 重置文件指针到文件开头
        await file.seek(0)
        # 读取文件内容
        content = await file.read()
        return content
    except Exception as e:
        raise HTTPException(500, f"读取文件时出错: {str(e)}")