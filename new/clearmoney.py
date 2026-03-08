import pandas as pd
import re
import os


def clean_salary_final(salary_str):
    """
    最终薪资格式：
    - 发薪月数>12 → 6k-7k*13
    - 发薪月数=12 → 6k-7k
    核心修复：匹配任意位数数字区间，解决7000-12000这类6位数字匹配失败问题
    """
    # 初始化核心变量
    clean_salary = ""
    pay_months = 12

    # 空值/非字符串处理
    if pd.isna(salary_str) or not isinstance(salary_str, str):
        return ""

    # 保留原始文本（用于精准匹配）
    original_text = salary_str.strip()
    # 预处理文本（统一格式）
    raw_text = original_text.lower().replace(" ", "").replace("·", "").replace("元", "").replace("月", "")

    # 1. 提取发薪月数（12/13/14薪等）
    pay_month_match = re.search(r"(\d{2})薪", raw_text)
    if pay_month_match:
        pay_months = int(pay_month_match.group(1))
        pay_months = 12 if (pay_months < 12 or pay_months > 24) else pay_months

    # 2. 处理日薪/时薪（折算为月薪）
    daily_match = re.search(r"(\d+(?:\.?\d+)?)-(\d+(?:\.?\d+)?)元?/天", original_text.lower())
    hourly_match = re.search(r"(\d+(?:\.?\d+)?)-(\d+(?:\.?\d+)?)元?/小时", original_text.lower())
    if daily_match:
        low_k = int(float(daily_match.group(1)) * 22 / 1000)
        high_k = int(float(daily_match.group(2)) * 22 / 1000)
        clean_salary = f"{low_k}k-{high_k}k" if (low_k > 0 and high_k > 0) else ""
    elif hourly_match:
        low_k = int(float(hourly_match.group(1)) * 8 * 22 / 1000)
        high_k = int(float(hourly_match.group(2)) * 8 * 22 / 1000)
        clean_salary = f"{low_k}k-{high_k}k" if (low_k > 0 and high_k > 0) else ""

    # 3. 处理月薪（核心修复：匹配任意位数数字区间）
    if not clean_salary:
        # 匹配万单位：1.2-2万 → 12k-20k
        wan_match = re.search(r"(\d+(?:\.?\d+)?)-(\d+(?:\.?\d+)?)万", raw_text)
        if wan_match:
            low_k = int(float(wan_match.group(1)) * 10)
            high_k = int(float(wan_match.group(2)) * 10)
            clean_salary = f"{low_k}k-{high_k}k"
        else:
            # 匹配千/k单位：3千-4千 → 3k-4k
            unit_match = re.search(r"(\d+(?:\.?\d+)?)(千|k)-(\d+(?:\.?\d+)?)(千|k)", raw_text)
            if unit_match:
                low_k = int(float(unit_match.group(1)))
                high_k = int(float(unit_match.group(3)))
                clean_salary = f"{low_k}k-{high_k}k"
            else:
                # 核心修复：匹配任意位数数字区间（解决7000-12000匹配失败）
                num_match = re.search(r"(\d+)-(\d+)", raw_text)  # 匹配任意位数数字区间
                if num_match:
                    low = int(num_match.group(1))
                    high = int(num_match.group(2))
                    # 确保是合理薪资范围（避免匹配到非薪资数字）
                    if 1000 <= low <= 100000 and 1000 <= high <= 100000:
                        low_k = int(low / 1000)
                        high_k = int(high / 1000)
                        clean_salary = f"{low_k}k-{high_k}k" if (low_k > 0 and high_k > 0) else ""

    # 4. 处理年薪（折算为月薪）
    if not clean_salary:
        year_match = re.search(r"(\d+(?:\.?\d+)?)万-(\d+(?:\.?\d+)?)万", original_text)
        if year_match:
            low_k = int(float(year_match.group(1)) * 10000 / 12 / 1000)
            high_k = int(float(year_match.group(2)) * 10000 / 12 / 1000)
            clean_salary = f"{low_k}k-{high_k}k" if (low_k > 0 and high_k > 0) else ""

    # 5. 最终格式拼接（>12薪才显示*N）
    if clean_salary:
        final_salary = f"{clean_salary}*{pay_months}" if pay_months > 12 else clean_salary
    else:
        final_salary = ""

    return final_salary


# ---------------------- 岗位分类（精准匹配） ----------------------
def classify_job(job_name):
    if pd.isna(job_name):
        return "其他"
    job_name = str(job_name).strip()
    # 开发岗
    if any(kw in job_name for kw in ["C/C++", "Java", "前端开发"]):
        return "开发岗"
    # 测试岗
    elif any(kw in job_name for kw in ["测试工程师", "软件测试", "硬件测试"]):
        return "测试岗"
    # 技术支持/实施岗
    elif any(kw in job_name for kw in ["实施工程师", "技术支持工程师"]):
        return "技术支持/实施岗"
    # 算法类
    elif "科研人员" in job_name:
        return "算法类"
    elif "项目经理/主管" in job_name:
        return "管理类"
    else:
        return "其他"


# ---------------------- 主流程 ----------------------
if __name__ == "__main__":
    # 配置路径（根据你的文件修改）
    INPUT_FILE = r"E:\\pycharm\\PythonProject1\\新数据.xls"
    OUTPUT_FILE = "E:\\pycharm\\PythonProject1\\计算机岗位_最终版.xlsx"

    # 读取数据
    try:
        df = pd.read_excel(INPUT_FILE)
        print(f"✅ 读取数据成功，共 {len(df)} 行")
    except Exception as e:
        print(f"❌ 读取失败：{str(e)}")
        exit()

    # 清洗薪资（核心）
    df["最终薪资"] = df["薪资范围"].apply(clean_salary_final)
    # 岗位分类
    df["岗位分类"] = df["岗位名称"].apply(classify_job)
    # 筛选计算机岗位
    target_jobs = ["C/C++", "Java", "测试工程师", "前端开发", "软件测试",
                   "硬件测试", "实施工程师", "技术支持工程师", "科研人员","项目经理/主管"]
    df_computer = df[df["岗位名称"].str.contains("|".join([re.escape(kw) for kw in target_jobs]), na=False)]

    # 保存+验证
    df_computer.to_excel(OUTPUT_FILE, index=False)
    # 统计空值
    empty_salary = df_computer["最终薪资"].isna().sum() + (df_computer["最终薪资"] == "").sum()
    print(f"\n✅ 处理完成！文件保存至：{OUTPUT_FILE}")
    print(f"📊 计算机岗位共 {len(df_computer)} 行，空薪资：{empty_salary} 行")
    # 打印示例
    print("\n📋 结果示例：")
    print(df_computer[["岗位名称", "薪资范围", "最终薪资", "岗位分类"]].head(10).to_string(index=False))