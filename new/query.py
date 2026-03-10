from neo4j import GraphDatabase

# ---------------------- 配置（和你之前一样） ----------------------
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"  # 改成你自己的


class CareerQuery:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    # 1. 查询某个岗位的【完整垂直晋升路线】
    def get_promotion_path(self, job_name):
        print("\n" + "="*50)
        print(f"📊 【{job_name}】垂直晋升路线")
        print("="*50)

        with self.driver.session() as session:
            result = session.run("""
                MATCH p = (start:Job {name: $name, level:'初级'})-[:PROMOTE_TO*]->(end)
                RETURN nodes(p) AS path
            """, name=job_name)

            for record in result:
                path = record["path"]
                line = " → ".join([f"{n['name']}({n['level']})" for n in path])
                print(line)

    # 2. 查询某个岗位能【横向换到哪些岗位】
    def get_transfer_paths(self, job_name):
        print("\n" + "="*50)
        print(f"🔁 【{job_name}】可横向换岗路线")
        print("="*50)

        with self.driver.session() as session:
            result = session.run("""
                MATCH (a:Job {name: $name})-[r:CAN_TRANSFER_TO]->(b)
                RETURN DISTINCT b.name AS to_job, b.level AS to_level
                ORDER BY to_job
            """, name=job_name)

            for record in result:
                print(f"→ {record['to_job']}({record['to_level']})")

    # 3. 查询某个岗位【最终能晋升到什么管理/顶级岗】
    def get_final_promotion(self, job_name):
        print("\n" + "="*50)
        print(f"🚀 【{job_name}】最终跨岗晋升路线")
        print("="*50)

        with self.driver.session() as session:
            result = session.run("""
                MATCH p = (a:Job {name: $name})-[:PROMOTE_TO*]->(top)
                WHERE top.name IN ["项目经理/主管", "科研人员"]
                RETURN nodes(p) AS path
            """, name=job_name)

            for record in result:
                path = record["path"]
                line = " → ".join([f"{n['name']}({n['level']})" for n in path])
                print(line)

    # 4. 一次性查全部：晋升 + 换岗 + 最终路线
    def full_query(self, job_name):
        self.get_promotion_path(job_name)
        self.get_transfer_paths(job_name)
        self.get_final_promotion(job_name)


# ---------------------- 运行示例 ----------------------
if __name__ == "__main__":
    q = CareerQuery()

    # 你想查哪个岗位，直接改这里！
    target_job = "Java"

    # 查询全部
    q.full_query(target_job)

    q.close()