from .models import ResumeData, ResumeResponse, StudentPortrait
import os
import json
import time
import re
from dotenv import load_dotenv
import dashscope
from dashscope import Generation
import pandas as pd
from datetime import datetime

# ---------------------- 配置项（和岗位画像代码对齐） ----------------------
load_dotenv(r"E:\pycharm\PythonProject1\new\mima.env")
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
if not dashscope.api_key:
    raise ValueError("❌ 未获取到DASHSCOPE_API_KEY，请检查mima.env文件")

# 画像文件保存路径（可自定义）
PORTRAIT_SAVE_DIR = "./student_portraits"
# 确保保存目录存在
os.makedirs(PORTRAIT_SAVE_DIR, exist_ok=True)

# ---------------------- 通用函数（复用岗位画像的逻辑） ----------------------
def classify_student_type(resume: ResumeData) -> str:
    """
    识别学生类型（参考岗位画像的classify_job_type）
    返回："fresh_grad"（应届生无实习）、"has_intern"（有实习）、"experienced"（有工作经验）
    """
    text = f"{resume.internshipProject} {resume.internshipDuration}".lower()
    # 有实习经验关键词
    intern_keywords = ["实习", "项目", "1个月", "3个月", "6个月", "1年"]
    # 有工作经验关键词
    exp_keywords = ["工作", "全职", "正式", "1年以上", "2年"]

    if any(kw in text for kw in exp_keywords):
        return "experienced"
    elif resume.internshipProject and any(kw in resume.internshipProject for kw in intern_keywords):
        return "has_intern"
    else:
        return "fresh_grad"


def generate_score(resume: ResumeData, portrait: dict, student_type: str) -> tuple[float, float]:
    """
    参考岗位画像的经验要求生成逻辑，计算完整度和竞争力评分
    返回：(完整度评分, 竞争力评分)
    """
    # 1. 完整度评分（0-100）：基于信息填写维度
    completeness_score = 0
    # 必填项（每项10分）
    required_fields = [resume.name, resume.education, resume.major, resume.desiredJob, resume.coreSkill]
    completeness_score += sum(10 for field in required_fields if field and field.strip())

    # 选填项（每项5分）
    optional_fields = [
        resume.certificate, resume.skillLevel, resume.stackDetail,
        resume.innovation, resume.learning, resume.pressureResistance,
        resume.communication, resume.internshipProject, resume.projectAchievement
    ]
    completeness_score += sum(5 for field in optional_fields if field and field.strip())

    # 兜底：最大100分，最小0分
    completeness_score = min(completeness_score, 100)
    completeness_score = max(completeness_score, 0)

    # 2. 竞争力评分（0-100）：基于学生类型+岗位匹配度
    competitiveness_score = 60  # 基础分
    job_name = resume.desiredJob

    # 按学生类型加分
    if student_type == "has_intern":
        competitiveness_score += 15  # 有实习加15分
    elif student_type == "experienced":
        competitiveness_score += 20  # 有工作经验加20分

    # 按岗位匹配度加分（参考岗位画像的专业技能匹配）
    core_skills = resume.coreSkill.split(",") if resume.coreSkill else []
    # 岗位核心技能映射（可从你的岗位画像Excel中提取）
    job_skill_map = {
        "前端开发": ["vue", "react", "javascript", "html", "css"],
        "Java开发": ["java", "spring", "mysql", "微服务"],
        "测试工程师": ["测试", "python", "自动化", "jmeter"],
        "数据分析师": ["python", "pandas", "sql", "可视化"]
    }
    # 匹配岗位技能加分
    if job_name in job_skill_map:
        match_count = sum(1 for skill in core_skills if any(kw in skill.lower() for kw in job_skill_map[job_name]))
        competitiveness_score += match_count * 5  # 每项匹配加5分

    # 兜底：最大100分，最小0分
    competitiveness_score = min(competitiveness_score, 100)
    competitiveness_score = max(competitiveness_score, 0)

    return round(completeness_score, 1), round(competitiveness_score, 1)


def call_dashscope_generate_portrait(resume: ResumeData) -> StudentPortrait:
    """
    参考岗位画像的generate_portfolio_for_job函数，调用通义千问生成学生画像
    差异化处理：应届生/有实习/有工作经验
    """
    # 第一步：识别学生类型
    student_type = classify_student_type(resume)
    # 第二步：构造差异化提示词（参考岗位画像的prompt逻辑）
    if student_type == "fresh_grad":
        student_type_desc = "应届生（无实习经验）"
        focus_point = "基础技能掌握、学习潜力、课程项目经验"
    elif student_type == "has_intern":
        student_type_desc = "有实习经验的应届生"
        focus_point = "实习项目成果、岗位技能匹配度、职场适应能力"
    else:
        student_type_desc = "有工作经验的求职者"
        focus_point = "工作经验匹配度、项目落地能力、跨团队协作能力"

    # 参考岗位画像的JSON格式提示词，严格结构化输出
    prompt = f"""
    请你作为资深IT就业指导师，基于以下学生简历数据，生成该学生的**就业能力标准化画像**，
    严格按照以下维度输出JSON格式（仅输出JSON，无多余文字、换行、空格）：

    维度及输出要求：
    1. 专业技能：该学生掌握的核心技术栈、编程语言、框架、工具，用列表形式
    2. 证书：该学生拥有的证书，有则列具体名称（列表），无则标注"无"
    3. 创新能力：该学生的创新能力表现，无则标注"无"
    4. 学习能力：该学生的学习能力表现，无则标注"无"
    5. 抗压能力：该学生的抗压能力表现，无则标注"无"
    6. 沟通能力：该学生的沟通能力表现，无则标注"无"
    7. 实习能力：该学生的实习/工作经验能力表现，无则标注"无"

    学生类型：{student_type_desc}
    重点分析：{focus_point}
    简历数据：
    - 姓名：{resume.name}
    - 学历：{resume.education}
    - 专业：{resume.major}
    - 求职意向：{resume.desiredJob}
    - 核心技能：{resume.coreSkill}
    - 证书：{resume.certificate}
    - 技能熟练度：{resume.skillLevel}
    - 技术栈详情：{resume.stackDetail}
    - 创新能力：{resume.innovation}
    - 学习能力：{resume.learning}
    - 抗压能力：{resume.pressureResistance}
    - 沟通能力：{resume.communication}
    - 实习项目：{resume.internshipProject}
    - 实习时长：{resume.internshipDuration}
    - 项目成果：{resume.projectAchievement}
    """

    # 参考岗位画像的调用逻辑（带重试、异常处理）
    def _call_llm():
        response = Generation.call(
            model=os.getenv("LLM_MODEL", "qwen-plus"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.05,  # 低随机性，和岗位画像一致
            max_tokens=1500,
            timeout=60
        )
        if response.status_code == 200 and response.output and response.output.text:
            # 清洗JSON字符串（参考岗位画像的处理）
            json_str = response.output.text.strip().replace("\n", "").replace(" ", "")
            # 移除可能的markdown标记
            json_str = re.sub(r"^```json|```$", "", json_str)
            return json.loads(json_str)
        else:
            raise Exception(f"通义千问返回空结果，状态码：{response.status_code}")

    try:
        llm_result = _call_llm()
    except Exception as e:
        print(f"⚠️ 第一次调用失败：{str(e)[:60]}，重试中...")
        time.sleep(3)  # 重试间隔，和岗位画像一致
        try:
            llm_result = _call_llm()
        except Exception as e2:
            print(f"❌ 第二次调用失败：{str(e2)[:60]}，使用默认画像")
            # 生成默认画像（参考岗位画像的default逻辑）
            llm_result = {
                "专业技能": resume.coreSkill.split(",") if resume.coreSkill else [],
                "证书": resume.certificate.split(",") if resume.certificate else ["无"],
                "创新能力": resume.innovation or "无",
                "学习能力": resume.learning or "无",
                "抗压能力": resume.pressureResistance or "无",
                "沟通能力": resume.communication or "无",
                "实习能力": f"实习时长：{resume.internshipDuration}，项目：{resume.internshipProject[:50]}" if resume.internshipProject else "无"
            }

    # 计算评分（参考岗位画像的generate_experience_requirement）
    completeness_score, competitiveness_score = generate_score(resume, llm_result, student_type)

    # 构造StudentPortrait对象
    return StudentPortrait(
        professional_skills=llm_result["专业技能"],
        certificates=llm_result["证书"],
        innovation=llm_result["创新能力"],
        learning_ability=llm_result["学习能力"],
        pressure_resistance=llm_result["抗压能力"],
        communication=llm_result["沟通能力"],
        internship_ability=llm_result["实习能力"],
        completeness_score=completeness_score,
        competitiveness_score=competitiveness_score
    )


def save_portrait_to_file(resume: ResumeData, portrait: StudentPortrait):
    """
    将学生画像保存为文件（支持JSON和Excel两种格式）
    - JSON：单文件，便于查看完整信息
    - Excel：汇总所有学生画像，便于批量查看
    """
    # 1. 构造完整的画像数据
    portrait_data = {
        "基本信息": {
            "姓名": resume.name,
            "学历": resume.education,
            "专业": resume.major,
            "求职意向": resume.desiredJob,
            "学生类型": classify_student_type(resume)
        },
        "就业能力画像": portrait.dict(),
        "原始简历数据": resume.dict(),
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # 2. 保存单个学生画像为JSON文件（按姓名+时间命名，避免重复）
    file_name = f"{resume.name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    file_path = os.path.join(PORTRAIT_SAVE_DIR, file_name)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(portrait_data, f, ensure_ascii=False, indent=4)
    print(f"✅ 单个学生画像已保存：{file_path}")

    # 3. 追加保存到汇总Excel文件（便于批量查看）
    excel_file = os.path.join(PORTRAIT_SAVE_DIR, "学生就业能力画像汇总.xlsx")
    # 整理Excel行数据
    excel_row = {
        "姓名": resume.name,
        "学历": resume.education,
        "专业": resume.major,
        "求职意向": resume.desiredJob,
        "学生类型": classify_student_type(resume),
        "专业技能": str(portrait.professional_skills),
        "证书": str(portrait.certificates),
        "创新能力": portrait.innovation,
        "学习能力": portrait.learning_ability,
        "抗压能力": portrait.pressure_resistance,
        "沟通能力": portrait.communication,
        "实习能力": portrait.internship_ability,
        "完整度评分": portrait.completeness_score,
        "竞争力评分": portrait.competitiveness_score,
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # 追加到Excel
    if os.path.exists(excel_file):
        df = pd.read_excel(excel_file)
        df = pd.concat([df, pd.DataFrame([excel_row])], ignore_index=True)
    else:
        df = pd.DataFrame([excel_row])
    df.to_excel(excel_file, index=False, encoding="utf-8")
    print(f"✅ 已追加到汇总Excel：{excel_file}")

    return file_path, excel_file


# 核心处理函数（去掉数据库，仅保留生成+保存文件）
def process_resume_data(resume: ResumeData) -> ResumeResponse:
    """核心流程：清洗数据 → 调用通义千问 → 保存为文件 → 返回结果"""
    # 1. 数据清洗（参考岗位画像的merge_job_details中的清洗逻辑）
    clean_core_skill = resume.coreSkill.strip().replace('，', ',') if resume.coreSkill else ""
    clean_name = resume.name.strip() if resume.name else ""
    resume.coreSkill = clean_core_skill
    resume.name = clean_name

    try:
        # 2. 调用通义千问生成画像
        portrait = call_dashscope_generate_portrait(resume)

        # 3. 保存画像到文件（替换原数据库保存逻辑）
        json_file, excel_file = save_portrait_to_file(resume, portrait)

        # 4. 返回结果
        return ResumeResponse(
            status="success",
            message=f"已成功处理 {clean_name} 的简历数据，生成就业能力画像并保存文件",
            data={
                "resume_basic": resume.dict(),
                "student_portrait": portrait.dict(),
                "file_paths": {
                    "单个画像JSON": json_file,
                    "汇总Excel": excel_file
                },
                "tips": "完整度评分越高表示简历信息越全面，竞争力评分越高表示匹配求职意向度越高"
            }
        )
    except Exception as e:
        return ResumeResponse(
            status="error",
            message=f"处理简历数据失败：{str(e)}",
            data={}
        )