# ENCflow/examples/glacier_valley/Makefile
#   make            ../../bin/ の実行ファイルへのリンクと初期地形(make_terrain.py)を作る
#   make run        本番(param_glacial.txt。既定の侵食係数で地形時間 6000 年。4 スレッドで約 10 分)
#   make run-x10    補足(param_glacial_x10.txt。侵食係数 10 倍。約 5 分)
#   make run-lakes  湖の段(補足の最終の地形に雨を降らせる。約 3 分)
#   make run-noero  対照(param_glacial_noero.txt。侵食なし。約 10 分)
#   make plot       図(figs/*.png と en/figs/*.png。説明図 mechanism.png だけなら計算の前に python3 plot_schematic.py)
#   make clean      リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: data/z.txt

data/z.txt: make_terrain.py
	python3 make_terrain.py

run: all
	./encflow param_glacial.txt 2>&1 | tee Screen_glacial.log

run-x10: all
	./encflow param_glacial_x10.txt 2>&1 | tee Screen_glacial_x10.log

run-lakes: all
	python3 prep_lakes.py
	./encflow param_lakes.txt 2>&1 | tee Screen_lakes.log

run-noero: all
	./encflow param_glacial_noero.txt 2>&1 | tee Screen_glacial_noero.log

plot:
	python3 plot_schematic.py
	python3 plot_schematic.py en
	python3 plot_results.py
	python3 plot_results.py en

clean:
	rm -f encflow encflow_mpi Screen_*.log
	rm -rf data result_glacial save_glacial result_glacial_x10 save_glacial_x10 \
	       result_glacial_noero save_glacial_noero result_lakes

.PHONY: all links inputs run run-x10 run-lakes run-noero plot clean
