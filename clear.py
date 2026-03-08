import pandas as pd
import re
import numpy as np

# 1. 读取数据（关键修复：xls用xlrd引擎，xlsx用openpyxl）
# 如果你文件是.xls，用下面这行；如果是.xlsx，把engine改成"openpyxl"
try:
    # 优先尝试读取xls格式（engine=xlrd）
    df = pd.read_excel(r"C:\Users\33395\Downloads\a13基于AI的大学生职业规划智能体-JD采样数据.xls", engine="xlrd")
    print(f"成功读取.xls格式文件，原始数据总行数：{len(df)}")
except Exception as e:
    # 如果是xlsx格式，自动切换引擎
    df = pd.read_excel("数据.xlsx", engine="openpyxl")
    print(f"成功读取.xlsx格式文件，原始数据总行数：{len(df)}")

# 2. 定义你的51个核心岗位（基于你实际的透视表结果）
CORE_JOBS = [
    "APP推广", "BD经理", "C/C++", "Java", "测试工程师", "产品专员/助理",
    "储备干部", "储备经理人", "大客户代表", "档案管理", "电话客服", "电话销售",
    "法务专员/助理", "风电工程师", "管培生/储备干部", "广告销售", "技术支持工程师",
    "科研人员", "猎头顾问", "律师", "律师助理", "内容审核", "培训师", "前端开发",
    "日语翻译", "软件测试", "商务专员", "社区运营", "实施工程师", "售后客服",
    "统计员", "网络客服", "网络销售", "项目经理/主管", "项目招投标", "项目专员/助理",
    "销售工程师", "销售运营", "销售助理", "英语翻译", "硬件测试", "游戏推广",
    "游戏运营", "运营助理/专员", "招聘专员/助理", "知识产权/专利代理", "质检员",
    "质量管理/测试", "咨询顾问", "资料管理", "总助/CEO助理/董事长助理"
]


# 3. 优化核心岗位匹配函数（解决原代码中"工程师"拆分的bug）
def mark_core_job(row):
    """
    精准匹配核心岗位：
    1. 去除空白/无效字符
    2. 模糊匹配（包含关系）
    3. 优先匹配长名称（避免"Java"匹配到"JavaScript"这类无关岗位）
    """
    job_name = str(row["岗位名称"]).strip()
    # 过滤空白/无效岗位名称
    if job_name in ["", "nan", "空白", "总计"]:
        return "其他"

    # 按岗位名称长度排序（长名称优先匹配，避免误匹配）
    sorted_core_jobs = sorted(CORE_JOBS, key=lambda x: len(x), reverse=True)

    # 模糊匹配核心岗位
    for core_job in sorted_core_jobs:
        core_job_clean = core_job.strip()
        if core_job_clean in job_name or job_name in core_job_clean:
            return core_job_clean
    return "其他"


# 4. 标记核心岗位
df["核心岗位"] = df.apply(mark_core_job, axis=1)

# 5. 统计核心岗位分布（优化统计逻辑）
core_job_dist = df["核心岗位"].value_counts()
# 排除"其他"，只统计核心岗位
valid_core_jobs = core_job_dist[core_job_dist.index != "其他"]

print("\n=== 核心岗位分布（前51）===")
print(valid_core_jobs.head(51))
print(f"\n实际匹配到的核心岗位数量：{len(valid_core_jobs)}")
print(f"所有核心岗位的总记录数：{valid_core_jobs.sum()}")
print(f"'其他'类别的记录数：{core_job_dist.get('其他', 0)}")

# 可选：保存标记后的数据到新Excel（方便后续分析）
df.to_excel("标记核心岗位后的数据.xlsx", index=False)
print("\n✅ 标记后的数据已保存为：标记核心岗位后的数据.xlsx")