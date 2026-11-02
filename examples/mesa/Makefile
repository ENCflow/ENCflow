# ENCflow/examples/mesa/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(make_terrain.py が z.txt・z_dx4.txt を作る)
#   make run    主ケース cap・nocap を計算する(各 8 分。4 スレッド)
#   make bench  補足 1: 中間の硬い層(bench・bench2・bench3)
#   make sat    補足 2: 増幅の飽和(sat・sat2。図は bench2・bench3 と比べる)
#   make rock   補足 3: 段差の規則の崩落(rock〜rock5。図は bench2 と比べる)
#   make dx4    補足 3: Δx = 4 m(dx4・dx4_rock・dx4_rock2・dx4_rc・dx4_rc2。各 30 秒)
#   make rc     補足 3: 窓版(rc・rc2)
#   make face   補足 3: 支え方式(face〜face5。図は rc2 と比べる)
#   make uc     補足 3: 張り出しと両立の案(uc〜uc3・uc_cap・uc_slow。uc_slow は約 16 分)
#   make clean  リンクと生成物を削除する(z_dx4.txt は入力として残す)
#   画面出力は Screen_<ケース>.log(plot_results.py が崩落・排出の台帳を読む)。図の比較の相手は
#   その系列より前のターゲットで計算する(例: make bench のあとに make sat)

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
MAIN	= cap nocap
BENCH	= bench bench2 bench3
SAT	= sat sat2
ROCK	= rock rock2 rock3 rock4 rock5
DX4	= dx4 dx4_rock dx4_rock2 dx4_rc dx4_rc2
RC	= rc rc2
FACE	= face face2 face3 face4 face5
UC	= uc uc2 uc3 uc_cap uc_slow
RUN	= @for c in $(1); do ./encflow param_$$c.txt | tee Screen_$$c.log; done

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: z.txt z_dx4.txt

z.txt: make_terrain.py
	python3 make_terrain.py

z_dx4.txt: make_terrain.py
	python3 make_terrain.py --dx 4

run: all
	$(call RUN,$(MAIN))

bench: all
	$(call RUN,$(BENCH))

sat: all
	$(call RUN,$(SAT))

rock: all
	$(call RUN,$(ROCK))

dx4: all
	$(call RUN,$(DX4))

rc: all
	$(call RUN,$(RC))

face: all
	$(call RUN,$(FACE))

uc: all
	$(call RUN,$(UC))

install: all

clean:
	rm -rf result result_* save save_*
	rm -f encflow encflow_mpi a.out Screen.log Screen_*.log analysis*.txt z.txt

.PHONY: all links inputs run bench sat rock dx4 rc face uc install clean
