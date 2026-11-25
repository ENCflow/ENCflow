# ENCflow/examples/snow_avalanche/Makefile
#   make          ../../bin/ の実行ファイルへのリンクと、全ケースの入力・設定(make_init.py)を作る
#   make run      本文の 5 ケース(走路の雪 0・1・2 m、誘導堤あり 2 ケース)を計算する(4 スレッドで 6 分ほど)
#   make extra    補足の 23 ケース(摩擦係数・格子間隔・沢の向き・時間刻み・限界水深・運動量・連行則・全面の雪)を
#                 計算する(4 スレッドで 40 分ほど。格子 2.5 m の 1 ケースが 3 割)
#   make clean    リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
# base は param.txt そのもの
MAIN	= nosnow base deep dam deep_dam
EXTRA	= mu155 mu340 dx10 r22p5 r45 dt2 dthalf dd3 dd3_dthalf dd5 nomom deep_nomom hungr \
	  allsnow allsnow_dd3 allsnow_dd5 allsnow_h allsnow_h_dd3 allsnow_h_dd5 allsnow_t allsnow_t_dd3 allsnow_t_dd5 dx2p5

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: data_dx5_r0_t1/z.txt

data_dx5_r0_t1/z.txt: make_init.py param.txt
	python3 make_init.py

# 計算済み(result_<case>/D9999.bil がある)のケースは飛ばす。設定を変えたら make clean から
run: all
	@for c in $(MAIN); do $(MAKE) --no-print-directory result_$$c/D9999.bil; done

extra: all
	@for c in $(EXTRA); do $(MAKE) --no-print-directory result_$$c/D9999.bil; done

result_%/D9999.bil:
	@if [ "$*" = base ]; then p=param.txt; else p=param_$*.txt; fi; \
	    ./encflow $$p | tee Screen_$*.log

install: all

clean:
	rm -rf result_* data_* __pycache__
	rm -f encflow encflow_mpi a.out Screen_*.log param_*.txt houses.txt

.PHONY: all links inputs run extra install clean
