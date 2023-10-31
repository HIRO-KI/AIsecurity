# 宅配業者の制服をラズパイのカメラで認証させ、宅配ボックスを開ける宅配防犯システム
# 人を検知したら写真を撮影しAIで判定
# 宅配業者の場合、IoTデバイスに信号を送り
# BOXの開錠と施錠を行い、LINEに訪問を通知する


# 画像処理用のOpenCVなど各種ライブラリの取り込み
import cv2
import numpy as np
import argparse
import time
import random
import serial
import subprocess
import predict


# HTTP 用の requests ライブラリの取り込み
import requests
#.netrc から必要な情報を取り込むのに使う netrc ライブラリの取り込み
import netrc

#VGG16に使う
from tensorflow import keras
from tensorflow.keras.models import Sequential, Model,load_model
from PIL import Image
import sys

#VGG16推論
def vgg16_suiron(gazou):

    # パラメーターの初期化
    classes = ["gyosya1", "others"]
    num_classes = len(classes)
    image_size = 224

    # 引数から画像ファイルを参照して読み込む
    image = Image.open(gazou)
    image = image.convert("RGB")
    image = image.resize((image_size,image_size))
    data = np.asarray(image) / 255.0
    X = []
    X.append(data)
    X = np.array(X)

    # モデルのロード
    model = load_model('./vgg16_transfer.h5')

    result = model.predict([X])[0]
    predicted = result.argmax()
    percentage = int(result[predicted] * 100)

    return classes[predicted], percentage


# カメラバッファ読み飛ばし回数
CAMERA_BUF_FLUSH_NUM = 6


# 人工知能モデルへ入力する画像の調整パラメタ
IN_WIDTH = 224
IN_HEIGHT = 224

# Mobilenet SSD COCO学習済モデルのラベル一覧の定義
CLASS_LABELS = {0: 'background', 1: 'person'} 

# .netrcからトークンを読み込む
secrets = netrc.netrc('/home/pi/.netrc')
username, account, line_notify_token = secrets.authenticators('notify-api')

# 引数の定義
ap = argparse.ArgumentParser()
ap.add_argument('-p', '--pbtxt', required=True,
                help='path to pbtxt file')
ap.add_argument('-w', '--weights', required=True,
                help='path to TensorFlow inference graph')
ap.add_argument('-c', '--confidence', type=float, default=0.3,
                help='minimum probability')
ap.add_argument('-i', '--interval', type=int, default=0,
                help='process interval to reduce CPU usage')
ap.add_argument('-t', '--target', type=int, default=1,
                help='target class id')
args = vars(ap.parse_args())

target_class_id = args['target']

colors = {}
# ラベル毎の枠色をランダムにセット
random.seed()
for key in CLASS_LABELS.keys():
    colors[key] = (random.randrange(255),
                   random.randrange(255),
                   random.randrange(255))

# 人工知能モデルの読み込み
print('モデル読み込み...')
net = cv2.dnn.readNet(args['weights'], args['pbtxt'])

# ビデオカメラ開始
print('ビデオカメラ開始...')
cap = cv2.VideoCapture(0)

# 前回送信時の時刻を0にセット
last_send_time = 0

#画像保存したフラグ
image_cap = 0

# 画像キャプチャと検出の永久ループ
while True:

    #バッファに滞留しているカメラ画像を指定回数読み飛ばし、最新画像をframeに読み込む
    for i in range(CAMERA_BUF_FLUSH_NUM):
        ret, frame = cap.read()

    # 取り込んだ画像の幅を縦横比を維持して500ピクセルに縮小
    ratio = 500 / frame.shape[1]
    frame = cv2.resize(frame, dsize=None, fx=ratio, fy=ratio)

    # 高さと幅情報を画像フレームから取り出す
    (frame_height, frame_width) = frame.shape[:2]

    # 画像フレームを調整しblob形式へ変換
    blob =  cv2.dnn.blobFromImage(frame, size=(IN_WIDTH, IN_HEIGHT), swapRB=False, crop=False)

    # blob形式の入力画像を人工知能にセット
    net.setInput(blob)

    # 画像を人工知能へ流す（計算させる）
    detections = net.forward()

    # ターゲット検出数を0にリセット
    target_object_count = 0

    # 検出数（mobilenet SSDでは100）繰り返し
    for i in range(detections.shape[2]):
        class_id = int(detections[0, 0, i, 1])

        # ターゲットオブジェクトでなければ何もしない
        if class_id != target_class_id:
            continue

        # i番目の検出オブジェクトの正答率を取り出す
        confidence = detections[0, 0, i, 2]

        # 正答率がしきい値を下回ったらなにもしない
        if confidence < args['confidence']:
            continue

        # ターゲット検出数を加算
        target_object_count += 1

        # 検出物体の種別と座標を取得
        class_id = int(detections[0, 0, i, 1])
        start_x = int(detections[0, 0, i, 3] * frame_width)
        start_y = int(detections[0, 0, i, 4] * frame_height)
        end_x = int(detections[0, 0, i, 5] * frame_width)
        end_y = int(detections[0, 0, i, 6] * frame_height)

        # 枠をフレームに描画
        cv2.rectangle(frame, (start_x, start_y), (end_x, end_y),
                      colors[class_id], 2)

        # ラベルをフレームに描画
        label = CLASS_LABELS[class_id] + ': ' + str(round(confidence * 100, 2)) + '%'

        label_size, base_line = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)

        cv2.rectangle(frame, (start_x, start_y),
                      (start_x + label_size[0], start_y + base_line + label_size[1]),
                      (255, 255, 255), cv2.FILLED)

        cv2.putText(frame, label, (start_x, start_y + label_size[1]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0))
                    
        print(class_id)
        print(label)

        # 写真を保存する
        people = int(round(confidence * 100, 2))
        if class_id == 1 and people > 80:   # 人判断する値
           path = "./gyosya.jpg"
           cv2.imwrite(path, frame)
           image_cap = 1
           time.sleep(2)

    # フレームを画面に描画（確認用）
    cv2.imshow('Live', frame)

    if cv2.waitKey(1) >= 0:
        break

    #カメラを終了する
    if image_cap == 1:
        #time.sleep(10)
        break

    time.sleep(args['interval'])

# VGG16で推論する
# path = "gyosya.jpg"
predicted_class, percentage = vgg16_suiron("./gyosya.jpg")
print(predicted_class, percentage)

# 推論結果を入力する
#if predicted_class == "gyosya1" or predicted_class == "gyosya3":
if predicted_class == "gyosya1":
    vgg_result_flag = 1
    
else:
    vgg_result_flag = 2

# IoTを操作する
if vgg_result_flag == 1:
    ser = serial.Serial('/dev/ttyUSB0', 115200)
    ser.write(b'A')
    print("open")
    ser.close()


# 終了処理
print('終了...')
cv2.destroyAllWindows()
cap.release()
time.sleep(3)

