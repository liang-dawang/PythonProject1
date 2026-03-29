# app/resume/router.py
import time  # ← 必须有这行！

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import os
import tempfile
import json
from app.db import get_latest_student_profile  # 导入数据库函数
from app.resume.scoring_service import calculate_competitiveness_score# 导入评分逻辑
from .models import ResumeData, ResumeResponse,MatchingResponse,JobMatchItem # ← 注意是 ResumeTextInput
from .servicetext import resume_parser_async  # ← 你已有的服务函数

resume_router = APIRouter(prefix="/user", tags=["简历分析"])

# 定义严格的返回模型，确保数据类型可序列化

# ================== 接口1：纯文本简历 ==================
@resume_router.post("/resume-text", response_model=ResumeResponse)
async def analyze_resume_text(request: ResumeData):
    """
    接收结构化简历数据，拼接为自然语言文本，再交由大模型标准化解析
    """
    try:
        # === 关键：将结构化字段拼成一段连贯的简历文本 ===
        parts = []

        if request.name:
            parts.append(f"姓名：{request.name}")
        if request.education:
            parts.append(f"学历：{request.education}")
        if request.major:
            parts.append(f"专业：{request.major}")
        if request.desiredJob:
            parts.append(f"求职意向：{request.desiredJob}")
        if request.desiredSalary:
            parts.append(f"期望薪资：{request.desiredSalary}")
        if request.coreSkill:
            parts.append(f"专业技能：{request.coreSkill}")
        if request.certificate:
            parts.append(f"证书：{request.certificate}")
        if request.innovation:
            parts.append(f"创新能力：{request.innovation}")
        if request.learning:
            parts.append(f"学习能力：{request.learning}")
        if request.pressureResistance:
            parts.append(f"抗压能力：{request.pressureResistance}")
        if request.communication:
            parts.append(f"沟通能力：{request.communication}")
        if request.internshipProject or request.internshipDuration:
            intern = " ".join(filter(None, [request.internshipProject, request.internshipDuration]))
            parts.append(f"实习经历：{intern}")
        if request.projectAchievement:
            parts.append(f"项目成果：{request.projectAchievement}")

        resume_text = "；".join(parts) + "。"

        # === 调用原有大模型解析流程 ===
        result = resume_parser_async(
            student_name=request.name,
            resume_input=resume_text,
            input_type="text"
        )

        if result["code"] == 200:
            return ResumeResponse(
                status="success",
                message=result["msg"],
                data=result["data"]
            )
        else:
            raise HTTPException(status_code=500, detail=result["msg"])

    except Exception as e:
        return ResumeResponse(
            status="error",
            message=f"处理失败: {str(e)}",
            data=None
        )


@resume_router.post("/resume-picture", response_model=ResumeResponse)
async def analyze_resume_picture(file: UploadFile = File(...)):
    if not file.content_type.startswith(("image/", "application/pdf")):
        raise HTTPException(status_code=400, detail="仅支持图片或PDF文件")

    temp_dir = tempfile.gettempdir()
    # ✅ 现在 time.time() 可用
    temp_filename = f"resume_{int(time.time() * 1000)}_{file.filename}"
    temp_path = os.path.join(temp_dir, temp_filename)

    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        result = resume_parser_async(
            student_name="未知姓名",
            resume_input=temp_path,
            input_type="image"
        )

        if result["code"] == 200:
            return ResumeResponse(status="success", message=result["msg"], data=result["data"])
        else:
            raise HTTPException(status_code=500, detail=result["msg"])

    except Exception as e:
        return ResumeResponse(status="error", message=f"图片处理失败: {str(e)}", data=None)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@resume_router.post("/resume/matching-trigger")
async def analyze_resume_trigger():
    student_profile = await get_latest_student_profile()

    if not student_profile:
        raise HTTPException(status_code=404, detail="未找到学生数据")

    # ✅ 关键：从 profile 中取出 id 并转为字符串
    student_id = str(student_profile.get("id"))
    if not student_id or student_id == "None":
        raise HTTPException(status_code=400, detail="学生数据缺少 id 字段")

    # ✅ 正确传入 student_id
    result = calculate_competitiveness_score(
        student_profile=student_profile,
        student_id=student_id
    )

    # 可选：如果 scoring 函数返回 error，也抛出异常
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result