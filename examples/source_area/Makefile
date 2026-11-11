# ENCflow/examples/source_area/Makefile
#   make          ../../bin/ の実行ファイルへのリンクと入力(data/。make_catchment.py)を作る
#   make run      基本の 3 ケース(過程計算・鉛直浸透のみ・浸透なし)を順に計算する
#   make sweep    斜面の粗度・土層・雨の強さなどを変えた 22 ケース(sweep.py が設定を作る)を順に計算する
#   make -j 4 sweep OMP_NUM_THREADS=1
#                 -j を付けるとケースを並べて計算する(run も同じ。所要時間は README.md)
#   make vz       VZ 流出の土壌柱の計算(雨 10 mm/h と 30 mm/h の 2 ケース。流域の入力は使わず、
#                 数秒で終わる。追補の比較用)
#   make clean    リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= process vertical surface
VZCASES	= vz vz_r30

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: data/catchment.txt

data/catchment.txt: make_catchment.py
	python3 make_catchment.py

# 計算は別の make に渡す(-j を付けても、リンクと入力ができてから始まる)
run: all
	@$(MAKE) --no-print-directory $(addprefix run-,$(CASES))

# 設定 param_sweep_*.txt は sweep.py inputs が毎回作り直す(前回の設定は消す)
sweep: all
	python3 sweep.py inputs
	@$(MAKE) --no-print-directory $$(python3 sweep.py targets)

# VZ 流出の土壌柱(param_vz.txt と param_vz_r30.txt。入力は data_vz/ の区画番号のラスタだけ)
vz: links
	@$(MAKE) --no-print-directory $(addprefix run-,$(VZCASES))

run-process:
	./encflow param.txt | tee Screen_process.log

run-%:
	./encflow param_$*.txt | tee Screen_$*.log

install: all

clean:
	rm -rf result_* data
	rm -f encflow encflow_mpi a.out Screen*.log param_sweep_*.txt

.PHONY: all links inputs run sweep vz install clean
