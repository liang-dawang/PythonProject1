import pandas as pd
import re

# ===================== 1. 核心配置（集中管理，易维护） =====================
# 1.1 岗位类型映射
JOB_TYPE_MAP = {
    "C/C++": "开发类",
    "Java": "开发类",
    "前端开发": "开发类",
    "测试工程师": "测试类",
    "软件测试": "测试类",
    "硬件测试": "测试类",
    "实施工程师": "实施支持类",
    "技术支持工程师": "实施支持类",
    "科研人员": "顶层类",
    "项目经理/主管": "顶层类"
}

# 1.2 各岗位类型薪资阈值（用于薪资打分）
SALARY_SCORE_MAP = {
    "开发类": {"高级": (15000, 10), "中级": (8000, 6), "初级": (4000, 3)},
    "测试类": {"高级": (12000, 10), "中级": (7000, 6), "初级": (3500, 3)},
    "实施支持类": {"高级": (10000, 10), "中级": (6000, 6), "初级": (3000, 3)},
    "顶层类": {"高级": (20000, 10), "中级": (15000, 6), "初级": (10000, 3)}
}

# 1.3 年限打分规则
YEAR_SCORE_MAP = {
    (3, float('inf')): 10,  # ≥3年得10分
    (1, 3): 6,  # 1-3年得6分
    (0, 1): 3,  # 0-1年/实习得3分
    (0, 0): 0  # 无年限得0分
}

# 1.4 关键词打分规则
KEYWORD_SCORE_MAP = {
    "开发类": {
        "高级关键词": ["架构设计", "分布式", "微服务", "高并发", "JVM调优", "主导开发"],
        "中级关键词": ["系统设计", "性能优化", "spring框架", "独立开发", "协议栈"],
        "初级关键词": ["基础编码", "javase", "html", "css", "使用框架"]
    },
    "测试类": {
        "高级关键词": ["性能测试", "全链路测试", "测试策略", "自动化框架开发"],
        "中级关键词": ["自动化测试", "接口测试", "脚本编写", "性能分析"],
        "初级关键词": ["手工测试", "用例设计", "功能测试", "万用表"]
    },
    "实施支持类": {
        "高级关键词": ["系统集成设计", "跨部门方案设计", "大规模部署"],
        "中级关键词": ["独立实施", "客户培训", "云平台部署", "问题排查"],
        "初级关键词": ["基础部署", "调试", "office", "arcgis"]
    },
    "顶层类": {
        "高级关键词": ["团队管理", "技术架构决策", "项目全流程把控"],
        "中级关键词": ["模块负责人", "技术方案评审"],
        "初级关键词": ["协助管理", "执行方案"]
    }
}

# 1.5 维度权重配置
WEIGHT_CONFIG = {"年限分": 0.4, "薪资分": 0.4, "关键词分": 0.2}

# 1.6 总分定级规则
TOTAL_SCORE_LEVEL = {(8, float('inf')): "高级", (4, 8): "中级", (0, 4): "初级"}

# 1.7 中文数字转阿拉伯数字映射
CN_NUM_MAP = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


# ===================== 2. 工具函数（数据提取） =====================
def extract_work_years(skills_text):
    """提取开发年限（兼容中文/阿拉伯数字）"""
    text = str(skills_text).lower().replace(" ", "")
    work_years = 0

    # 匹配中文数字+年
    cn_year_pattern = re.compile(r'([一二两三四五六七八九十]+)年')
    cn_year_matches = cn_year_pattern.findall(text)
    if cn_year_matches:
        cn_year = cn_year_matches[0]
        work_years = CN_NUM_MAP.get(cn_year, 0)

    # 匹配阿拉伯数字+年（优先级更高）
    num_year_pattern = re.compile(r'(\d+)年')
    num_year_matches = num_year_pattern.findall(text)
    if num_year_matches:
        work_years = int(num_year_matches[0])

    # 处理年限区间（如1-3年取中间值）
    range_pattern = re.compile(r'(\d+)-(\d+)年')
    range_matches = range_pattern.findall(text)
    if range_matches:
        start = int(range_matches[0][0])
        end = int(range_matches[0][1])
        work_years = (start + end) / 2

    # 匹配实习/应届生
    if work_years == 0 and any(kw in text for kw in ["实习", "应届", "入门", "0-1年"]):
        work_years = 0.5

    return work_years


def extract_salary_median(salary_text):
    """精准提取薪资中位数（适配3k-4k、10k-12k*13等格式）"""
    text = str(salary_text).lower().strip()

    # 1. 去掉年终奖及后面的内容（如*13、*17）
    text_before_bonus = text.split("*")[0]

    # 2. 处理带-的薪资区间
    if '-' in text_before_bonus:
        parts = text_before_bonus.split('-')
        if len(parts) >= 2:  # 确保拆分出首尾
            start_str = parts[0].strip()
            end_str = parts[1].strip()

            # 转换为数字（去掉k，转为整数）
            def k_to_num(s):
                num_part = re.sub(r'[^0-9]', '', s)
                return int(num_part) * 1000 if num_part else 0

            start = k_to_num(start_str)
            end = k_to_num(end_str)
            return (start + end) / 2 if start and end else 0
    # 3. 处理单个薪资值
    else:
        num_part = re.sub(r'[^0-9]', '', text_before_bonus)
        return int(num_part) * 1000 if num_part else 0


# ===================== 3. 打分函数（核心） =====================
def calculate_year_score(work_years):
    """计算年限分"""
    for (min_year, max_year), score in YEAR_SCORE_MAP.items():
        if min_year <= work_years < max_year:
            return score
    return 0


def calculate_salary_score(salary_median, job_type):
    """计算薪资分（按岗位类型阈值）"""
    salary_config = SALARY_SCORE_MAP.get(job_type, SALARY_SCORE_MAP["开发类"])

    if salary_median >= salary_config["高级"][0]:
        return salary_config["高级"][1]
    elif salary_config["中级"][0] <= salary_median < salary_config["高级"][0]:
        return salary_config["中级"][1]
    elif salary_config["初级"][0] <= salary_median < salary_config["中级"][0]:
        return salary_config["初级"][1]
    else:
        return 0


def calculate_keyword_score(skills_text, job_type):
    """计算关键词分"""
    text = str(skills_text).lower()
    keyword_config = KEYWORD_SCORE_MAP.get(job_type, KEYWORD_SCORE_MAP["开发类"])

    # 优先级：高级 > 中级 > 初级
    if any(kw.lower() in text for kw in keyword_config["高级关键词"]):
        return 10
    elif any(kw.lower() in text for kw in keyword_config["中级关键词"]):
        return 6
    elif any(kw.lower() in text for kw in keyword_config["初级关键词"]):
        return 3
    else:
        return 0


# ===================== 4. 核心分级函数（加权评分+双向修正） =====================
def classify_job_level(row):
    job_name = row["岗位名称"]
    skills_text = str(row["岗位详情"])
    salary_text = row.get("最终薪资", "")  # 注意：这里列名是"最终薪资"，需和Excel列名一致

    # 特殊处理：顶层类岗位直接定顶级
    if job_name in ["科研人员", "项目经理/主管"]:
        return {
            "岗位类型": "顶层类",
            "提取年限": extract_work_years(skills_text),
            "薪资中位数": extract_salary_median(salary_text),
            "年限分": 10,
            "薪资分": 10,
            "关键词分": 10,
            "总分": 10.0,
            "岗位级别": "顶级"
        }

    # 1. 基础数据提取
    job_type = JOB_TYPE_MAP.get(job_name, "开发类")
    work_years = extract_work_years(skills_text)
    salary_median = extract_salary_median(salary_text)

    # 2. 各维度打分
    year_score = calculate_year_score(work_years)
    salary_score = calculate_salary_score(salary_median, job_type)
    keyword_score = calculate_keyword_score(skills_text, job_type)

    # 3. 加权计算总分
    total_score = (year_score * WEIGHT_CONFIG["年限分"] +
                   salary_score * WEIGHT_CONFIG["薪资分"] +
                   keyword_score * WEIGHT_CONFIG["关键词分"])
    total_score = round(total_score, 2)  # 保留2位小数

    # 4. 按总分定级
    final_level = "初级"
    for (min_score, max_score), level in TOTAL_SCORE_LEVEL.items():
        if min_score <= total_score < max_score:
            final_level = level
            break

    # 5. 双向修正（贴合企业实际）
    salary_threshold = SALARY_SCORE_MAP[job_type]
    # 规则1：高级但薪资未达阈值 → 降级为中级
    if final_level == "高级" and salary_median < salary_threshold["高级"][0]:
        final_level = "中级"
    # 规则2：中级但薪资远超高级阈值 → 升级为高级
    elif final_level == "中级" and salary_median >= salary_threshold["高级"][0]:
        final_level = "高级"

    # 返回所有中间结果（方便核对）
    return {
        "岗位类型": job_type,
        "提取年限": work_years,
        "薪资中位数": salary_median,
        "年限分": year_score,
        "薪资分": salary_score,
        "关键词分": keyword_score,
        "总分": total_score,
        "岗位级别": final_level
    }


# ===================== 5. 主执行流程 =====================
if __name__ == "__main__":
    # 读取Excel数据（请确保路径和列名正确）
    excel_path = r"E:\pycharm\PythonProject1\计算机岗位_最终版.xlsx"
    df = pd.read_excel(excel_path)

    # 批量分级
    result_list = []
    for idx, row in df.iterrows():
        try:
            level_result = classify_job_level(row)
            row_dict = row.to_dict()
            row_dict.update(level_result)
            result_list.append(row_dict)
        except Exception as e:
            print(f"处理第{idx + 1}行数据出错：{e}")
            continue

    # 导出结果
    result_df = pd.DataFrame(result_list)
    result_df.to_excel("岗位分级结果_加权评分制_最终版.xlsx", index=False)

    # 打印核心结果核对
    print("✅ 加权评分制分级完成！")
    print("=" * 120)
    print(result_df[["岗位名称", "岗位类型", "提取年限", "薪资中位数",
                     "年限分", "薪资分", "关键词分", "总分", "岗位级别"]].to_string(index=False))