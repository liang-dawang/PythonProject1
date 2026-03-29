from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    Column, String, Text, Float, JSON, DateTime,
    Integer, Boolean, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import time
from typing import Optional, List  # ← 新增导入

# ===================== 1. 初始化 SQLAlchemy 基类 =====================
Base = declarative_base()
class ResumeTextInput(BaseModel):
    user_id: str
    student_name: str
    text: str

class ResumeTextInput(BaseModel):
    student_name: str
    text: str
    user_id: str  # 可选，如果用得上

# ===================== 2. Pydantic 输入模型（前端传入） =====================
class ResumeData(BaseModel):
    name: str
    education: str
    major: str
    desiredJob: str
    coreSkill: str  # 前端传的是字符串，如 "java, redis"
    certificate: str = ""
    desiredSalary: str = ""
    innovation: str = ""
    learning: str = ""
    pressureResistance: str = ""
    communication: str = ""
    internshipProject: str = ""      # 可用于实习能力
    internshipDuration: str = ""     # 如 "6个月"
    projectAchievement: str = ""
class JobMatchItem(BaseModel):
    job_id: str
    job_title: str
    job_category: Optional[str] = None
    similarity_score: float

class MatchingResponse(BaseModel):
    top_matched_jobs: List[JobMatchItem]
    error: Optional[str] = None
# ===================== 3. 接口返回模型 =====================
class ResumeResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None  # ✅ 允许 None，默认值为 None

# ===================== 4. SQLAlchemy 数据库模型 =====================
class StudentPortraitDB(Base):
    __tablename__ = "student_portraits"

    id = Column(String(50), primary_key=True, default=lambda: f"stu_{int(time.time() * 1000)}")
    name = Column(String(50), nullable=False, comment="学生姓名")
    education = Column(String(20), comment="学历")
    major = Column(String(50), comment="专业")
    desired_job = Column(String(50), comment="求职意向")
    desired_salary = Column(String(20), comment="期望薪资")
    student_type = Column(String(20), comment="学生类型：fresh_grad/has_intern/experienced")
    work_experience_years = Column(Float, comment="工作/实习经验年限")
    professional_skills = Column(JSON, comment="专业技能列表")
    certificates = Column(JSON, comment="证书列表")
    innovation = Column(Text, comment="创新能力")
    learning_ability = Column(Text, comment="学习能力")
    pressure_resistance = Column(Text, comment="抗压能力")
    communication = Column(Text, comment="沟通能力")
    internship_ability = Column(Text, comment="实习/工作能力")
    completeness_score = Column(Float, comment="简历完整度评分")
    competitiveness_score = Column(Float, comment="求职竞争力评分")
    job_fitness_score = Column(Float, comment="岗位适配度最终得分")
    raw_resume_data = Column(JSON, comment="原始简历数据")
    create_time = Column(DateTime, default=datetime.now, comment="生成时间")

# ===================== 5. Pydantic ORM 模型（用于 API 返回） =====================
class StudentPortrait(BaseModel):
    id: str
    name: str
    education: Optional[str] = None
    major: Optional[str] = None
    desired_job: Optional[str] = None
    desired_salary: Optional[str] = None
    student_type: Optional[str] = None
    work_experience_years: Optional[float] = None

    professional_skills: List[str] = []
    certificates: List[str] = []
    innovation: str = ""
    learning_ability: str = ""
    pressure_resistance: str = ""
    communication: str = ""
    internship_ability: str = ""

    completeness_score: float = 0.0
    competitiveness_score: float = 0.0
    job_fitness_score: float = 0.0

    create_time: Optional[datetime] = None

    # ✅ 关键：Pydantic V2 替代 orm_mode
    model_config = ConfigDict(from_attributes=True)