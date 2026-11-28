# ENCflow/examples/paddy_dam/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(data/。make_district.py)を作る
#   make run    同じ地区を、表現 A(Δx = 30 m。サブグリッドの水田タンク)の 6 ケース(A30_*: 片方向・双方向・
#               双方向で集水面積率を与える × 通常・田んぼダム)と表現 B(Δx = 10 m。区画の解像)の 4 ケース
#               (B10_*: N・D・Du・Dd)、小排水路を実際の幅 1.5 m にした表現 B の 2 ケース(B10_Nw・B10_Dw)で
#               順に計算する(4 コアの計算機で表現 A は 1 ケース 2〜3 分、表現 B は 10〜20 分)
#   make figs   図(figs/・en/figs/)と数表(標準出力)
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= A30_N A30_D A30_N2 A30_D2 A30_N2c A30_D2c B10_N B10_D B10_Du B10_Dd B10_Nw B10_Dw

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

data/z.txt: make_district.py
	python3 make_district.py

run: all
	@for c in $(CASES); do \
	    ./encflow param_$$c.txt | tee Screen_$$c.log; \
	done

figs:
	python3 plot_results.py
	python3 plot_results.py en

install: all

clean:
	rm -rf result_* data
	rm -f encflow encflow_mpi a.out Screen*.log

.PHONY: all links inputs run figs install clean
