# ENCflow/examples/levee_breach/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(data/。make_terrain.py・make_breach.py)を作る
#   make run    4 ケースを順に計算する(1 ケース 4 スレッドで 6〜8 分)
#   make supp   補足(仮想壁面の破堤との比較)の入力(data_supp/)を作り、2 ケースを計算する
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= overtop breach delay dike
BREACH	= --cols 14 15 --rows 53 67 --floor-col 16 --tdeep 20

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: data/bm_breach/bmlist.txt data/bm_delay/bmlist.txt

data/z.txt: make_terrain.py
	python3 make_terrain.py

data/bm_breach/bmlist.txt: data/z.txt make_breach.py
	cd data && python3 ../make_breach.py --z z.txt $(BREACH) --t0 180 --t1 240 --out bm_breach

data/bm_delay/bmlist.txt: data/z.txt make_breach.py
	cd data && python3 ../make_breach.py --z z.txt $(BREACH) --t0 240 --t1 300 --out bm_delay

run: all
	@for c in $(CASES); do \
	    if [ $$c = breach ]; then p=param.txt; else p=param_$$c.txt; fi; \
	    ./encflow $$p | tee Screen_$$c.log; \
	done

supp: links data_supp/bm/bmlist.txt
	./encflow param_supp.txt | tee Screen_supp.log
	./encflow param_supp_vwall.txt | tee Screen_supp_vwall.log

data_supp/z.txt: make_supp.py
	python3 make_supp.py

data_supp/bm/bmlist.txt: data_supp/z.txt make_breach.py
	cd data_supp && python3 ../make_breach.py --z z.txt --cols 21 22 --rows 48 52 --floor-col 23 \
	    --t0 70 --t1 90 --tdeep 10 --out bm

install: all

clean:
	rm -rf result_* data data_supp
	rm -f encflow encflow_mpi a.out Screen*.log

.PHONY: all links inputs run supp install clean
