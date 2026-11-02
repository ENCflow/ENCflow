# ENCflow/examples/badland/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(make_terrain.py が z_*.txt・sw_*.txt を作る)
#   make run    7 ケース(主ケース・格子の曲率・相関長 3・格子収束 2)を順に計算する(各 10 秒〜3 分)
#   make supp   補足(崖の崩落 param_rockfall.txt)を計算する(約 2 分)
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
SERIES	= grid lc1 lc2 lc4 lc2_dx05 lc2_dx2

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: z_main.txt z_sweep.txt z_sweep05.txt z_sweep2.txt

z_main.txt: make_terrain.py
	python3 make_terrain.py main

z_sweep.txt: make_terrain.py
	python3 make_terrain.py sweep

z_sweep05.txt: make_terrain.py
	python3 make_terrain.py sweep --dx 0.5

z_sweep2.txt: make_terrain.py
	python3 make_terrain.py sweep --dx 2

# 画面出力は Screen.log / Screen_<ケース>.log(plot_results.py が排出量・上限の回数・崩落の台帳を読む。
# これらは標準エラーに出る警告の行なので 2>&1 で合わせて記録する)
run: all
	./encflow param.txt 2>&1 | tee Screen.log
	@for c in $(SERIES); do ./encflow param_$$c.txt 2>&1 | tee Screen_$$c.log; done

supp: all
	./encflow param_rockfall.txt 2>&1 | tee Screen_rockfall.log

install: all

clean:
	rm -rf result result_* save save_*
	rm -f encflow encflow_mpi a.out Screen.log Screen_*.log z.txt z_*.txt sw_*.txt

.PHONY: all links inputs run supp install clean
