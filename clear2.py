import pandas as pd
import re
import numpy as np
import os

# ===================== 配置项（替换成你的实际路径/列名） =====================
# 标记核心岗位后的文件路径（比如桌面）
INPUT_FILE = r"E:\pycharm\PythonProject1\标记核心岗位后的数据.xlsx"
# 清洗后保存路径
OUTPUT_FILE = r"E:\pycharm\PythonProject1\清洗薪资，筛选完计算机的数据.xlsx"
SALARY_COLUMN = "薪资范围"  # 你的薪资列名
CORE_JOB_COLUMN = "核心岗位"  # 岗位名称所在列

# ===================== 定义计算机相关岗位关键词/完整岗位名 =====================
# 基于你提供的岗位列表，整理的计算机相关岗位（精准匹配）+ 核心关键词（模糊匹配）
COMPUTER_JOB_FULL = [
    "C/C++", "Java", "测试工程师", "产品专员/助理", "技术支持工程师",
    "科研人员", "前端开发", "软件测试", "实施工程师", "硬件测试",
    "项目经理/主管", "项目专员/助理", "质量管理/测试", "质检员"
]
# 补充关键词（用于模糊匹配，防止岗位名有细微差异，如“高级Java开发”）
COMPUTER_JOB_KEYWORDS = [
    "开发", "测试", "工程师", "技术", "前端", "Java", "C/C++",
    "项目", "质量", "实施", "软件", "硬件", "科研"
]

# ===================== 修正后的核心清洗函数（彻底处理“万”） =====================
def clean_salary_fix(salary_str):
    """
    彻底解决“万”的转换问题：
    - 1万 → 10000元
    - 1.5万 → 15000元
    - 1.2-2万 → 16000元（中位数）
    - 120-150元/天 → 2970元/月
    - 6000-8000元 → 7000元/月
    - 1.2-1.5万·17薪 → 13500元/月（月薪），229500元（年薪）
    """
    salary_str = str(salary_str).strip()
    # 处理空值/无效值
    if salary_str in ["nan", "面议", "无", "", "None"]:
        return np.nan, np.nan

    # 步骤1：提取带薪数（如17薪 → 17）
    salary_times = re.findall(r"(\d+)薪", salary_str)
    times = int(salary_times[0]) if salary_times else 12  # 默认12薪

    # 步骤2：彻底处理“万”（核心修正！）
    has_wan = "万" in salary_str
    salary_clean = salary_str.replace("万", "")

    # 步骤3：去除干扰字符（薪数、元、·、空格、/天等）
    salary_clean = re.sub(r"\·|\s|(\d+)薪|元|/天", "", salary_clean)

    # 步骤4：提取薪资数字（支持范围：6000-8000、1.2-2、1-1.5）
    nums = re.findall(r"\d+\.?\d*", salary_clean)
    if len(nums) < 1:
        return np.nan, np.nan

    # 步骤5：转换数字并处理范围（取中位数）
    nums = [float(num) for num in nums]
    salary_median = (nums[0] + nums[1]) / 2 if len(nums) >= 2 else nums[0]

    # 步骤6：如果含“万”，乘10000（核心修正！）
    if has_wan:
        salary_median = salary_median * 10000

    # 步骤7：处理日薪（单独逻辑，避免和月薪混淆）
    if "元/天" in salary_str:
        month_salary = salary_median * 22  # 日薪转月薪（22天）
    else:
        month_salary = salary_median  # 月薪直接用

    # 计算年薪
    year_salary = month_salary * times

    # 返回整数（避免小数）
    return int(month_salary), int(year_salary)

# ===================== 定义筛选计算机岗位的函数 =====================
def is_computer_job(job_name):
    """
    判断岗位是否为计算机相关：
    1. 先精准匹配完整岗位名
    2. 再模糊匹配关键词
    """
    job_name = str(job_name).strip()
    if job_name in ["nan", "", "None"]:
        return False
    # 精准匹配
    if job_name in COMPUTER_JOB_FULL:
        return True
    # 模糊匹配关键词
    for keyword in COMPUTER_JOB_KEYWORDS:
        if keyword in job_name:
            return True
    return False

# ===================== 读取数据并执行筛选+清洗 =====================
df = pd.read_excel(INPUT_FILE, engine="openpyxl")
print(f"✅ 读取数据成功，原始总行数：{len(df)}")

# 检查列名
if SALARY_COLUMN not in df.columns:
    print(f"❌ 错误：无'{SALARY_COLUMN}'列！当前列名：{df.columns.tolist()}")
    exit(1)
if CORE_JOB_COLUMN not in df.columns:
    print(f"❌ 错误：无'{CORE_JOB_COLUMN}'列！当前列名：{df.columns.tolist()}")
    exit(1)

# 第一步：筛选计算机相关岗位
df_computer = df[df[CORE_JOB_COLUMN].apply(is_computer_job)].copy()
print(f"✅ 筛选出计算机相关岗位数据，行数：{len(df_computer)}")

# 第二步：应用薪资清洗函数（仅处理筛选后的数据）
df_computer[["清洗后月薪（元/月）", "清洗后年薪（元）"]] = df_computer[SALARY_COLUMN].apply(
    lambda x: pd.Series(clean_salary_fix(x))
)

# 填充空值（用核心岗位平均薪资）
salary_mean = df_computer.groupby(CORE_JOB_COLUMN)["清洗后月薪（元/月）"].transform("mean")
df_computer["清洗后月薪（元/月）"] = df_computer["清洗后月薪（元/月）"].fillna(salary_mean).astype(int)
df_computer["清洗后年薪（元）"] = df_computer["清洗后年薪（元）"].fillna(df_computer["清洗后月薪（元/月）"] * 12).astype(int)

# ===================== 验证结果 =====================
print("\n=== 计算机岗位筛选结果 ===")
print(f"计算机相关岗位类型数：{df_computer[CORE_JOB_COLUMN].nunique()}")
print("计算机相关岗位列表：")
print(df_computer[CORE_JOB_COLUMN].unique())

print("\n=== 修正后清洗示例（重点验证“万”的转换）===")
# 筛选含“万”的薪资数据验证
wan_samples = df_computer[df_computer[SALARY_COLUMN].str.contains("万", na=False)][
    [CORE_JOB_COLUMN, SALARY_COLUMN, "清洗后月薪（元/月）"]].head(10)
print(wan_samples)

print(f"\n=== 整体清洗结果 ===")
print(f"有效月薪数据数：{df_computer['清洗后月薪（元/月）'].gt(0).sum()}")
print(f"计算机岗位平均月薪TOP5：")
top5 = df_computer.groupby(CORE_JOB_COLUMN)["清洗后月薪（元/月）"].mean().sort_values(ascending=False).head(5)
for job, sal in top5.items():
    print(f"  {job}：{int(sal)} 元/月")

# 保存筛选+清洗后的数据
df_computer.to_excel(OUTPUT_FILE, index=False, engine="openpyxl")
print(f"\n✅ 筛选+清洗后数据已保存：{OUTPUT_FILE}")