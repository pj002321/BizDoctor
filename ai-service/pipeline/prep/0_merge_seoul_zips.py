# -*- coding: utf-8 -*-
"""
상권 신호등 - 0단계: 서울시 상권분석서비스 zip 3개 병합

preprocess_seoul_panel.py 를 돌리기 전에 반드시 먼저 실행해야 함.
zip 파일 3개(2023/2024/2025년) 안의 csv를 하나로 합쳐서
seoul_panel_raw.parquet 으로 저장한다.

실행 순서: 0_merge_seoul_zips.py → preprocess_seoul_panel.py →
           join_kosis_hardship.py → generate_synthetic_timeseries.py →
           train_risk_model.py → rag_pipeline.py
"""
import glob
import zipfile
import pandas as pd
import os
from pathlib import Path

# 입출력 경로는 전부 ai-service/data/ 기준이다. 어디서 실행해도 같은 파일을 읽고 쓴다.
os.chdir(Path(__file__).resolve().parents[2] / "data")

ZIP_FILES = sorted(glob.glob("raw/서울시*상권분석서비스*.zip"))
print("발견된 zip 파일:", ZIP_FILES)
if len(ZIP_FILES) != 3:
    print("⚠ 3개가 아님! 파일명을 확인하거나 아래 ZIP_FILES 리스트에 직접 경로를 적어주세요.")

dfs = []
for zip_path in ZIP_FILES:
    with zipfile.ZipFile(zip_path) as z:
        # zip 안에 csv가 하나만 들어있다고 가정
        csv_name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(csv_name) as f:
            df = pd.read_csv(f, encoding="cp949")
        dfs.append(df)
        print(f"{zip_path} -> {csv_name} 로드 완료: {df.shape}")

merged = pd.concat(dfs, ignore_index=True)
print("\n병합 결과:", merged.shape)

merged.to_parquet("seoul_panel_raw.parquet")
print("저장 완료: seoul_panel_raw.parquet")