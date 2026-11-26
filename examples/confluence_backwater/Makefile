# ENCflow/examples/confluence_backwater/Makefile
#   make           ../../bin/ の実行ファイルへのリンクと入力(data/・data_coarse/・junction/data/)を作る
#   make run       本編の 6 ケースを順に計算する(1 ケース 4 スレッドで 6 分前後)
#   make coarse    補足: 粗い格子(Δx = 100 m)の 2 ケースと定常の 1 ケース(合わせて 2 分前後)
#   make coarse_check  補足: 粗い格子の切り分けの 16 ケース(本川だけの定常。合わせて 5 分前後)と数表
#   make coarse_oblique  補足: 斜めの河道での河道の表し方の 47 ケース(直線の河道の等流。合わせて 20 分前後)と数表
#   make steady    補足: 本編の格子の定常の 1 ケース(背水曲線を 1 次元の理論と比べる。4 スレッドで 3 分前後)
#   make junction  補足「合流の形と水位」の 9 ケース(Δx = 10 m の定常。1 ケース 4 スレッドで 2 分前後)
#   make junction_fine  同じ補足の格子の確認 2 ケース(Δx = 5 m。1 ケース 4 スレッドで 10 分前後)
#   make clean     リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= trib main early same raise gate
JCASES	= a45 a90 a135 b45 b90 b135 bend_none bend_outer bend_inner
JFINE	= fa90 fa135
CCHECK	= f_uniform f_constr f_bend f_base f_trib c_uniform c_constr c_bend c_base c_trib \
	  c_constr_round c_constr_split c_constr_full c_bend_k2 c_base_k2 c_trib_k2

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	        for d in junction coarse_check; do ln -sf ../$(BINDIR)/$$b $$d/$$b; done; \
	    else rm -f $$b junction/$$b coarse_check/$$b; fi; \
	done

inputs: data/z.txt data_coarse/z.txt junction/data/z_a90.txt

data/z.txt: make_terrain.py
	python3 make_terrain.py

data_coarse/z.txt: make_coarse.py make_terrain.py data/z.txt
	python3 make_coarse.py

junction/data/z_a90.txt: junction/make_junction.py
	cd junction && python3 make_junction.py

run: all
	@for c in $(CASES); do \
	    if [ $$c = same ]; then p=param.txt; else p=param_$$c.txt; fi; \
	    ./encflow $$p | tee Screen_$$c.log; \
	done

coarse: all
	@for c in main same steady; do ./encflow param_coarse_$$c.txt | tee Screen_coarse_$$c.log; done

coarse_check: all
	@cd coarse_check && python3 make_check.py > /dev/null && \
	    for c in $(CCHECK); do ./encflow param_$$c.txt > Screen_$$c.log || exit 1; done && python3 make_check.py table

coarse_oblique: all
	@cd coarse_check && python3 oblique.py gen && cd oblique && ln -sf ../encflow encflow && \
	    for c in $$(cat cases.txt); do ./encflow param_$$c.txt > Screen_$$c.log || exit 1; done && \
	    cd .. && python3 oblique.py table

steady: all
	./encflow param_steady.txt | tee Screen_steady.log

junction: all
	@cd junction && for c in $(JCASES); do ./encflow param_$$c.txt | tee Screen_$$c.log; done

junction_fine: all
	@cd junction && for c in $(JFINE); do ./encflow param_$$c.txt | tee Screen_$$c.log; done

install: all

clean:
	rm -rf result_* data data_coarse junction/result_* junction/data coarse_check/result_* coarse_check/data_* coarse_check/oblique
	rm -f encflow encflow_mpi junction/encflow junction/encflow_mpi Screen*.log junction/Screen*.log
	rm -f coarse_check/encflow coarse_check/encflow_mpi coarse_check/Screen*.log

.PHONY: all links inputs run coarse coarse_check coarse_oblique steady junction junction_fine install clean
