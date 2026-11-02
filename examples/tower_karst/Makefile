# ENCflow/examples/tower_karst/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(make_terrain.py が z.txt・sd.txt・ksv.txt を作る)
#   make run    主ケース(param.txt)を計算する(1〜2 時間。4 スレッド)
#   make clean  リンクと生成物を削除する
#   画面出力は Screen.log(plot_results.py が湛水の時系列と台帳を読む)

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

inputs: z.txt

z.txt: make_terrain.py
	python3 make_terrain.py

run: all
	./encflow param.txt | tee Screen.log

install: all

clean:
	rm -rf result result_* save save_*
	rm -f encflow encflow_mpi a.out Screen.log Screen*.log analysis*.txt z.txt sd.txt ksv.txt

.PHONY: all links inputs run install clean
