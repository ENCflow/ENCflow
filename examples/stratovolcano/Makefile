# ENCflow/examples/stratovolcano/Makefile
#   make           ../../bin/ の実行ファイルへのリンクを作る
#   make run       主ケース P(火砕物の多い噴火 + 侵食)・比較 L(溶岩の多い噴火 + 侵食)・
#                  対照 P0(P と同じ噴火で侵食なし)を順に計算する(合わせて約 16 分)
#   make run-P / run-L / run-P0   1 ケースだけ計算する
#   make clean     リンクと計算結果を削除する
#   時間は 4 スレッドの目安。図は python3 plot_results.py(引数 en で英語版を en/figs/ に)

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src

all: links

links:
	@if [ ! -e $(BINDIR)/encflow ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

run: run-P run-L run-P0

run-P: all
	python3 run_cycles.py P 2>&1 | tee Screen_P.log

run-L: all
	python3 run_cycles.py L 2>&1 | tee Screen_L.log

run-P0: all
	python3 run_cycles.py P0 2>&1 | tee Screen_P0.log

install: all

clean:
	rm -rf result_*
	rm -f encflow encflow_mpi Screen_*.log

.PHONY: all links run run-P run-L run-P0 install clean
