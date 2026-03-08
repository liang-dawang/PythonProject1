import pandas as pd
import dashscope
from dotenv import load_dotenv
import os
import time

# ===================== 基础配置 =====================
load_dotenv("new/mima.env")
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

INPUT_FILE = "分类完数据.xlsx"  # 原始数据
PORTRAIT_ONLY_FILE = "岗位画像_单独保存版.xlsx"  # 仅保存画像的独立文件
FULL_DATA_FILE = "原始数据+画像完整版.xlsx"  # 原始数据+画像的文件

# 画像生成提示词（强化维度要求，确保全覆盖）
PORTRAIT_PROMPT = """
你是资深的IT岗位分析专家，请根据以下岗位名称和整合后的岗位详情，生成该岗位的标准化专属画像。
画像必须包含以下维度，每个维度单独用小标题+内容形式呈现：
1. 专业技能：核心技术栈、编程语言、框架、工具、算法等该岗位必备的专业能力要求
2. 证书要求：明确该岗位是否需要专业证书（如软考、云厂商认证、职业资格证等），无则标注"无"
3. 创新能力：该岗位对创新能力的具体要求（如方案优化、技术攻关、新思路提出等）
4. 学习能力：该岗位对学习能力的具体要求（如新技术学习、技术迭代跟进、自主学习等）
5. 抗压能力：该岗位对抗压能力的具体要求（如紧急需求处理、加班、高并发场景、问题排查等）
6. 沟通能力：该岗位对沟通能力的具体要求（如跨团队协作、需求对接、技术评审、客户沟通等）
7. 实习能力/经验要求：明确该岗位的实习经历、工作经验、项目经验要求，无则标注"无"
8. 学历要求：明确该岗位的学历、专业背景要求（如本科/专科、计算机相关专业等）
9. 岗位职责核心：概括3-5条该岗位的核心工作职责

要求：
1. 每个维度内容简洁明了（30-80字），贴合该岗位的真实招聘要求
2. 严格按维度分点呈现，格式清晰，小标题加粗（用**包裹）
3. 内容完全基于岗位详情，不编造、不夸大、不通用化
4. 语言专业、精准，符合IT岗位招聘的行业规范

岗位信息：
岗位名称：{job_name}
整合后的岗位详情：{job_detail}
"""


# ===================== 核心函数 =====================
def generate_portrait(job_name, job_detail):
    """生成单个岗位的专属画像"""
    if pd.isna(job_detail) or job_detail.strip() == "":
        return f"{job_name}：无有效岗位详情，无法生成画像"

    prompt = PORTRAIT_PROMPT.format(job_name=job_name, job_detail=job_detail)
    try:
        response = dashscope.Generation.call(
            model="qwen-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  # 保证画像稳定、精准
            max_tokens=1200,
            timeout=30
        )
        if response.status_code == 200 and response.output:
            return response.output.text.strip()
        time.sleep(1)
    except Exception as e:
        print(f"⚠️ {job_name} 画像生成失败（重试）：{str(e)[:60]}")
        time.sleep(3)
    return f"{job_name} 画像生成失败：{str(e)[:50]}" if 'e' in locals() else f"{job_name} 画像生成失败"


def integrate_job_detail(df, job_name_col="岗位名称", detail_col="岗位详情"):
    """
    整合同一岗位名称的所有详情内容（去重+合并）
    返回：包含岗位名称+整合后详情的DataFrame
    """
    # 按岗位名称分组，合并所有详情并去重
    integrated_data = []
    for job_name, group in df.groupby(job_name_col):
        # 提取所有非空详情
        details = group[detail_col].dropna().astype(str).tolist()
        # 去重（保留唯一内容）
        unique_details = list(set(details))
        # 整合为一个文本
        integrated_detail = "\n\n".join(
            [f"详情片段{i + 1}：{d}" for i, d in enumerate(unique_details)]) if unique_details else ""
        integrated_data.append({
            "岗位名称": job_name,
            "整合后的岗位详情": integrated_detail if integrated_detail else "无岗位详情"
        })

    return pd.DataFrame(integrated_data)


# ===================== 主流程 =====================
if __name__ == "__main__":
    # 1. 读取原始数据（自动过滤空值）
    print("📥 开始读取并处理数据...")
    df = pd.read_excel(INPUT_FILE).dropna(subset=["岗位名称"])  # 过滤无岗位名称的行
    print(f"✅ 原始数据读取完成，有效数据量：{len(df)}")

    # 2. 整合同一岗位的所有详情内容
    print("\n🔧 开始整合同一岗位的详情内容...")
    df_integrated = integrate_job_detail(df)
    unique_jobs = len(df_integrated)
    print(f"✅ 详情整合完成，唯一岗位数：{unique_jobs}")
    print(f"📋 岗位列表：{list(df_integrated['岗位名称'])}")

    # 3. 批量生成岗位画像
    print(f"\n🚀 开始生成 {unique_jobs} 个岗位的专属画像...")
    portraits = []
    for idx, row in df_integrated.iterrows():
        job_name = row["岗位名称"]
        job_detail = row["整合后的岗位详情"]

        print(f"   [{idx + 1}/{unique_jobs}] 生成中：{job_name}")
        portrait = generate_portrait(job_name, job_detail)
        portraits.append(portrait)

    # 4. 给整合后的数据添加画像列（单独保存的核心数据）
    df_integrated["岗位专属画像"] = portraits

    # 5. 单独保存画像文件（仅含岗位名称+整合详情+画像）
    df_integrated.to_excel(PORTRAIT_ONLY_FILE, index=False)
    print(f"\n💾 画像单独保存完成：{os.path.abspath(PORTRAIT_ONLY_FILE)}")

    # 6. 合并回原始数据（所有行都匹配对应画像）
    df_full = pd.merge(df, df_integrated[["岗位名称", "岗位专属画像"]], on="岗位名称", how="left")
    df_full.to_excel(FULL_DATA_FILE, index=False)
    print(f"💾 原始数据+画像保存完成：{os.path.abspath(FULL_DATA_FILE)}")

    # 7. 生成统计报告
    print("\n📊 画像生成统计报告：")
    success_count = sum(1 for p in portraits if "生成失败" not in p)
    fail_count = unique_jobs - success_count
    print(f"   成功生成：{success_count} / {unique_jobs} 个岗位画像")
    print(f"   生成失败：{fail_count} / {unique_jobs} 个岗位画像")
    print(f"   成功率：{success_count / unique_jobs * 100:.1f}%")

    # 8. 打印失败的岗位（方便排查）
    if fail_count > 0:
        print("\n❌ 生成失败的岗位：")
        failed_jobs = [df_integrated.iloc[i]["岗位名称"] for i, p in enumerate(portraits) if "生成失败" in p]
        for job in failed_jobs:
            print(f"   - {job}")

    print("\n🎉 所有操作完成！核心文件：")
    print(f"   1. 单独画像文件：{PORTRAIT_ONLY_FILE}")
    print(f"   2. 原始数据+画像：{FULL_DATA_FILE}")