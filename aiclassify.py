import pandas as pd
import dashscope
from dotenv import load_dotenv
import os

# ===================== 1. 环境配置与基础函数 =====================
# 加载通义千问API密钥
load_dotenv("new/mima.env")
dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')

if not dashscope.api_key:
    raise ValueError("请在mima.env文件中配置DASHSCOPE_API_KEY！格式：DASHSCOPE_API_KEY=你的密钥")


def load_job_base_data(file_path=None):
    """
    加载岗位基础数据（优先读取外部文件，无文件则用内置配置）
    :param file_path: 外部Excel/CSV文件路径（列名：岗位大类、专业技能、证书要求、创新能力、学习能力、抗压能力、沟通能力、实习能力）
    :return: 岗位基础要求字典
    """
    # 内置原始10大类+4个细分岗位的配置（和你提供的完全一致）
    builtin_data = {
        # ========== 原始10大类 ==========
        "前端开发类": {
            "专业技能": "HTML5、CSS3、JavaScript（ES6+）、Vue.js、React、TypeScript、Webpack/Vite、RESTful API、Git、响应式开发、跨浏览器兼容性处理、单元测试（Jest/Vitest）",
            "证书要求": "计算机二级（编程方向）、软考Web前端开发师、阿里云ACA前端开发认证",
            "创新能力": "无明确要求",
            "学习能力": "能快速掌握新框架、工具链及前端领域前沿技术（如微前端、低代码平台、WebAssembly等）",
            "抗压能力": "能适应迭代快、需求变更频繁的敏捷开发节奏，保障关键节点交付质量",
            "沟通能力": "具备与产品经理、UI设计师、后端工程师高效协作的能力，能清晰表达技术方案与问题",
            "实习能力": "有参与真实项目开发经验者优先，熟悉团队协作流程（如Git分支管理、Code Review）"
        },
        "后端开发类": {
            "专业技能": "Java、Python、Spring Boot、MyBatis/MyBatis-Plus、MySQL、Redis、Linux、RESTful API设计、微服务架构（Spring Cloud/Dubbo）、消息队列（RabbitMQ/Kafka）、Git、Docker基础",
            "证书要求": "计算机二级（Java/Python方向）、软考软件设计师、华为HCIA云计算认证",
            "创新能力": "能结合业务场景提出技术优化方案，参与新技术预研与落地验证（如新框架选型、性能调优策略）",
            "学习能力": "持续跟踪主流后端技术演进，快速掌握新框架/中间件并应用于实际项目，具备文档阅读与源码分析能力",
            "抗压能力": "能高效应对高并发、紧急线上故障等压力场景，保障系统稳定性与交付时效，具备7×24小时应急响应意识",
            "沟通能力": "能清晰向产品、前端、测试等角色阐述技术方案与边界，准确理解需求并反馈技术可行性，参与跨团队协作评审",
            "实习能力": "具备企业级项目实习经历（如参与电商/政务/金融类后端模块开发），熟悉DevOps流程与团队协作规范"
        },
        "软件测试类": {
            "专业技能": "功能测试、接口测试、自动化测试（Selenium/Pytest/Appium）、性能测试（JMeter/LoadRunner）、数据库SQL操作、Linux基础命令、HTTP/HTTPS协议、缺陷管理工具（Jira/Bugzilla）、测试用例设计方法、API测试工具（Postman/SoapUI）、持续集成（Jenkins/GitLab CI）、Python/Java基础编程",
            "证书要求": "计算机二级、软考软件测试工程师、ISTQB国际软件测试认证",
            "创新能力": "无明确要求",
            "学习能力": "能快速掌握新业务领域、测试工具及技术框架，持续跟进测试行业发展趋势",
            "抗压能力": "能适应项目周期紧张、多版本并行、上线前高强度回归测试等压力场景",
            "沟通能力": "具备跨职能协作能力，能清晰向开发、产品反馈缺陷，准确理解需求并参与评审",
            "实习能力": "有至少3个月以上软件测试相关实习经历，熟悉测试全流程（需求分析→用例设计→执行→报告）"
        },
        "硬件开发与测试类": {
            "专业技能": "电路设计、PCB Layout、嵌入式C/C++开发、硬件调试与故障定位、示波器/逻辑分析仪等仪器操作、EMC/EMI基础设计与整改、FPGA基础应用（Verilog/VHDL）、电源完整性与信号完整性基础、硬件测试用例编写与执行、自动化测试脚本（Python/LabVIEW）",
            "证书要求": "电子工程师职业资格证、软考嵌入式系统设计师、电子设备装调工（中级）",
            "创新能力": "能结合新器件、新方案优化传统硬件架构，提出可落地的测试方法改进或模块级创新设计",
            "学习能力": "能快速掌握新型MCU/SoC平台、高速接口协议（如USB PD、PCIe、MIPI）、新兴测试标准（如AEC-Q200、IEC 61000）",
            "抗压能力": "能在项目周期紧、多任务并行、硬件问题复现难等高压场景下保持系统性排查与稳定输出",
            "沟通能力": "能清晰向软件/结构/质量团队同步硬件约束、测试风险及协同接口需求，准确理解跨部门技术反馈",
            "实习能力": "无明确要求"
        },
        "技术支持与运维类": {
            "专业技能": "Linux系统管理、网络协议与排错（TCP/IP、DNS、DHCP、HTTP/HTTPS）、Shell/Python脚本编写、服务器部署与维护（Web/Nginx/Apache、DB/MySQL/PostgreSQL）、监控工具使用（Zabbix/Prometheus/Grafana）、日志分析（ELK/Splunk）、容器基础（Docker）、故障诊断与应急响应、AD域与权限管理、备份与容灾方案实施、云平台基础操作（阿里云/AWS/Azure常用服务）",
            "证书要求": "计算机三级（网络技术）、软考网络工程师、红帽RHCE Linux运维认证",
            "创新能力": "无明确要求",
            "学习能力": "持续跟踪新技术（如云原生、自动化运维DevOps工具链），快速掌握新平台、新工具及厂商文档能力",
            "抗压能力": "能承受7×24小时轮值、突发故障高压响应（如核心业务中断、大规模告警），具备快速决策与闭环处理能力",
            "沟通能力": "需清晰向非技术人员解释技术问题，跨部门协同（开发、测试、安全、业务方），撰写规范运维报告与知识库文档",
            "实习能力": "具备6个月以上IT基础设施或运维相关实习经历，独立完成过服务器部署、监控配置、故障复盘等实操任务"
        },
        "实施交付类": {
            "专业技能": "系统部署与配置、需求分析与转化、用户培训与赋能、UAT支持与问题闭环、SQL基础查询与数据验证、主流ERP/CRM系统操作（如SAP/Oracle/用友/金蝶）、Windows/Linux基础运维、接口对接与联调测试、文档编写（实施手册/操作指南/验收报告）、变更管理与版本控制、客户现场问题诊断与快速响应、项目进度跟踪与交付物管理",
            "证书要求": "计算机二级、软考信息系统项目管理师、PMP入门级",
            "创新能力": "无明确要求",
            "学习能力": "能快速掌握新业务场景、新系统模块及行业解决方案，适应多产品线交付要求",
            "抗压能力": "能适应阶段性高强度出差、多项目并行及客户紧急需求响应，保障关键节点交付",
            "沟通能力": "具备跨角色（客户业务人员、IT部门、内部研发/产品团队）高效沟通能力，可清晰传递技术逻辑与业务价值",
            "实习能力": "具备不少于3个月的信息化项目现场实施实习经历，能独立完成模块级交付任务"
        },
        "项目管理类": {
            "专业技能": "项目计划制定、进度管控、成本预算与控制、风险管理、干系人管理、需求分析与确认、WBS分解、变更管理、质量管理、范围管理、资源协调、敏捷项目管理（Scrum/Kanban）",
            "证书要求": "PMP、软考信息系统项目管理师、PRINCE2认证",
            "创新能力": "无明确要求",
            "学习能力": "无明确要求",
            "抗压能力": "无明确要求",
            "沟通能力": "无明确要求",
            "实习能力": "无明确要求"
        },
        "产品相关类": {
            "专业技能": "需求分析、用户调研、原型设计（Axure/Figma）、PRD撰写、竞品分析、数据驱动决策、敏捷开发协作、产品生命周期管理、交互设计基础、SQL基础查询、A/B测试设计、跨部门协同推进",
            "证书要求": "计算机二级、软考系统分析师、NPDP产品经理认证、Axure官方认证",
            "创新能力": "能独立提出差异化产品方案，持续优化用户体验与业务模式，具备从0到1的产品构思与验证能力",
            "学习能力": "快速掌握新技术、新平台及行业动态，主动学习用户行为分析工具（如神策、GrowingIO）与AI产品化知识",
            "抗压能力": "能在多线程任务、紧急上线压力及需求频繁变更环境下保持高效输出与质量稳定",
            "沟通能力": "精准传达产品逻辑与目标，有效协调研发、设计、运营、市场等多方角色，推动共识落地",
            "实习能力": "具备至少1段6个月以上互联网/科技公司产品岗实习经历，能独立完成模块级需求闭环（调研→设计→跟进→复盘）"
        },
        "科研与算法类": {
            "专业技能": "Python、TensorFlow/PyTorch、机器学习算法、深度学习模型设计、数据预处理与特征工程、统计学与概率论、优化理论、自然语言处理（NLP）或计算机视觉（CV）方向专长、SQL/数据库基础、算法复杂度分析、A/B测试与实验设计、大模型微调与评估（加分项）",
            "证书要求": "软考人工智能工程师、计算机技术与软件专业技术资格（高级）、专利/论文（加分项）",
            "创新能力": "需具备独立提出新方法、改进现有模型或解决前沿问题的能力，能基于文献调研开展原创性实验设计",
            "学习能力": "需持续跟踪顶会（NeurIPS/ICML/CVPR/ACL等）进展，快速掌握新兴框架（如JAX、vLLM）、工具链及跨领域知识（如生物信息、金融建模）",
            "抗压能力": "能应对算法迭代周期短、实验失败率高、项目 deadline 紧、多任务并行等压力，保持稳定输出与复盘优化习惯",
            "沟通能力": "能向非技术背景 stakeholders 清晰阐释模型原理、局限性与业务价值；具备跨团队协作经验（如与产品、工程、数据团队对齐需求与交付标准）",
            "实习能力": "有头部科技企业/重点实验室6个月以上算法实习经历者优先，需体现完整项目闭环（问题定义→建模→验证→落地支持）"
        },
        "全栈开发类": {
            "专业技能": "JavaScript、TypeScript、React、Vue、Node.js、Spring Boot、MySQL、Redis、Docker、Kubernetes、RESTful API设计、Git版本控制",
            "证书要求": "软考系统架构设计师、阿里云ACP全栈开发认证、华为HCIP云原生认证",
            "创新能力": "能结合业务场景提出技术优化与架构演进方案，主动探索新技术在项目中的落地路径",
            "学习能力": "持续跟踪前端框架演进、后端微服务实践及云原生技术发展，具备快速掌握新工具链和平台的能力",
            "抗压能力": "能在多任务并行、需求频繁变更及线上故障应急等高压场景下保持高质量交付",
            "沟通能力": "熟练与产品经理、UI/UX设计师、测试及运维团队跨职能协作，清晰表达技术方案与权衡逻辑",
            "实习能力": "无明确要求"
        },
        # ========== 仅新增4个细分岗位（不破坏10大类） ==========
        "Java后端开发（后端开发类细分）": {
            "专业技能": "Java、Spring Boot、Spring Cloud、MyBatis、MySQL、达梦数据库、Linux、微服务架构",
            "证书要求": "计算机二级（Java方向）、软考软件设计师、华为HCIA-Java认证、阿里云ACA Java开发认证",
            "创新能力": "无明确要求",
            "学习能力": "无明确要求",
            "抗压能力": "无明确要求",
            "沟通能力": "无明确要求",
            "实习能力": "无明确要求"
        },
        "Python后端开发（后端开发类细分）": {
            "专业技能": "Python、Django、Flask、FastAPI、Redis、MongoDB、Linux、Pandas",
            "证书要求": "计算机二级（Python方向）、软考软件设计师、阿里云ACA Python认证、数据分析工程师认证",
            "创新能力": "无明确要求",
            "学习能力": "无明确要求",
            "抗压能力": "无明确要求",
            "沟通能力": "无明确要求",
            "实习能力": "无明确要求"
        },
        "系统运维/云运维（技术支持与运维类细分）": {
            "专业技能": "Linux系统操作、服务器部署、数据库维护、网络配置、监控工具、云服务器运维、故障排查",
            "证书要求": "计算机三级（网络技术）、软考网络工程师、红帽RHCE Linux运维认证、阿里云ACP云运维认证",
            "创新能力": "无明确要求",
            "学习能力": "无明确要求",
            "抗压能力": "无明确要求",
            "沟通能力": "无明确要求",
            "实习能力": "无明确要求"
        },
        "技术支持/售后实施（技术支持与运维类细分）": {
            "专业技能": "现场调试、问题定位、客户培训、文档编写、产品讲解、售后对接、验收支持",
            "证书要求": "计算机二级、软考信息处理技术员、客户服务管理师（初级）、售后技术支持认证",
            "创新能力": "无明确要求",
            "学习能力": "无明确要求",
            "抗压能力": "无明确要求",
            "沟通能力": "无明确要求",
            "实习能力": "无明确要求"
        }
    }

    # 优先读取外部文件
    if file_path and os.path.exists(file_path):
        try:
            if file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8')
            else:
                raise ValueError("仅支持xlsx/csv格式！")

            job_data = {}
            for _, row in df.iterrows():
                job_name = row["岗位大类"].strip()
                job_data[job_name] = {
                    "专业技能": row.get("专业技能", "").strip(),
                    "证书要求": row.get("证书要求", "").strip(),
                    "创新能力": row.get("创新能力", "").strip(),
                    "学习能力": row.get("学习能力", "").strip(),
                    "抗压能力": row.get("抗压能力", "").strip(),
                    "沟通能力": row.get("沟通能力", "").strip(),
                    "实习能力": row.get("实习能力", "").strip()
                }
            print(f"✅ 成功读取外部文件：{file_path}（共{len(job_data)}个岗位）")
            return job_data
        except Exception as e:
            print(f"⚠️ 读取外部文件失败，使用内置配置：{str(e)[:50]}")
            return builtin_data
    else:
        print("✅ 使用内置岗位配置（10大类+4个细分）")
        return builtin_data


def generate_standard_portrait(job_name, job_info):
    """调用大模型生成标准化岗位画像（格式统一）"""
    prompt = f"""
你是资深的计算机行业人力资源专家，请严格按照以下要求生成{job_name}的岗位画像：
1. 输出格式固定（每个维度独占一行，无额外内容）：
{job_name}岗位画像
专业技能：{job_info['专业技能']}
证书要求：{job_info['证书要求']}
创新能力：{job_info['创新能力']}
学习能力：{job_info['学习能力']}
抗压能力：{job_info['抗压能力']}
沟通能力：{job_info['沟通能力']}
实习能力：{job_info['实习能力']}
2. 内容完全复用提供的信息，不增删、不修改任何表述
3. 仅输出画像内容，无其他多余文字
"""
    try:
        # 调用通义千问生成
        response = dashscope.Generation.call(
            model="qwen-plus",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,  # 0温度保证输出完全一致
            max_tokens=1000,
            timeout=60
        )
        if response.status_code == 200:
            return response.output.text.strip()
        else:
            raise Exception(f"模型返回错误：{response.status_code}")
    except Exception as e:
        # 兜底：直接拼接，不依赖大模型
        print(f"⚠️ {job_name}画像生成失败，使用兜底方案：{str(e)[:30]}")
        return f"""
{job_name}岗位画像
专业技能：{job_info['专业技能']}
证书要求：{job_info['证书要求']}
创新能力：{job_info['创新能力']}
学习能力：{job_info['学习能力']}
抗压能力：{job_info['抗压能力']}
沟通能力：{job_info['沟通能力']}
实习能力：{job_info['实习能力']}
""".strip()


# ===================== 2. 主程序 =====================
if __name__ == "__main__":
    # 配置：如需读取外部文件，替换为你的文件路径（如 "岗位要求.xlsx"）
    JOB_DATA_FILE ="分类完数据.xlsx"  # 改为你的文件路径即可读取外部文件，保持None则用内置配置

    # 1. 加载岗位数据
    job_data = load_job_base_data(JOB_DATA_FILE)

    # 2. 拆分原始10大类和细分岗位（便于区分）
    original_10_cats = [
        "前端开发类", "后端开发类", "软件测试类", "硬件开发与测试类",
        "技术支持与运维类", "实施交付类", "项目管理类", "产品相关类",
        "科研与算法类", "全栈开发类"
    ]
    sub_cats = [
        "Java后端开发（后端开发类细分）", "Python后端开发（后端开发类细分）",
        "系统运维/云运维（技术支持与运维类细分）", "技术支持/售后实施（技术支持与运维类细分）"
    ]

    # 3. 批量生成画像
    all_portraits = []  # 所有画像文本（用于TXT）
    structured_data = []  # 结构化数据（用于Excel）

    # 先生成原始10大类画像
    print("\n========== 生成原始10大类画像 ==========")
    for cat in original_10_cats:
        print(f"正在生成：{cat}")
        portrait = generate_standard_portrait(cat, job_data[cat])
        all_portraits.append(portrait)

        # 解析为结构化数据
        lines = portrait.split('\n')
        data_item = {"岗位分类层级": "原始10大类", "岗位名称": cat}
        for line in lines[1:]:
            if "：" in line:
                key, value = line.split("：", 1)
                data_item[key] = value.strip()
        structured_data.append(data_item)

    # 再生成4个细分岗位画像
    print("\n========== 生成细分岗位画像 ==========")
    for sub_cat in sub_cats:
        print(f"正在生成：{sub_cat}")
        portrait = generate_standard_portrait(sub_cat, job_data[sub_cat])
        all_portraits.append(f"\n【细分岗位】{portrait}")

        # 解析为结构化数据
        lines = portrait.split('\n')
        data_item = {"岗位分类层级": "细分岗位", "岗位名称": sub_cat}
        for line in lines[1:]:
            if "：" in line:
                key, value = line.split("：", 1)
                data_item[key] = value.strip()
        structured_data.append(data_item)

    # 4. 保存结果
    # 4.1 保存TXT（便于阅读）
    with open("岗位画像_10大类+细分版.txt", "w", encoding="utf-8") as f:
        f.write('\n\n' + '=' * 60 + '\n\n'.join(all_portraits))

    # 4.2 保存Excel（便于后续分析）
    df_portrait = pd.DataFrame(structured_data)
    df_portrait = df_portrait[["岗位分类层级", "岗位名称", "专业技能", "证书要求",
                               "创新能力", "学习能力", "抗压能力", "沟通能力", "实习能力"]]
    df_portrait.to_excel("岗位画像_10大类+细分版.xlsx", index=False)

    # 5. 输出完成信息
    print("\n🎉 所有岗位画像生成完成！")
    print(f"📄 TXT文件路径：{os.path.abspath('岗位画像_10大类+细分版.txt')}")
    print(f"📊 Excel文件路径：{os.path.abspath('岗位画像_10大类+细分版.xlsx')}")
    print(f"\n📈 生成统计：")
    print(f"   - 原始10大类：{len(original_10_cats)}个")
    print(f"   - 细分岗位：{len(sub_cats)}个")
    print(f"   - 总计：{len(original_10_cats) + len(sub_cats)}个岗位画像")