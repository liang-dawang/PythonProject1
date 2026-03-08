import pandas as pd
import re

# ---------------------- 配置项（修改这里适配你的文件） ----------------------
INPUT_FILE = r"E:\pycharm\PythonProject1\工作簿1.xlsx"  # 你的新建文件路径
OUTPUT_FILE = "E:\\pycharm\\PythonProject1\\清洗后薪资文件.xlsx"  # 输出路径
SALARY_COLUMN = "薪资范围"  # 你的薪资列名称（如果是其他名称，比如“薪资”，改这里）


# ---------------------- 核心清洗函数 ----------------------
def clean_salary(salary_str):
    """
    专门处理：6000-8000元·14薪 → 6k-8k*14
             7000-10000元 → 7k-10k（12薪不显示*12）
    """
    if pd.isna(salary_str) or not isinstance(salary_str, str):
        return ""

    # 1. 提取发薪月数（匹配·14薪、·13薪等）
    month_match = re.search(r"·(\d{2})薪", salary_str)
    pay_months = int(month_match.group(1)) if month_match else 12

    # 2. 提取薪资数字（匹配6000-8000、7000-12000等）
    num_match = re.search(r"(\d+)-(\d+)元", salary_str)
    if not num_match:
        return ""

    # 3. 转换为k单位
    low_k = int(int(num_match.group(1)) / 1000)
    high_k = int(int(num_match.group(2)) / 1000)

    # 4. 拼接最终格式（>12薪才显示*N）
    if pay_months > 12:
        return f"{low_k}k-{high_k}k*{pay_months}"
    else:
        return f"{low_k}k-{high_k}k"


# ---------------------- 执行清洗 ----------------------
if __name__ == "__main__":
    # 读取新建文件
    try:
        df = pd.read_excel(INPUT_FILE)
        print(f"✅ 成功读取文件：{INPUT_FILE}")
        print(f"📊 数据共 {len(df)} 行")
    except Exception as e:
        print(f"❌ 读取失败：{str(e)}")
        exit()

    # 检查薪资列是否存在
    if SALARY_COLUMN not in df.columns:
        print(f"❌ 错误：表格中无「{SALARY_COLUMN}」列")
        print(f"👉 表格所有列名：{df.columns.tolist()}")
        exit()

    # 执行清洗
    print("\n🔧 开始清洗薪资...")
    df["清洗后薪资"] = df[SALARY_COLUMN].apply(clean_salary)

    # 保存文件
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"\n✅ 清洗完成！文件保存至：{OUTPUT_FILE}")

    # 打印示例验证
    print("\n📋 清洗结果示例：")
    sample = df[[SALARY_COLUMN, "清洗后薪资"]].head(10)
    print(sample.to_string(index=False))