from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html

app = FastAPI()

# 自定义 Swagger UI 文档，使用国内 CDN
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        # 使用 BootCDN 提供的 Swagger UI 资源
        swagger_js_url="https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.1.3/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.1.3/swagger-ui.css",
    )

# 你的接口定义
@app.get("/")
def read_root():
    return {"Hello": "FastAPI"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

@app.get("/hello")
async def gethello():
    return {"msg":"老铁666"}


# 标记核心岗位后的文件路径（比如桌面）
INPUT_FILE = r"E:\pycharm\PythonProject1\标记核心岗位后的数据.xlsx"
# 清洗后保存路径
OUTPUT_FILE = r"E:\pycharm\PythonProject1\清洗薪资后的数据.xlsx"