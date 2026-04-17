from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from ..dependencies import get_current_user
from ..services.hdfs_client import list_path, upload_file

router = APIRouter(prefix="/train/files", tags=["files"])


@router.get("/list")
def list_directory(path: Optional[str] = "/user", current_user=Depends(get_current_user)):
    items = list_path(path)
    return items


@router.post("/upload")
async def upload_file_endpoint(
        file: UploadFile = File(...),
        overwrite: bool = False,  # 新增查询参数
        current_user=Depends(get_current_user)
):
    content = await file.read()
    try:
        hdfs_path = upload_file(file.filename, content, overwrite=False)
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
    return {"path": hdfs_path}


@router.get("/preview")
async def preview_file(
    path: str,
    rows: int = 100,
    current_user=Depends(get_current_user)
):
    from ..services.hdfs_client import client, create_spark_session, cleanup_spark_session
    from ..config import HDFS_RPC
    import base64
    import pandas as pd
    import io

    # 检查文件是否存在（使用 HDFS 客户端）
    if not client.status(path, strict=False):
        raise HTTPException(404, "文件不存在")

    # 构造完整的 HDFS 路径供 Spark 使用
    full_path = f"{HDFS_RPC}{path}"
    ext = path.split('.')[-1].lower()

    # 图片文件：使用 Spark 读取二进制文件并转为 Base64
    if ext in ['jpg', 'jpeg', 'png', 'bmp', 'gif']:
        sc, spark = create_spark_session()
        try:
            # 读取二进制文件
            binary_rdd = sc.binaryFiles(full_path)
            # 获取第一个文件的内容（路径匹配）
            file_data = binary_rdd.collect()
            if not file_data:
                raise HTTPException(404, "图片文件内容为空")
            img_bytes = file_data[0][1]  # 元组 (path, bytes)
            img_base64 = base64.b64encode(img_bytes).decode()
            return {"type": "image", "data": img_base64, "format": ext}
        finally:
            cleanup_spark_session(sc, spark)

    # CSV / TXT 使用 Spark 读取文本
    if ext in ['csv', 'txt']:
        sc, spark = create_spark_session()
        try:
            df = spark.read.text(full_path).limit(rows)
            lines = df.rdd.map(lambda r: r[0]).collect()
            if not lines:
                return {"columns": [], "rows": []}
            # 检测分隔符
            delimiter = None
            for sep in [',', '\t', ';', ' ']:
                if sep in lines[0]:
                    delimiter = sep
                    break
            if delimiter and len(lines) > 1:
                columns = lines[0].split(delimiter)
                data_rows = [line.split(delimiter) for line in lines[1:rows]]
                return {"columns": columns, "rows": data_rows}
            else:
                return {"columns": ["content"], "rows": [[line] for line in lines]}
        finally:
            cleanup_spark_session(sc, spark)

    # Excel 使用 Pandas 读取（通过 client.read 但可能仍失败，建议转换 CSV）
    elif ext in ['xls', 'xlsx']:
        # 尝试使用 Spark 读取 Excel 不直接支持，这里改用 client.read 并捕获异常
        try:
            with client.read(path) as reader:
                content = reader.read()
            df = pd.read_excel(io.BytesIO(content), nrows=rows)
            columns = df.columns.tolist()
            rows_data = df.values.tolist()
            return {"columns": columns, "rows": rows_data}
        except Exception as e:
            raise HTTPException(500, f"读取 Excel 失败: {str(e)}")

    raise HTTPException(400, f"不支持预览的文件类型: {ext}")



