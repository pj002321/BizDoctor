# -*- coding: utf-8 -*-
"""
상권 신호등 - TensorFlow 스코어링 모델 학습

설계:
  - 입력: 관찰된 최근 3개월 매출 시계열(시퀀스) + 정적 피처(업종 내 폐업률 percentile,
          프랜차이즈 비중, KOSIS 산업대분류 임베딩)
  - 출력: risk_type 6-class 분류 (정상_유지형 / 단기_매출_정체형 / 원가_상승_부담형 /
          매출_폭락형 / 고금리_과다채무형 / 상권_침체_붕괴형)
  - "3개월치 관측만으로 향후(4~6개월차) 흐름이 반영된 risk_type을 미리 잡아낸다"는
    컨셉 = 기획서의 '3개월 뒤 위험 예측'과 동일한 구조.
  - risk_type을 맞추면 risk_level(RED/YELLOW/GREEN)과 score는 매핑으로 자동 도출됨.
"""
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight
import os
import sys
from pathlib import Path

# ai-service/ 를 import 경로에 넣어 app/core/config.py 를 쓴다(이 줄은 config 를 찾기 위한 것).
# 입출력 경로는 config.DATA_DIR(ai-service/data) 한 곳에서 정한다. 어디서 실행해도 같은 파일을 읽고 쓴다.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.core import config  # noqa: E402

os.chdir(config.DATA_DIR)

RNG_SEED = 42
np.random.seed(RNG_SEED)
tf.random.set_seed(RNG_SEED)

# ------------------------------------------------------------------
# 1. 데이터 로드 & 병합
# ------------------------------------------------------------------
companies = pd.read_csv("synthetic_companies.csv")
sales_ts = pd.read_csv("synthetic_sales_timeseries.csv")

# 최근 3개월(1~3월차)만 "관측 가능한 입력"으로 사용 (4~6월차는 미래 -> 라벨에만 반영됨)
seq = sales_ts[sales_ts["월차"] <= 3].pivot(
    index="company_id", columns="월차", values="매출지수"
)
seq.columns = [f"m{c}" for c in seq.columns]
seq = seq.reset_index()

df = companies.merge(seq, on="company_id")

# ------------------------------------------------------------------
# 2. 피처 구성
# ------------------------------------------------------------------
# (a) 시퀀스 입력: 3개월 매출지수를 스케일링 (첫 달 대비 상대값으로 변환 -> 절대 규모 영향 제거)
seq_raw = df[["m1", "m2", "m3"]].values.astype("float32")
seq_rel = seq_raw / seq_raw[:, [0]]        # 1개월차 대비 상대 매출
seq_rel = seq_rel[:, :, np.newaxis]        # (N, 3, 1) LSTM 입력 형태

# (b) 정적 피처
static_cols = ["폐업률_업종내_percentile", "프랜차이즈_비중"]
df[static_cols] = df[static_cols].fillna(df[static_cols].median())
static_scaler = StandardScaler()
static_X = static_scaler.fit_transform(df[static_cols])

# (c) 업종대분류(KOSIS_산업1) 원-핫
industry_dummies = pd.get_dummies(df["KOSIS_산업1"], prefix="ind").values.astype("float32")

static_X_full = np.concatenate([static_X, industry_dummies], axis=1).astype("float32")

# (d) 타겟: risk_type
label_enc = LabelEncoder()
y = label_enc.fit_transform(df["risk_type"])
n_classes = len(label_enc.classes_)
print("클래스:", list(label_enc.classes_))

# ------------------------------------------------------------------
# 3. train/test 분할 (stratify로 소수 클래스 비율 유지)
# ------------------------------------------------------------------
idx_train, idx_test = train_test_split(
    np.arange(len(df)), test_size=0.2, stratify=y, random_state=RNG_SEED
)

seq_train, seq_test = seq_rel[idx_train], seq_rel[idx_test]
static_train, static_test = static_X_full[idx_train], static_X_full[idx_test]
y_train, y_test = y[idx_train], y[idx_test]

# 클래스 불균형 보정 — 현재는 비활성화(USE_CLASS_WEIGHT=False)
#
# 왜 껐는가:
#   인코딩 수정으로 RED가 3개 유형(94/66/11)으로 쪼개지면서 학습 9건짜리 클래스가 생겼고,
#   "balanced" 공식이 여기에 44.4배 가중치를 부여한다(정상은 0.19 → 최대/최소 228배).
#   손실이 9건에 끌려가면서 정상 재현율이 99.8% → 26%로 붕괴했다.
#   결정적으로 RED 재현율은 켜든 끄든 85.3%로 동일 — 즉 이 가중치는 본래 목적(위험군 포착)에
#   기여하지 않으면서 나머지 성능만 깎고 있었다.
#   재현율을 높여야 한다면 손실 가중치가 아니라 예측 확률 임계값으로 조정할 것.
#   (표본이 보강되어 최소 클래스가 수백 건이 되면 다시 켜도 무방하다)
USE_CLASS_WEIGHT = False

class_weights_arr = compute_class_weight(
    class_weight="balanced", classes=np.unique(y_train), y=y_train
)
class_weight = dict(zip(np.unique(y_train), class_weights_arr))
print("클래스 가중치(참고용):", {label_enc.classes_[k]: round(v, 2) for k, v in class_weight.items()})
print("class_weight 적용 여부:", USE_CLASS_WEIGHT)

# ------------------------------------------------------------------
# 4. 모델 구성 (시퀀스 LSTM + 정적 피처 결합)
# ------------------------------------------------------------------
seq_input = keras.Input(shape=(3, 1), name="sales_sequence")
x1 = layers.LSTM(16, activation="tanh")(seq_input)

static_input = keras.Input(shape=(static_X_full.shape[1],), name="static_features")
x2 = layers.Dense(16, activation="relu")(static_input)

merged = layers.Concatenate()([x1, x2])
merged = layers.Dense(32, activation="relu")(merged)
merged = layers.Dropout(0.2)(merged)
output = layers.Dense(n_classes, activation="softmax")(merged)

model = keras.Model(inputs=[seq_input, static_input], outputs=output)
model.compile(
    optimizer=keras.optimizers.Adam(1e-3),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)
model.summary()

# ------------------------------------------------------------------
# 5. 학습
# ------------------------------------------------------------------
early_stop = keras.callbacks.EarlyStopping(
    monitor="val_loss", patience=8, restore_best_weights=True
)

history = model.fit(
    [seq_train, static_train], y_train,
    validation_split=0.15,
    epochs=60,
    batch_size=64,
    callbacks=[early_stop],
    verbose=2,
    **({"class_weight": class_weight} if USE_CLASS_WEIGHT else {}),
)

# ------------------------------------------------------------------
# 6. 평가 (재현율 중심 확인 — 부실 유형을 놓치지 않는지가 핵심)
# ------------------------------------------------------------------
y_pred_prob = model.predict([seq_test, static_test])
y_pred = np.argmax(y_pred_prob, axis=1)

print("\n=== classification_report ===")
print(classification_report(
    y_test, y_pred, target_names=label_enc.classes_, digits=3, zero_division=0
))

print("=== confusion matrix ===")
cm = confusion_matrix(y_test, y_pred)
print(pd.DataFrame(cm, index=label_enc.classes_, columns=label_enc.classes_))

# ------------------------------------------------------------------
# 7. risk_type -> risk_level, score 매핑 & 저장
# ------------------------------------------------------------------
RISKTYPE_TO_LEVEL = {
    "정상_유지형": "GREEN",
    "단기_매출_정체형": "YELLOW",
    "원가_상승_부담형": "YELLOW",
    "매출_폭락형": "RED",
    "고금리_과다채무형": "RED",
    "상권_침체_붕괴형": "RED",
}

# 행정동_코드도 함께 저장한다 — 이름만으로는 신사동(강남구·관악구)을 구분할 수 없다.
pred_df = df.iloc[idx_test][["company_id","행정동_코드","행정동_코드_명","서비스_업종_코드_명","risk_type","risk_level","score"]].copy()
pred_df["예측_risk_type"] = label_enc.inverse_transform(y_pred)
pred_df["예측_risk_level"] = pred_df["예측_risk_type"].map(RISKTYPE_TO_LEVEL)
pred_df["정답여부"] = pred_df["risk_type"] == pred_df["예측_risk_type"]

pred_df.to_csv("model_predictions_sample.csv", index=False, encoding="utf-8-sig")
model.save("risk_model.keras")

print("\n저장 완료: risk_model.keras, model_predictions_sample.csv")
print("\n전체 정확도:", round((pred_df["정답여부"]).mean(), 4))
print("RED 재현율(recall) 확인용 - 실제 RED 중 RED로 예측된 비율:")
red_actual = pred_df[pred_df["risk_level"] == "RED"]
print(round((red_actual["예측_risk_level"] == "RED").mean(), 4))