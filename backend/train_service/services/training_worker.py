import io
import os
import random
import sys
import time
import traceback

import cv2
import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from keras.layers import Conv2D, MaxPooling2D, Dense, Flatten
from keras.models import Sequential
from keras.optimizers import Adam
from keras.src.legacy.preprocessing.image import ImageDataGenerator
from keras.utils import to_categorical

from sklearn import metrics
from sklearn.metrics import accuracy_score, mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler

from .hdfs_client import client, create_spark_session, cleanup_spark_session, detect_delimiter
from .progress_tracker import set_phase, update_progress, finalize_record, append_log, redis_client


def log_print(task_id, *args, **kwargs):
    """同时打印到控制台和 Redis 日志"""
    sep = kwargs.get('sep', ' ')
    end = kwargs.get('end', '\n')
    message = sep.join(str(arg) for arg in args) + end
    print(message, end='')
    sys.stdout.flush()
    if task_id:
        append_log(task_id, message.rstrip('\n'))


def inverse_transform_col(scaler, y, n_col):
    """反归一化"""
    y = y.copy()
    y -= scaler.min_[n_col]
    y /= scaler.scale_[n_col]
    return y


def process_image(file_data):
    """处理图像文件"""
    file_path, binary_content = file_data
    image_array = np.frombuffer(binary_content, dtype=np.uint8)
    img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if img is not None:
        img = cv2.resize(img, (128, 128))
    return img


# ---------- BPNN 分类器 ----------
def train_bpnn_classifier(file_path, hidden_layer_sizes, learning_rate, max_iter, task_id, user_id, db):
    # 立即初始化 Redis 进度
    set_phase(task_id, "loading_data")
    update_progress(task_id, epoch=0, error=0, max_epochs=max_iter, training_duration=0)
    log_print(task_id, f"=== 后台任务已启动，task_id={task_id} ===")

    sc, spark = create_spark_session()
    try:
        log_print(task_id, f"开始训练 BPNN 分类器，数据路径: {file_path}")
        df = load_data_with_spark(spark, file_path)
        if df is None or df.empty:
            raise ValueError("无法加载数据或数据为空")

        df_processed = df.copy()
        for col in df_processed.columns:
            if df_processed[col].dtype == 'object':
                try:
                    df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce')
                    if df_processed[col].isna().sum() > len(df_processed) * 0.5:
                        le = LabelEncoder()
                        df_processed[col] = le.fit_transform(df_processed[col].astype(str))
                except:
                    le = LabelEncoder()
                    df_processed[col] = le.fit_transform(df_processed[col].astype(str))
        df_processed = df_processed.dropna()
        if df_processed.empty:
            raise ValueError("预处理后数据为空")

        features = df_processed.iloc[:, :-1].values
        labels = df_processed.iloc[:, -1].values
        if labels.dtype == 'object':
            le = LabelEncoder()
            labels = le.fit_transform(labels)

        scaler = StandardScaler()
        features = scaler.fit_transform(features)
        X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)

        model = MLPClassifier(hidden_layer_sizes=(hidden_layer_sizes,),
                              learning_rate_init=learning_rate,
                              max_iter=1, warm_start=True, random_state=42)

        set_phase(task_id, "training")
        log_print(task_id, f"开始训练，最大迭代次数: {max_iter}")
        start_time = time.time()
        for epoch in range(1, max_iter + 1):
            if redis_client.get(f"training:{task_id}:stop") == "1":
                log_print(task_id, "收到停止信号，正在退出训练...")
                break

            if epoch == 1:
                model.fit(X_train, y_train)
            else:
                model.partial_fit(X_train, y_train, classes=np.unique(y_train))
            loss = model.loss_
            y_pred = model.predict(X_test)
            acc = accuracy_score(y_test, y_pred)
            elapsed = time.time() - start_time
            update_progress(task_id, epoch=epoch, error=loss, accuracy=acc,
                            training_duration=elapsed, max_epochs=max_iter)
            log_print(task_id, f"Epoch {epoch}/{max_iter}: loss={loss:.6f}, accuracy={acc:.4f}, elapsed={elapsed:.2f}s")
            if loss < 0.01:
                log_print(task_id, "损失达到阈值，提前停止训练")
                break

        if redis_client.get(f"training:{task_id}:stop") == "1":
            log_print(task_id, "训练已被用户停止")
            finalize_record(db, task_id, "stopped", None, error_message="User stopped")
            set_phase(task_id, "failed")
        else:
            final_loss = model.loss_
            final_acc = accuracy_score(y_test, model.predict(X_test))
            log_print(task_id, f"训练完成，最终损失: {final_loss:.6f}, 最终准确率: {final_acc:.4f}")
            buffer = io.BytesIO()
            joblib.dump(model, buffer)
            model_bytes = buffer.getvalue()

            # 确保模型目录存在
            model_dir = "/user/models"
            try:
                if not client.status(model_dir, strict=False):
                    client.makedirs(model_dir)
                    log_print(task_id, f"创建模型目录: {model_dir}")
            except Exception as e:
                log_print(task_id, f"检查/创建模型目录失败: {e}")
                raise

            model_path = f"{model_dir}/{task_id}_bpnn_classifier.pkl"
            with client.write(model_path, overwrite=True) as writer:
                writer.write(model_bytes)
            log_print(task_id, f"模型已保存至 HDFS: {model_path}")
            finalize_record(db, task_id, "completed", final_loss, final_accuracy=final_acc, model_path=model_path)
            set_phase(task_id, "completed")
    except Exception as e:
        err_msg = traceback.format_exc()
        log_print(task_id, f"训练失败: {err_msg}")
        finalize_record(db, task_id, "failed", None, error_message=str(e))
        set_phase(task_id, "failed")
    finally:
        cleanup_spark_session(sc, spark)


def load_data_with_spark(spark, file_path):
    try:
        first_line = spark.read.text(file_path).first().value
        delimiter = detect_delimiter(first_line)
        if delimiter is None:
            raise ValueError("无法检测分隔符")
        data = spark.read.csv(file_path, header=True, inferSchema=True, sep=delimiter, encoding='utf-8')
        empty_cols = [col for col in data.columns if col in ['', '_c0']]
        if empty_cols:
            data = data.drop(*empty_cols)
        return data.toPandas()
    except Exception as e:
        print(f"Spark加载数据失败: {e}")
        return None


# ---------- BPNN 回归器 ----------
class BPNNRegression:
    def __init__(self, sizes):
        self.num_layers = len(sizes)
        self.sizes = sizes
        self.biases = [np.random.randn(n, 1) for n in sizes[1:]]
        self.weights = [np.random.randn(r, c) for c, r in zip(sizes[:-1], sizes[1:])]

    def sigmoid(self, x):
        return 1.0 / (1.0 + np.exp(-x))

    def sigmoid_prime(self, x):
        return self.sigmoid(x) * (1 - self.sigmoid(x))

    def feed_forward(self, a):
        for i, (b, w) in enumerate(zip(self.biases, self.weights)):
            if i == len(self.biases) - 1:
                a = np.dot(w, a) + b
            else:
                a = self.sigmoid(np.dot(w, a) + b)
        return a

    def cost_function(self, output_a, y):
        return (output_a - y)

    def back_propagation(self, x, y):
        delta_b = [np.zeros(b.shape) for b in self.biases]
        delta_w = [np.zeros(w.shape) for w in self.weights]
        a = x
        activations = [x]
        zs = []
        for b, w in zip(self.biases, self.weights):
            z = np.dot(w, a) + b
            zs.append(z)
            a = self.sigmoid(z)
            activations.append(a)
        activations[-1] = zs[-1]
        delta = self.cost_function(activations[-1], y)
        delta_b[-1] = delta
        delta_w[-1] = np.dot(delta, activations[-2].T)
        for lev in range(2, self.num_layers):
            z = zs[-lev]
            zp = self.sigmoid_prime(z)
            delta = np.dot(self.weights[-lev + 1].T, delta) * zp
            delta_b[-lev] = delta
            delta_w[-lev] = np.dot(delta, activations[-lev - 1].T)
        return delta_b, delta_w

    def update_WB_by_mini_batch(self, mini_batch, eta):
        batch_par_b = [np.zeros(b.shape) for b in self.biases]
        batch_par_w = [np.zeros(w.shape) for w in self.weights]
        for x, y in mini_batch:
            delta_b, delta_w = self.back_propagation(x, y)
            batch_par_b = [bb + dbb for bb, dbb in zip(batch_par_b, delta_b)]
            batch_par_w = [bw + dbw for bw, dbw in zip(batch_par_w, delta_w)]
        self.weights = [w - (eta / len(mini_batch)) * dw for w, dw in zip(self.weights, batch_par_w)]
        self.biases = [b - (eta / len(mini_batch)) * db for b, db in zip(self.biases, batch_par_b)]

    def MSGD(self, training_data, max_epoch, mini_batch_size, eta, task_id, max_epochs, error=0.01):
        n = len(training_data)
        start_time = time.time()
        for epoch in range(1, max_epoch + 1):
            # 检查停止标志
            if redis_client.get(f"training:{task_id}:stop") == "1":
                log_print(task_id, "收到停止信号，正在退出训练...")
                break

            random.shuffle(training_data)
            mini_batchs = [training_data[k:k + mini_batch_size] for k in range(0, n, mini_batch_size)]
            for mini_batch in mini_batchs:
                self.update_WB_by_mini_batch(mini_batch, eta)
            final_error = self.evaluate(training_data)
            elapsed = time.time() - start_time
            update_progress(task_id, epoch=epoch, error=final_error, training_duration=elapsed, max_epochs=max_epochs)
            if final_error < error:
                return final_error
        return final_error

    def evaluate(self, train_data):
        test_result = [[self.feed_forward(x), y] for x, y in train_data]
        return np.sum([0.5 * (x - y) ** 2 for (x, y) in test_result])

    def predict(self, test_input):
        return [self.feed_forward(x) for x in test_input]


def train_bpnn_regressor(file_path, hidden_layer_sizes, learning_rate, max_epoch, task_id, user_id, db):
    # 立即初始化 Redis 进度
    set_phase(task_id, "loading_data")
    update_progress(task_id, epoch=0, error=0, max_epochs=max_epoch, training_duration=0)
    log_print(task_id, f"=== 后台任务已启动，task_id={task_id} ===")

    sc, spark = create_spark_session()
    try:
        log_print(task_id, f"开始训练 BPNN 回归器，数据路径: {file_path}")
        log_print(task_id, f"Reading from: {file_path}")

        file_content = sc.textFile(file_path)
        first_few_lines = file_content.take(10)
        header_line = first_few_lines[0]
        data_line = first_few_lines[1]
        space_split_header = header_line.split()
        space_split_data = data_line.split()
        has_header = any(not col.replace('.', '').replace('-', '').isdigit() for col in space_split_header)
        if has_header:
            column_names = space_split_header
            data_rdd = file_content.filter(lambda line: line.strip() != header_line.strip())
        else:
            actual_columns = len(space_split_data)
            column_names = [f"feature_{i}" for i in range(actual_columns - 1)] + ["target"]
            data_rdd = file_content
        actual_num_columns = len(column_names)
        from pyspark.sql.types import StructType, StructField, DoubleType
        schema_fields = [StructField(col, DoubleType(), True) for col in column_names]
        schema = StructType(schema_fields)

        def parse_line(line):
            try:
                values = line.strip().split()
                if len(values) != actual_num_columns:
                    if len(values) > actual_num_columns:
                        values = values[:actual_num_columns]
                    else:
                        values = values + [0.0] * (actual_num_columns - len(values))
                float_values = []
                for val in values:
                    try:
                        float_values.append(float(val))
                    except ValueError:
                        float_values.append(0.0)
                return float_values
            except:
                return [0.0] * actual_num_columns

        parsed_rdd = data_rdd.map(parse_line)
        df = spark.createDataFrame(parsed_rdd, schema)
        for column in df.columns:
            df = df.withColumn(column, df[column].cast('float'))
        pandas_df = df.toPandas().astype(float)
        log_print(task_id, f"数据加载完成，形状: {pandas_df.shape}")

        min_max_scaler = MinMaxScaler()
        df_scaled = min_max_scaler.fit_transform(pandas_df)
        df_scaled = pd.DataFrame(df_scaled, columns=pandas_df.columns)
        x, y = df_scaled.iloc[:, :-1], df_scaled.iloc[:, -1]
        cut = int(len(df_scaled) * 0.2)
        x_train, x_test = x.iloc[:-cut], x.iloc[-cut:]
        y_train, y_test = y.iloc[:-cut], y.iloc[-cut:]
        x_train, x_test = x_train.values, x_test.values
        y_train, y_test = y_train.values, y_test.values

        layers = [x_train.shape[1]] + [hidden_layer_sizes] + [1]
        bp = BPNNRegression(layers)
        train_data = [[sx.reshape(-1, 1), sy.reshape(1, 1)] for sx, sy in zip(x_train, y_train)]
        test_data = [sx.reshape(-1, 1) for sx in x_test]

        set_phase(task_id, "training")
        log_print(task_id, f"开始训练，最大迭代次数: {max_epoch}")
        final_error = bp.MSGD(train_data, max_epoch, len(train_data) // 10, learning_rate, task_id, max_epoch)
        log_print(task_id, f"训练完成，最终误差: {final_error:.6f}")

        # 检查是否被用户停止
        if redis_client.get(f"training:{task_id}:stop") == "1":
            log_print(task_id, "训练已被用户停止")
            finalize_record(db, task_id, "stopped", None, error_message="User stopped")
            set_phase(task_id, "failed")
        else:
            y_pred = bp.predict(test_data)
            y_pred = np.array(y_pred).reshape(-1, 1)
            y_pred_inv = inverse_transform_col(min_max_scaler, y_pred.flatten(), n_col=0)
            y_test_inv = inverse_transform_col(min_max_scaler, y_test.flatten(), n_col=0)
            mae = mean_absolute_error(y_test_inv, y_pred_inv)
            mse = mean_squared_error(y_test_inv, y_pred_inv)
            r2 = metrics.r2_score(y_test_inv, y_pred_inv)
            log_print(task_id, f"评估结果: MAE={mae:.6f}, MSE={mse:.6f}, R2={r2:.6f}")

            finalize_record(db, task_id, "completed", final_error, final_mae=mae, final_accuracy=r2)
            set_phase(task_id, "completed")
    except Exception as e:
        err_msg = traceback.format_exc()
        log_print(task_id, f"训练失败: {err_msg}")
        finalize_record(db, task_id, "failed", None, error_message=str(e))
        set_phase(task_id, "failed")
    finally:
        cleanup_spark_session(sc, spark)


# ---------- CNN 图像分类器 ----------
def train_cnn_image_classifier(hdfs_root_path, hidden_layer_sizes, learning_rate, max_epoch, task_id, user_id, db):
    # 立即初始化 Redis 进度
    set_phase(task_id, "loading_data")
    update_progress(task_id, epoch=0, error=0, max_epochs=max_epoch, training_duration=0)
    log_print(task_id, f"=== 后台任务已启动，task_id={task_id} ===")

    sc, spark = create_spark_session()
    num_classes = 24
    size_x, size_y = 128, 128
    try:
        log_print(task_id, f"开始训练 CNN 图像分类器，数据根路径: {hdfs_root_path}")
        hdfs_paths = {
            "train_label": f"{hdfs_root_path.rstrip('/')}/train_label.txt",
            "test_label": f"{hdfs_root_path.rstrip('/')}/val_label.txt",
            "img_dir": f"{hdfs_root_path.rstrip('/')}/24classify_img"
        }

        def take_label(label_hdfs_path, dataset_name):
            label_df = sc.textFile(label_hdfs_path)
            label_data = label_df.collect()
            total_files = len(label_data)
            if total_files == 0:
                return None, None, None, 0
            random.shuffle(label_data)
            label_set, label_img, label_img_label = [], [], []
            update_interval = max(1, total_files // 10)
            for i, line in enumerate(label_data):
                parts = line.strip().split(' ')
                img_name = parts[0]
                img_label = parts[1]
                img_path = os.path.join(hdfs_paths["img_dir"], img_name)
                image_rdd = sc.binaryFiles(img_path)
                image_data = image_rdd.map(process_image).collect()[0]
                label_set.append(img_name)
                label_img.append(image_data)
                label_img_label.append(int(img_label))
                if i % update_interval == 0 or i == total_files - 1:
                    progress = (i + 1) / total_files * 100
                    log_print(task_id, f"[{dataset_name}] 加载进度: {progress:.1f}%")
            label_img = np.array(label_img).astype('float32') / 255.0
            label_img_label = to_categorical(np.array(label_img_label), num_classes=num_classes)
            return label_set, label_img, label_img_label, total_files

        train_set, train_img, train_label, train_total = take_label(hdfs_paths["train_label"], "训练集")
        test_set, test_img, test_label, test_total = take_label(hdfs_paths["test_label"], "测试集")
        if train_img is None:
            raise ValueError("训练数据加载失败")

        log_print(task_id, f"训练集大小: {len(train_img)}, 测试集大小: {len(test_img)}")
        set_phase(task_id, "training")

        # 在 CNN 训练中，每个 epoch 检查停止标志
        class ProgressCallback(tf.keras.callbacks.Callback):
            def __init__(self, task_id, max_epoch):
                super().__init__()
                self.task_id = task_id
                self.max_epoch = max_epoch
                self.epoch_start_time = None
                self.stopped = False

            def on_epoch_begin(self, epoch, logs=None):
                self.epoch_start_time = time.time()
                # 检查停止标志
                if redis_client.get(f"training:{self.task_id}:stop") == "1":
                    log_print(self.task_id, "收到停止信号，正在退出训练...")
                    self.model.stop_training = True
                    self.stopped = True

            def on_epoch_end(self, epoch, logs=None):
                if self.stopped:
                    return
                current_epoch = epoch + 1
                loss = logs.get('loss', 0)
                acc = logs.get('accuracy', 0)
                elapsed = time.time() - self.epoch_start_time if self.epoch_start_time else 0
                update_progress(self.task_id, epoch=current_epoch, error=loss, accuracy=acc,
                                training_duration=elapsed, max_epochs=self.max_epoch)
                log_print(self.task_id, f"Epoch {current_epoch}/{self.max_epoch}: loss={loss:.6f}, accuracy={acc:.4f}, elapsed={elapsed:.2f}s")
                if current_epoch == self.max_epoch:
                    set_phase(self.task_id, "completed")

        train_datagen = ImageDataGenerator(
            rotation_range=30, width_shift_range=0.2, height_shift_range=0.2,
            shear_range=0.2, zoom_range=0.2, horizontal_flip=True, fill_mode='nearest'
        )
        train_flow = train_datagen.flow(train_img, train_label, batch_size=80)
        model = Sequential()
        model.add(Conv2D(32, (3, 3), activation='relu', input_shape=(size_x, size_y, 3)))
        model.add(MaxPooling2D(pool_size=(2, 2)))
        model.add(Conv2D(64, (3, 3), activation='relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))
        model.add(Flatten())
        model.add(Dense(128, activation='relu'))
        model.add(Dense(num_classes, activation='softmax'))
        model.compile(loss='categorical_crossentropy', optimizer=Adam(learning_rate=learning_rate),
                      metrics=['accuracy'])
        log_print(task_id, f"CNN 模型编译完成，开始训练，最大 epoch: {max_epoch}")

        callback = ProgressCallback(task_id, max_epoch)
        model.fit(train_flow, epochs=max_epoch, verbose=1,
                  validation_data=(test_img, test_label),
                  callbacks=[callback])

        # 判断是否被用户停止
        if callback.stopped:
            log_print(task_id, "训练已被用户停止")
            finalize_record(db, task_id, "stopped", None, error_message="User stopped")
            set_phase(task_id, "failed")
        else:
            final_loss, final_acc = model.evaluate(test_img, test_label, verbose=0)
            log_print(task_id, f"训练完成，最终损失: {final_loss:.6f}, 最终准确率: {final_acc:.4f}")
            model_bytes = io.BytesIO()
            model.save(model_bytes, save_format='h5')
            model_dir = "/user/models"

            try:
                if not client.status(model_dir, strict=False):
                    client.makedirs(model_dir)
                    log_print(task_id, f"创建模型目录: {model_dir}")
            except Exception as e:
                log_print(task_id, f"检查/创建模型目录失败: {e}")
                raise


            model_path = f"/user/models/{task_id}_cnn_model.h5"
            with client.write(model_path, overwrite=True) as writer:
                writer.write(model_bytes.getvalue())
            log_print(task_id, f"模型已保存至 HDFS: {model_path}")
            finalize_record(db, task_id, "completed", final_loss, final_accuracy=final_acc, model_path=model_path)
            set_phase(task_id, "completed")
    except Exception as e:
        err_msg = traceback.format_exc()
        log_print(task_id, f"训练失败: {err_msg}")
        finalize_record(db, task_id, "failed", None, error_message=str(e))
        set_phase(task_id, "failed")
    finally:
        cleanup_spark_session(sc, spark)