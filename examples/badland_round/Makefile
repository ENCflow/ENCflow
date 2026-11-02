# ENCflow/examples/badland_round/Makefile
#   make         ../../bin/ の実行ファイルへのリンクと入力(make_terrain.py が z.txt を作る)
#   make run     クリープの 4 ケース(D = 0 / 3e-7 / 1e-6 / 3e-6)を順に計算する(1 ケース 2〜4 分)
#   make strata  互層の 5 ケース(層厚 1.5 m: D = 0 / 1e-6、層厚 3 m: D = 0 / 3e-7 / 1e-6)を順に計算する
#   make clean   リンクと生成物を削除する
#   画面出力は Screen_<ケース>.log(plot_results.py が排出量を読む。標準エラーの行なので 2>&1 で合わせて記録する)

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= d0 d3e-7 d1e-6 d3e-6
STRATA	= d0_strata d1e-6_strata d0_strata3 d3e-7_strata3 d1e-6_strata3

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: z.txt

z.txt: make_terrain.py
	python3 make_terrain.py

run: all
	@for c in $(CASES); do ./encflow param_$$c.txt 2>&1 | tee Screen_$$c.log; done

strata: all
	@for c in $(STRATA); do ./encflow param_$$c.txt 2>&1 | tee Screen_$$c.log; done

install: all

clean:
	rm -rf result result_* save save_*
	rm -f encflow encflow_mpi a.out Screen.log Screen_*.log analysis*.txt z.txt

.PHONY: all links inputs run strata install clean
