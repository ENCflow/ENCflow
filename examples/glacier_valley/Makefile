# ENCflow/examples/glacier_valley/Makefile
#   make            ../../bin/ の実行ファイルへのリンクと初期地形(make_terrain.py)を作る
#   make run        氷期の段(param_glacial.txt。地形時間 6000 年。4 スレッドで約 1 時間)
#   make run-lakes  湖の段(氷期の段の最終の地形に雨を降らせる。約 5 分)
#   make plot       図(figs/*.png と en/figs/*.png)
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

run-lakes: all
	python3 prep_lakes.py
	./encflow param_lakes.txt 2>&1 | tee Screen_lakes.log

plot:
	python3 plot_results.py
	python3 plot_results.py en

clean:
	rm -f encflow encflow_mpi Screen_*.log
	rm -rf data result_glacial save_glacial result_lakes

.PHONY: all links inputs run run-lakes plot clean
