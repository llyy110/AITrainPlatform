import os

HDFS_NAMENODE = os.getenv("HDFS_NAMENODE", "http://127.0.0.1:50070")
HDFS_USER = os.getenv("HDFS_USER", "hdfs")
HDFS_ROOT_PATH = os.getenv("HDFS_ROOT_PATH", "/user")
HDFS_RPC = os.getenv("HDFS_RPC", "hdfs://localhost:9000")
HDFS_HOST = os.getenv("HDFS_HOST", "127.0.0.1")
HDFS_FILE_PORT = os.getenv("HDFS_FILE_PORT", "9000")
HDFS_PORT = os.getenv("HDFS_PORT", "50070")

DATABASE_URL = os.getenv("DATABASE_URL", 'mysql+pymysql://modelmanager:linyu0110@localhost:3308/modelTrainDB')

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "linyu0110")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

JWT_SECRET_KEY = os.getenv("SECRET_KEY", 'django-insecure-lgtiphx#ezoelvx55qamypbif)f57l%r*vxi7m(02q90#*#(y-')
JWT_ALGORITHM = "HS256"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-61f85294584344e5a338370e4fdda294")

TRAIN_SVC_URL = "http://127.0.0.1:8001"
