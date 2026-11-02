# ENCflow/examples/badland_storm/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(make_terrain.py が平坦・傾き 2 %・
#               傾き 2 % の Δx 2 m / 0.5 m の地形を作る)
#   make run    結果 1・2 の 5 ケース(対照・表面流あり、平坦・傾き、表面流の水理だけ)を順に計算する
#               (表面流ありは約 22 分、対照は約 8 分。4 スレッド)
#   make wet    結果 3 の強い湿潤侵食(param_storm_wet.txt)を計算する
#   make conv   結果 4・5 の 5 ケース(格子収束、wet_lw = 2 m)を順に計算する(Δx = 0.5 m は 1 時間前後)
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= dry storm dry_tilt storm_tilt stormnowet_tilt
CONV	= storm_wet_dx2 storm_wet_dx05 storm_wet_lw_dx2 storm_wet_lw storm_wet_lw_dx05

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: z_main.txt z_main_tilt.txt z_main2_tilt.txt z_main05_tilt.txt

z_main.txt: make_terrain.py
	python3 make_terrain.py main

z_main_tilt.txt: make_terrain.py
	python3 make_terrain.py main --tilt 0.02

z_main2_tilt.txt: make_terrain.py
	python3 make_terrain.py main --tilt 0.02 --dx 2

z_main05_tilt.txt: make_terrain.py
	python3 make_terrain.py main --tilt 0.02 --dx 0.5 --ly 120

run: all
	@for c in $(CASES); do ./encflow param_$$c.txt 2>&1 | tee Screen_$$c.log; done

wet: all
	./encflow param_storm_wet.txt 2>&1 | tee Screen_storm_wet.log

conv: all
	@for c in $(CONV); do ./encflow param_$$c.txt 2>&1 | tee Screen_$$c.log; done

install: all

clean:
	rm -rf result_* save save_*
	rm -f encflow encflow_mpi a.out Screen.log Screen_*.log z_*.txt sw_*.txt

.PHONY: all links inputs run wet conv install clean
