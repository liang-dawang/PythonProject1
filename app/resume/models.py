from pydantic import BaseModel

# 前端传入的简历数据模型
class ResumeData(BaseModel):
    name: str
    education: str
    major: str
    desiredJob: str
    coreSkill: str
    certificate: str = ""
    expectedSalary: str = ""
    skillLevel: str = ""
    stackDetail: str = ""
    innovation: str = ""
    learning: str = ""
    pressureResistance: str = ""
    communication: str = ""
    internshipProject: str = ""
    internshipDuration: str = ""
    projectAchievement: str = ""

# 学生画像模型
class StudentPortrait(BaseModel):
    professional_skills: list | str  # 专业技能
    certificates: list | str         # 证书
    innovation: str                  # 创新能力
    learning_ability: str            # 学习能力
    pressure_resistance: str         # 抗压能力
    communication: str               # 沟通能力
    internship_ability: str          # 实习能力
    completeness_score: float        # 完整度评分（0-100）
    competitiveness_score: float     # 竞争力评分（0-100）

# 接口返回结果模型
class ResumeResponse(BaseModel):
    status: str
    message: str
    data: dict = {}