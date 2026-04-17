import gc
import io
import os
import sys
import time
import traceback
import uuid

import pandas as pd
from hdfs import InsecureClient
from py4j.protocol import Py4JJavaError

from ..config import HDFS_NAMENODE, HDFS_USER, HDFS_HOST, HDFS_FILE_PORT

# Spark
spark_home = r'C:\spark-300'
hadoop_home = r'C:\hadoop-273'
sys.path.insert(0, os.path.join(spark_home, 'python'))
os.environ['SPARK_HOME'] = spark_home
os.environ['HADOOP_HOME'] = hadoop_home


def initialize_hdfs_client():
    """Initialize HDFS client"""
    global client
    try:
        client = InsecureClient(f"{HDFS_NAMENODE}", user=HDFS_USER)
        # Test connection
        client.status("/")
        print("[HDFS] client initialized successfully")
        return client
    except Exception as e:
        print(f"[HDFS] client initialization failed: {e}")
        return None


# Initialize HDFS connection immediately after Spark initialization
print("Initialize HDFS ...")
client = initialize_hdfs_client()
if client is None:
    print("Warning: HDFS connection initialization failed, subsequent operations may be affected")


def hdfs_exists(hdfs_path: str) -> bool:
    """检查HDFS路径（文件或目录）是否存在"""
    try:
        # 使用hdfs客户端检查状态
        client.status(hdfs_path)
        return True
    except Exception as e:
        if "not found" in str(e).lower() or "does not exist" in str(e).lower():
            return False
        # 其他错误也认为不存在（但可打印日志）
        print(f"检查HDFS路径存在性时出错: {e}")
        return False


# ========== Spark Session ==========
def create_spark_session():
    """create new Spark Session"""
    from pyspark import SparkConf, SparkContext
    from pyspark.sql import SparkSession
    # master = os.getenv("SPARK_MASTER", "local[*]")  # 默认 local[*]，但会被 .env 覆盖
    conf = (SparkConf().setMaster("local[*]")
            .setAppName(f"ModelTraining_{uuid.uuid4().hex[:8]}")
            .set("spark.pyspark.python", sys.executable)
            .set("spark.pyspark.driver.python", sys.executable)
            # === 解决端口绑定问题的关键配置 ===
            .set("spark.driver.bindAddress", "127.0.0.1")  # 绑定到本地回环地址
            .set("spark.driver.host", "localhost")  # 声明主机名
            .set("spark.driver.port", "0")  # 随机端口（可尝试固定如 50000）
            .set("spark.blockManager.port", "0")
            .set("spark.executor.memory", "2g")
            .set("spark.driver.memory", "2g")
            .set("spark.executor.cores", "1")
            .set("spark.default.parallelism", "4")
            .set("spark.sql.shuffle.partitions", "4")
            .set("spark.network.timeout", "300s")
            .set("spark.executor.heartbeatInterval", "30s")
            .set("spark.sql.adaptive.enabled", "true")
            .set("spark.sql.adaptive.coalescePartitions.enabled", "true")
            .set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
            .set("spark.driver.extraJavaOptions", "-XX:+UseG1GC")
            .set("spark.executor.extraJavaOptions", "-XX:+UseG1GC"))

    sc = SparkContext(conf=conf)
    spark = SparkSession.builder.config(conf=conf).getOrCreate()
    return sc, spark


def cleanup_spark_session(sc, spark):
    """cleanup Spark Session"""
    try:
        if spark:
            spark.stop()
        if sc:
            sc.stop()
        # Force garbage collection
        gc.collect()
        time.sleep(1)  # Give Spark some time to clean up
    except Exception as e:
        print(f"Error cleaning up Spark session: {e}")


# ========== HDFS FILE OPERATIONS ==========
def list_path(hdfs_dir):
    """返回列表，元素格式 'DIR:/user/xxx' 或 'FILE:/user/xxx'"""
    hdfs_dir = hdfs_dir.rstrip('/') if hdfs_dir != '/' else ''
    try:
        file_list = client.list(hdfs_dir)
        result = []
        for file_path in file_list:
            full_path = f"{hdfs_dir}/{file_path}" if hdfs_dir else f"/{file_path}"
            status = client.status(full_path)
            if status['type'] == 'DIRECTORY':
                result.append(f"DIR:{full_path}")
            else:
                result.append(f"FILE:{full_path}")
        return result
    except Exception as e:
        print(f"HDFS list error: {e}")
        return []


def upload_file(filename, fileContent, overwrite=False):
    """
        上传文件到HDFS
        :param filename: 文件名
        :param fileContent: 文件内容（bytes）
        :param overwrite: 是否覆盖已存在的文件/目录
        :return: HDFS路径（字符串）
        :raises FileExistsError: 当文件已存在且overwrite=False时抛出
    """
    # hdfs_root_path = f"hdfs://{HDFS_HOST}:{HDFS_FILE_PORT}/user"
    # hdfs_path = f"hdfs://{HDFS_HOST}:{HDFS_FILE_PORT}/user/{filename}"
    hdfs_root_path = f"/user"  # 基础路径
    hdfs_path = f"/user/{filename}"  # 完整HDFS路径（用于Spark目录写入或直接文件写入）
    # 注意：对于CSV等文本文件，我们将用Spark写入，目标路径是一个目录，目录名为filename

    # 检查目标是否存在
    if hdfs_exists(hdfs_path):
        if overwrite:
            print(f"目标路径 {hdfs_path} 已存在，将覆盖")
            # 删除已存在的目录或文件
            try:
                client.delete(hdfs_path, recursive=True)
            except Exception as e:
                print(f"删除已存在路径失败: {e}")
                raise
        else:
            raise FileExistsError(f"文件 {filename} 已存在于 HDFS 中")

    # 创建独立的Spark会话
    sc, spark = create_spark_session()
    print("upload方法， [Spark] 创建新的Spark会话")
    try:
        print(f"接收到的文件名: {filename}", f"接收到的文件内容类型: {type(fileContent)}", fileContent)
        if isinstance(fileContent, tuple):
            # 如果 fileContent 是元组，尝试取出其中的第一个元素
            fileContent = fileContent[0]  # 取元组的第一个元素
        if not isinstance(fileContent, bytes):
            raise ValueError("fileContent is not a byte-like object")

        if filename.lower().endswith('.csv'):
            try:
                print('处理 CSV 文件')
                data = fileContent.decode('utf-8')  # 使用 UTF-8 解码
                lines = data.splitlines()  # 按行分割
                rdd = sc.parallelize(lines).coalesce(1)  # coalesce(1)强制生成1个文件
                rdd.saveAsTextFile(f"hdfs://{HDFS_HOST}:{HDFS_FILE_PORT}{hdfs_path}")
            except Exception as e:
                print(f"上传csv文件时出错：{e}")
                traceback.print_exc()
                return f"失败：{str(e)}"
            return hdfs_path

        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            print(f'处理图像文件: {filename}')
            full_file_path = f"{hdfs_root_path}/{filename}"
            # 使用hdfs客户端直接写入二进制文件（避免RDD文本处理）
            with client.write(full_file_path, overwrite=True) as writer:
                writer.write(fileContent)
            return full_file_path

        elif filename.lower().endswith('.txt'):
            print('处理 TXT 文件')
            data = fileContent.decode('utf-8')
            lines = data.splitlines()
            rdd = sc.parallelize(lines).coalesce(1)
            rdd.saveAsTextFile(f"hdfs://{HDFS_HOST}:{HDFS_FILE_PORT}{hdfs_path}")
            return hdfs_path

        elif filename.lower().endswith('.xls') or filename.lower().endswith('.xlsx'):
            print('处理 Excel 文件')
            excel_data = io.BytesIO(fileContent)
            df = pd.read_excel(excel_data)
            # 转换为CSV并上传到HDFS
            csv_filename = filename.split('.')[0] + '.csv'
            csv_hdfs_path = f"{hdfs_root_path}/{csv_filename}"
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_content = csv_buffer.getvalue().encode('utf-8')
            # 先检查csv是否存在
            if hdfs_exists(csv_hdfs_path) and not overwrite:
                raise FileExistsError(f"文件 {csv_filename} 已存在于 HDFS 中")
            with client.write(csv_hdfs_path, overwrite=True) as writer:
                writer.write(csv_content)
            return csv_hdfs_path
        #     print('处理 XLS 文件')
        #     # 确保 fileContent 是 bytes 类型
        #     excel_data = io.BytesIO(fileContent)  # 将字节数据转换为 BytesIO 以便 Pandas 使用
        #     df = pd.read_excel(excel_data)  # 读取 Excel 文件
        #     # 将 DataFrame 保存为 CSV 到 HDFS
        #     hdfs_csv_path = f"{hdfs_root_path}/{filename.split('.')[0]}.csv"  # 保存为 CSV 格式
        #     df.to_csv(hdfs_csv_path, index=False)  # 使用 pandas 保存文件
        #     return "success"
        else:
            raise ValueError(f"不支持的文件类型: {filename}")
        # return 'fail'
    except Exception as e:
        print(f"上传文件时出错：{e}")
        traceback.print_exc()
        raise  # 抛出异常，由上层处理
    finally:
        if sc or spark:
            print("[Spark] 清理Spark会话")
            cleanup_spark_session(sc, spark)

def detect_delimiter(line):
    # 尝试检测常见的分隔符
    delimiters = [',', '\t', ';', ' ', '|']
    delimiter_counts = {}
    for delimiter in delimiters:
        count = line.count(delimiter)
        delimiter_counts[delimiter] = count
    # 选择出现次数最多的分隔符
    if delimiter_counts:
        return max(delimiter_counts, key=delimiter_counts.get)
    else:
        return None

# def load_data(file_path):
#     """数据加载方法"""
#     # 创建独立的Spark会话
#     sc, spark = create_spark_session()
#     print("load_data方法，[Spark] 创建新的Spark会话")
#     try:
#         # 尝试不同的编码方式
#         encodings = ['utf-8', 'gbk', 'latin-1', 'iso-8859-1']
#         for encoding in encodings:
#             try:
#                 # 加载数据并检测分隔符
#                 first_line = spark.read.text(file_path).first().value
#                 delimiter = detect_delimiter(first_line)
#                 if delimiter is None:
#                     raise ValueError("无法检测到分隔符，请手动指定分隔符")
#                 print(f"检测到的分隔符: '{delimiter}'，编码: {encoding}")
#                 data = spark.read.csv(file_path, header=True, inferSchema=True, sep=delimiter, encoding=encoding)
#                 # 清理空列
#                 empty_cols = [col for col in data.columns if col in ['', '_c0']]
#                 if empty_cols:
#                     data = data.drop(*empty_cols)
#                 pandas_df = data.toPandas()
#                 # 检查数据质量
#                 if pandas_df.empty:
#                     continue
#                 print(f"成功加载数据: {pandas_df.shape}")
#                 return pandas_df
#             except Exception as e:
#                 print(f"使用编码 {encoding} 失败: {e}")
#                 continue
#         raise ValueError("所有编码方式都失败，无法加载数据")
#     except Exception as e:
#         print(f"数据加载失败: {e}")
#         raise
#     finally:
#         # 确保Spark会话被清理
#         if sc or spark:
#             print("[Spark] 清理Spark会话")
#             cleanup_spark_session(sc, spark)
