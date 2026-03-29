from neo4j import GraphDatabase

# ---------------------- 配置 ----------------------
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"  # 替换为你的密码


class CareerQuery:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    # 核心工具方法：计算两个完整岗位名之间的缺失技能
    def _get_missing_skills(self, from_fullname, to_fullname):
        """
        计算从源岗位（完整名）到目标岗位（完整名）的技能缺口
        :param from_fullname: 源岗位完整名（如Java初级）
        :param to_fullname: 目标岗位完整名（如Java中级）
        :return: 缺失技能列表、技能缺口数量
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (from:Job {name: $from_fullname})
                MATCH (to:Job {name: $to_fullname})
                UNWIND to.skills AS to_skill
                WITH from, to, collect(DISTINCT to_skill) AS to_skills
                UNWIND from.skills AS from_skill
                WITH from, to, to_skills, collect(DISTINCT from_skill) AS from_skills
                WITH from, to, [skill IN to_skills WHERE NOT skill IN from_skills] AS missing_skills
                RETURN missing_skills, size(missing_skills) AS missing_count
            """, from_fullname=from_fullname, to_fullname=to_fullname)

            record = result.single()
            if record:
                missing_skills = record["missing_skills"] if record["missing_skills"] else ["无"]
                missing_count = record["missing_count"]
                return missing_skills, missing_count
            return ["无"], 0

    # 1. 查询单个完整岗位名的垂直晋升路线（如Java初级→Java中级）
    def get_promotion_path(self, job_fullname):
        print("\n" + "=" * 80)
        print(f"📊 【{job_fullname}】垂直晋升路线（含需学习技能）")
        print("=" * 80)

        # 验证岗位是否存在
        with self.driver.session() as session:
            exist_res = session.run("""
                MATCH (j:Job {name: $fullname}) RETURN count(j) AS cnt
            """, fullname=job_fullname)
            if exist_res.single()["cnt"] == 0:
                print(f"❌ 未查询到【{job_fullname}】这个岗位，请检查输入是否正确")
                return

        # 查询该岗位的所有直接/间接垂直晋升路径
        with self.driver.session() as session:
            result = session.run("""
                MATCH p = (start:Job {name: $fullname})-[:PROMOTE_TO*]->(end:Job)
                WHERE ALL(rel IN relationships(p) WHERE rel.type = '垂直晋升')
                WITH p, length(p) AS path_length
                ORDER BY path_length DESC
                LIMIT 1  // 只取最长的完整晋升路径
                RETURN nodes(p) AS path
            """, fullname=job_fullname)

            records = list(result)
            if not records:
                print(f"❌ 【{job_fullname}】暂无垂直晋升路线")
                return

            # 输出晋升步骤
            path_nodes = records[0]["path"]
            for i in range(len(path_nodes) - 1):
                from_node = path_nodes[i]["name"]
                to_node = path_nodes[i + 1]["name"]

                # 获取技能缺口
                missing_skills, missing_count = self._get_missing_skills(from_node, to_node)
                skills_str = "、".join(missing_skills)

                # 打印步骤
                print(f"\n✅ 晋升步骤：{from_node} → {to_node}")
                print(f"   📚 需补充技能（共{missing_count}项）：{skills_str}")

    # 2. 查询单个完整岗位名的横向换岗路线（如Java初级→C/C++初级）
    def get_transfer_paths(self, job_fullname):
        print("\n" + "=" * 80)
        print(f"🔁 【{job_fullname}】可横向换岗路线（含需学习技能）")
        print("=" * 80)

        # 验证岗位是否存在
        with self.driver.session() as session:
            exist_res = session.run("""
                MATCH (j:Job {name: $fullname}) RETURN count(j) AS cnt
            """, fullname=job_fullname)
            if exist_res.single()["cnt"] == 0:
                print(f"❌ 未查询到【{job_fullname}】这个岗位，请检查输入是否正确")
                return

        # 查询该岗位的所有横向换岗关系
        with self.driver.session() as session:
            result = session.run("""
                MATCH (a:Job {name: $fullname})-[r:CAN_TRANSFER_TO]->(b:Job)
                RETURN b.name AS to_fullname ORDER BY to_fullname
            """, fullname=job_fullname)

            records = list(result)
            if not records:
                print(f"❌ 【{job_fullname}】暂无横向换岗路线")
                return

            # 输出换岗路径
            for record in records:
                to_fullname = record["to_fullname"]
                missing_skills, missing_count = self._get_missing_skills(job_fullname, to_fullname)
                skills_str = "、".join(missing_skills)

                print(f"\n🔹 换岗路径：{job_fullname} → {to_fullname}")
                print(f"   📚 需补充技能（共{missing_count}项）：{skills_str}")

    # 3. 查询单个完整岗位名的最终跨岗晋升路线（修复Result消费问题）
    def get_final_promotion(self, job_fullname):
        print("\n" + "=" * 80)
        print(f"🚀 【{job_fullname}】最终跨岗晋升路线（含需学习技能）")
        print("=" * 80)

        # 验证岗位是否存在
        with self.driver.session() as session:
            exist_res = session.run("""
                MATCH (j:Job {name: $fullname}) RETURN count(j) AS cnt
            """, fullname=job_fullname)
            if exist_res.single()["cnt"] == 0:
                print(f"❌ 未查询到【{job_fullname}】这个岗位，请检查输入是否正确")
                return

        # 修复核心：将Result结果立即转为列表，避免重复消费
        records = []
        with self.driver.session() as session:
            result = session.run("""
                MATCH p = (start:Job {name: $fullname})-[:PROMOTE_TO*]->(top:Job)
                WHERE top.name CONTAINS "项目经理/主管" OR top.name CONTAINS "科研人员"
                WITH p, length(p) AS path_length
                ORDER BY path_length DESC
                RETURN DISTINCT nodes(p) AS path
            """, fullname=job_fullname)
            # 立即消费结果并转为列表，存储在本地变量
            records = list(result)

        if not records:
            print(f"❌ 【{job_fullname}】暂无最终跨岗晋升路线")
            return

        # 去重并输出路径
        seen_paths = set()
        for record in records:
            path_nodes = record["path"]
            path_key = "→".join([n["name"] for n in path_nodes])

            if path_key in seen_paths:
                continue
            seen_paths.add(path_key)

            # 输出完整路径
            full_path = " → ".join([n["name"] for n in path_nodes])
            print(f"\n🎯 完整晋升路径：{full_path}")

            # 计算起点到终点的总技能缺口
            start_name = path_nodes[0]["name"]
            end_name = path_nodes[-1]["name"]
            missing_skills, missing_count = self._get_missing_skills(start_name, end_name)
            skills_str = "、".join(missing_skills)

            print(f"   📚 从起点到终点需补充技能（共{missing_count}项）：{skills_str}")

    # 4. 一次性查询全部路线（晋升+换岗+最终晋升）
    def full_query(self, job_fullname):
        self.get_promotion_path(job_fullname)
        self.get_transfer_paths(job_fullname)
        self.get_final_promotion(job_fullname)


# ---------------------- 运行示例 ----------------------
if __name__ == "__main__":
    q = CareerQuery()

    # 输入完整岗位名（如Java初级、Java中级、C/C++高级、项目经理/主管顶级）
    target_job_fullname = "Java初级"  # 核心修改：输入完整岗位名

    # 查询该完整岗位名的所有路线
    q.full_query(target_job_fullname)

    q.close()
    print("\n" + "=" * 80)
    print("✅ 所有查询完成！")