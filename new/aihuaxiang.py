import pandas as pd
import json
import time
import os
import re
from dotenv import load_dotenv
import dashscope
from dashscope import Generation

# ---------------------- 1. 配置项 ----------------------
INPUT_FILE = r"E:\pycharm\PythonProject1\计算机岗位_最终版.xlsx"
OUTPUT_PORTFOLIO = r"E:\pycharm\PythonProject1\岗位画像单独文件.xlsx"
OUTPUT_MERGED = r"E:\pycharm\PythonProject1\原数据+画像整合文件.xlsx"

JOB_NAME_COL = "岗位名称"
JOB_DETAIL_COL = "岗位详情"
SALARY_COL = "最终薪资"

# 大模型配置
load_dotenv("mima.env")
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
if not dashscope.api_key:
    raise ValueError("❌ 未获取到DASHSCOPE_API_KEY，请检查mima.env文件")


# ---------------------- 2. 核心函数 ----------------------
def classify_job_type(job_name, job_detail):
    """
    自动识别岗位类型：实习岗/校招岗/社招岗
    返回："intern"（实习/校招）、"social"（社招）
    """
    text = f"{job_name} {job_detail}".lower()
    # 实习/校招关键词
    intern_keywords = ["实习", "实习生", "校招", "应届生", "毕业", "暑期实习", "应届", "毕业生"]
    # 社招关键词
    social_keywords = ["经验", "资深", "高级", "3年", "5年", "社招", "全职", "工作经验", "多年"]

    # 优先判断实习岗
    if any(kw in text for kw in intern_keywords):
        return "intern"
    # 再判断社招岗
    elif any(kw in text for kw in social_keywords):
        return "social"
    # 默认按校招处理（兼顾应届生）
    else:
        return "intern"


def merge_job_details(df):
    """按岗位名称分组，整合详情（去重+拼接），并标记岗位类型"""
    df[JOB_DETAIL_COL] = df[JOB_DETAIL_COL].fillna("无详细信息")
    job_detail_dict = {}
    job_type_dict = {}  # 记录每个岗位类别的类型

    # 第一步：先给每条数据打类型标签
    df["job_type"] = df.apply(lambda row: classify_job_type(row[JOB_NAME_COL], row[JOB_DETAIL_COL]), axis=1)

    # 第二步：按岗位名称分组
    grouped = df.groupby(JOB_NAME_COL)
    for job_name, group in grouped:
        # 整合详情
        detail_list = group[JOB_DETAIL_COL].tolist()
        unique_details = []
        seen = set()
        for detail in detail_list:
            if detail not in seen and detail != "无详细信息":
                seen.add(detail)
                unique_details.append(detail)
        merged_detail = "\n".join(unique_details[:10]) if unique_details else "无详细信息"
        job_detail_dict[job_name] = merged_detail

        # 确定岗位类别类型（多数派原则）
        job_types = group["job_type"].value_counts()
        main_type = job_types.index[0] if not job_types.empty else "intern"
        job_type_dict[job_name] = main_type

    print(f"✅ 完成岗位详情整合，共 {len(job_detail_dict)} 个岗位类别")
    print(
        f"📌 岗位类型分布：实习/校招岗 {list(job_type_dict.values()).count('intern')} 个，社招岗 {list(job_type_dict.values()).count('social')} 个")
    return job_detail_dict, job_type_dict


def generate_experience_requirement(job_type, job_name, merged_detail):
    """根据岗位类型生成对应的经验要求"""
    if job_type == "intern":
        # 实习/校招岗：基础技能+项目/短期实习
        base_requirements = {
            "开发类": "需掌握基础开发技能，有课程设计或1-3个月相关实习经验优先",
            "测试类": "需掌握基础测试方法，有测试相关课程/项目或1-3个月测试实习经验优先",
            "产品类": "需具备产品思维，有竞品分析/原型设计或1-3个月产品实习经验优先",
            "数据类": "需掌握数据分析/算法基础，有数据相关项目或1-3个月数据分析实习经验优先",
            "通用类": "有相关专业课程或项目经验优先，有短期实习经验更佳"
        }
        # 匹配岗位类型
        if any(kw in job_name for kw in ["开发", "Java", "前端", "Python", "后端", "移动端"]):
            return base_requirements["开发类"]
        elif "测试" in job_name:
            return base_requirements["测试类"]
        elif "产品" in job_name:
            return base_requirements["产品类"]
        elif any(kw in job_name for kw in ["数据", "算法", "分析"]):
            return base_requirements["数据类"]
        else:
            return base_requirements["通用类"]
    else:
        # 社招岗：合理的工作经验要求（从详情提取，无则生成默认）
        # 提取详情中的经验年限
        exp_pattern = r"(\d+)年以上?经验"
        match = re.search(exp_pattern, merged_detail)
        if match:
            years = match.group(1)
            # 避免年限过大（最多8年）
            if int(years) > 8:
                return f"需{years}年以上相关工作经验，有大型项目落地经验优先"
            else:
                return f"需{years}年以上相关工作经验，有对应领域项目经验优先"
        else:
            # 无明确年限，按岗位类型生成
            if any(kw in job_name for kw in ["开发", "Java", "前端"]):
                return "需3-5年相关开发经验，有微服务/高并发项目经验优先"
            elif "测试" in job_name:
                return "需2-4年相关测试经验，有自动化测试/性能测试经验优先"
            elif "产品" in job_name:
                return "需3-5年相关产品经验，有独立负责产品模块经验优先"
            else:
                return "需2-5年相关工作经验，有对应领域项目经验优先"


def generate_portfolio_for_job(job_name, merged_detail, job_type):
    """按岗位类型生成差异化画像"""
    # 构造提示词（区分实习/社招）
    if job_type == "intern":
        prompt_type = "校招/实习"
        exp_desc = "实习/项目经验要求（针对在校生/应届生）"
    else:
        prompt_type = "社招"
        exp_desc = "工作经验要求（针对社会招聘）"

    prompt = f"""
    请你作为资深IT HR，基于【同一岗位类别的所有详情】，生成该岗位的**通用{prompt_type}标准化画像**，
    严格按照以下维度输出JSON格式（仅输出JSON，无多余文字、换行、空格）：

    维度及输出要求：
    1. 专业技能：该岗位{prompt_type}必备的核心技术栈、编程语言、框架、工具，用列表形式
    2. 证书要求：该岗位{prompt_type}的证书要求，有则列具体名称（列表），无则标注"无"
    3. 创新能力：该岗位{prompt_type}对创新能力的具体要求，无则标注"无"
    4. 学习能力：该岗位{prompt_type}对学习能力的具体要求，无则标注"无"
    5. 抗压能力：该岗位{prompt_type}对抗压能力的具体要求，无则标注"无"
    6. 沟通能力：该岗位{prompt_type}对沟通能力的具体要求，无则标注"无"
    7. 经验要求：{exp_desc}，无则标注"无"

    岗位名称：{job_name}
    整合后的所有详情：{merged_detail[:1500]}
    """

    try:
        response = Generation.call(
            model="qwen-plus",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.05,
            max_tokens=1500,
            timeout=60
        )

        if response.status_code == 200 and response.output and response.output.text:
            json_str = response.output.text.strip().replace("\n", "").replace(" ", "")
            portfolio = json.loads(json_str)
            # 兜底：如果经验要求为空，生成合理默认值
            if not portfolio.get("经验要求") or portfolio["经验要求"] == "无":
                portfolio["经验要求"] = generate_experience_requirement(job_type, job_name, merged_detail)
            return portfolio
        else:
            raise Exception(f"SDK返回空结果，状态码：{response.status_code}")

    except Exception as e:
        print(f"⚠️ {job_name} 画像生成失败：{str(e)[:60]}")
        time.sleep(3)
        try:
            response = Generation.call(
                model="qwen-plus",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.05,
                timeout=60
            )
            if response.status_code == 200 and response.output.text:
                json_str = response.output.text.strip().replace("\n", "").replace(" ", "")
                portfolio = json.loads(json_str)
                if not portfolio.get("经验要求") or portfolio["经验要求"] == "无":
                    portfolio["经验要求"] = generate_experience_requirement(job_type, job_name, merged_detail)
                return portfolio
        except:
            pass
        # 生成默认画像（按岗位类型）
        default_exp = generate_experience_requirement(job_type, job_name, merged_detail)
        return {
            "专业技能": [], "证书要求": "无", "创新能力": "无",
            "学习能力": "无", "抗压能力": "无", "沟通能力": "无",
            "经验要求": default_exp
        }


# ---------------------- 3. 主流程 ----------------------
if __name__ == "__main__":
    try:
        df = pd.read_excel(INPUT_FILE)
        print(f"✅ 成功读取文件：{INPUT_FILE}")
        print(f"📊 原始数据共 {len(df)} 行")
    except Exception as e:
        print(f"❌ 读取文件失败：{str(e)}")
        exit()

    required_cols = [JOB_NAME_COL, JOB_DETAIL_COL, SALARY_COL]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ 缺失必要列：{missing_cols}")
        print(f"👉 表格所有列名：{df.columns.tolist()}")
        exit()

    # 步骤1：分组整合详情 + 识别岗位类型
    job_detail_dict, job_type_dict = merge_job_details(df)

    # 步骤2：生成岗位画像（按类型差异化）
    print("\n🔧 开始为各岗位类别生成差异化画像...")
    job_portfolio_dict = {}
    total_jobs = len(job_detail_dict)

    for idx, (job_name, merged_detail) in enumerate(job_detail_dict.items(), 1):
        job_type = job_type_dict[job_name]
        portfolio = generate_portfolio_for_job(job_name, merged_detail, job_type)
        job_portfolio_dict[job_name] = portfolio

        progress = (idx / total_jobs) * 100
        print(f"🔹 进度：{idx}/{total_jobs} ({progress:.1f}%) - 完成「{job_name}」({job_type}) 画像生成")
        time.sleep(2)

    # 步骤3：匹配回原数据
    portfolio_df = pd.DataFrame.from_dict(job_portfolio_dict, orient="index").reset_index()
    portfolio_df.rename(columns={"index": JOB_NAME_COL}, inplace=True)
    df_merged = pd.merge(df, portfolio_df, on=JOB_NAME_COL, how="left")

    # 步骤4：保存单独画像文件（补充岗位类型和典型薪资）
    portfolio_only_df = portfolio_df.copy()
    # 添加岗位类型
    portfolio_only_df["岗位类型"] = portfolio_only_df[JOB_NAME_COL].map(job_type_dict)
    # 补充典型薪资
    salary_summary = df.groupby(JOB_NAME_COL)[SALARY_COL].apply(
        lambda x: x.mode()[0] if not x.mode().empty else "").to_dict()
    portfolio_only_df["典型薪资"] = portfolio_only_df[JOB_NAME_COL].map(salary_summary)
    # 调整列顺序
    portfolio_only_df = portfolio_only_df[[
        JOB_NAME_COL, "岗位类型", "典型薪资", "专业技能", "证书要求",
        "创新能力", "学习能力", "抗压能力", "沟通能力", "经验要求"
    ]]
    portfolio_only_df.to_excel(OUTPUT_PORTFOLIO, index=False)
    print(f"\n✅ 按岗位分组的画像文件已保存：{OUTPUT_PORTFOLIO}")

    # 步骤5：保存整合文件
    df_merged.to_excel(OUTPUT_MERGED, index=False)
    print(f"✅ 原数据+画像整合文件已保存：{OUTPUT_MERGED}")

    # 步骤6：打印示例验证
    print("\n📋 差异化画像示例：")
    # 取实习岗和社招岗各一个示例
    intern_job = [j for j in job_type_dict if job_type_dict[j] == "intern"][0]
    social_job = [j for j in job_type_dict if job_type_dict[j] == "social"][0]

    print(f"\n【实习/校招岗 - {intern_job}】")
    intern_port = job_portfolio_dict[intern_job]
    print(f"典型薪资：{salary_summary.get(intern_job, '')}")
    print(f"经验要求：{intern_port['经验要求']}")
    print(f"专业技能：{intern_port['专业技能'][:5]}")  # 只显示前5个

    print(f"\n【社招岗 - {social_job}】")
    social_port = job_portfolio_dict[social_job]
    print(f"典型薪资：{salary_summary.get(social_job, '')}")
    print(f"经验要求：{social_port['经验要求']}")
    print(f"专业技能：{social_port['专业技能'][:5]}")