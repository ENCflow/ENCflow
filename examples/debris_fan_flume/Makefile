# ENCflow/examples/debris_fan_flume/Makefile
#   make          ../../bin/ の実行ファイルへのリンクと、全ケースの入力・設定(make_init.py)を作る
#   make run      11 ケースを順に計算する(形成の 5 ケース → 侵食の 6 ケース。侵食は形成の保存を初期条件にする)
#   make figs     図を描く(python3 plot_results.py と python3 plot_results.py en)
#   make clean    リンクと生成物を削除する

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

inputs: data_dx5/z.txt

data_dx5/z.txt: make_init.py param.txt
	python3 make_init.py

# 計算済み(result_<case>/Z9998.bil がある)のケースは飛ばす。設定を変えたら make clean から
run: all
	@for c in $$(python3 make_init.py list); do $(MAKE) --no-print-directory result_$$c/Z9998.bil; done

result_%/Z9998.bil:
	@if [ "$*" = form ]; then p=param.txt; else p=param_$*.txt; fi; \
	    ./encflow $$p | tee Screen_$*.log

figs:
	python3 plot_results.py
	python3 plot_results.py en

install: all

clean:
	rm -rf result_* save_* data_*
	rm -f encflow encflow_mpi a.out Screen_*.log param_*.txt

.PHONY: all links inputs run figs install clean
