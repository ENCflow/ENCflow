# ENCflow/tutorials/bmi/Makefile
#
#   make        BMI 共有ライブラリ ../../bmi/libencflow_bmi.so をビルドする
#               (必要なら ../../src もビルドされる)。Python ラッパー
#               bmi/python/encflow.py はこのライブラリを自動で見つける
#   make clean  このディレクトリの計算結果と図・連番画像を削除する
#               (ライブラリは消さない。消すなら ../../bmi で make clean)

TOPDIR	= ../..
BMIDIR	= $(TOPDIR)/bmi

all: $(BMIDIR)/libencflow_bmi.so

$(BMIDIR)/libencflow_bmi.so:
	$(MAKE) -C $(BMIDIR)

clean:
	rm -rf result result_norain frames figs/step4_depth.png __pycache__

.PHONY: all clean
