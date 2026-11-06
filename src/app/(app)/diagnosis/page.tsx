// F-DIA: 개별 사업장 "진단 등급". 지역 결과와 이름·색 범례·URL 을 분리한다(F-SYS-01).
import type { Metadata } from "next";
import DiagnosisView from "@/features/diagnosis/DiagnosisView";

export const metadata: Metadata = { title: "사업장 진단" };

export default DiagnosisView;
