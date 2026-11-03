# ENCflow/examples/shield_volcano/Makefile
#   make           ../../bin/ の実行ファイルへのリンクを作る(設定ファイルはリポジトリに入れてある)
#   make run       楯状火山の S1(降伏応力 2×10³ Pa。約 6 分)と S2(2×10⁴ Pa。約 1.5 分)を計算する
#   make run-dome  溶岩ドーム(固化なし dome・固化あり dome_sol)を計算する(各約 40 秒)
#   make params    設定ファイルを make_param.py で作り直す(乱数の種・噴火の回数などを変えるとき)
#   make clean     リンクと計算結果を削除する
#   時間は 4 スレッドの目安。図は python3 plot_results.py(引数 en で英語版を en/figs/ に)

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src

all: links

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

run: all
	./encflow param_S1.txt 2>&1 | tee Screen_S1.log
	./encflow param_S2.txt 2>&1 | tee Screen_S2.log

run-dome: all
	./encflow param_dome.txt 2>&1 | tee Screen_dome.log
	./encflow param_dome_sol.txt 2>&1 | tee Screen_dome_sol.log

params:
	python3 make_param.py

install: all

clean:
	rm -rf result_* save_*
	rm -f encflow encflow_mpi a.out Screen_*.log z_cone.txt

.PHONY: all links run run-dome params install clean
