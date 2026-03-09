# app/resume/router.py
from fastapi import APIRouter
from .models import ResumeData, ResumeResponse
from .service import process_resume_data  # 导入服务层函数

# 创建路由
resume_router = APIRouter(prefix="/user", tags=["简历相关接口"])

# 简历数据接收接口
@resume_router.post("/resume-text", response_model=ResumeResponse)
async def receive_resume_data(resume: ResumeData):
    # 核心：调用服务层处理数据（业务逻辑全在service里）
    result = process_resume_data(resume)
    # 直接返回处理结果
    return result