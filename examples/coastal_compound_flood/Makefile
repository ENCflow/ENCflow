# ENCflow/examples/coastal_compound_flood/Makefile
#   make          ../../bin/ の実行ファイルへのリンクと、入力マップ・全ケースの設定(gen_data.py)を作る
#   make run      本体の 6 ケースを計算する(1 ケース 4 スレッドで 2 分ほど)
#   make lag      雨と高潮のピークのずれの 8 ケースを計算する
#   make supp     補足(下水道を通った水の割合)の 2 ケースを計算する
#   make check    数値設定の確認の 4 ケースを計算する(合わせて数十分。任意)
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

inputs: data/z.txt

data/z.txt: gen_data.py param.txt
	python3 gen_data.py

# 計算済み(result_<case>/H9999.txt がある)のケースは飛ばす。設定を変えたら make clean から
run: all
	@for c in $$(python3 gen_data.py list); do $(MAKE) --no-print-directory result_$$c/H9999.txt; done

lag: all
	@for c in $$(python3 gen_data.py lag); do $(MAKE) --no-print-directory result_$$c/H9999.txt; done

supp: all
	@for c in $$(python3 gen_data.py supp); do $(MAKE) --no-print-directory result_$$c/H9999.txt; done

check: all
	@for c in $$(python3 gen_data.py check); do $(MAKE) --no-print-directory result_$$c/H9999.txt; done

result_%/H9999.txt:
	@if [ "$*" = compound ]; then p=param.txt; else p=param_$*.txt; fi; \
	    ./encflow $$p | tee Screen_$*.log

figs:
	python3 plot_results.py
	python3 plot_results.py en

install: all

clean:
	rm -rf result_* data data_slot50 data_dx10 __pycache__
	rm -f encflow encflow_mpi a.out Screen_*.log param_*.txt

.PHONY: all links inputs run lag supp check figs install clean
