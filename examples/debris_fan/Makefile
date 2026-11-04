# ENCflow/examples/debris_fan/Makefile
#   make          ../../bin/ の実行ファイルへのリンクと、全ケースの入力・設定(make_init.py)を作る
#   make run      全 26 ケースを計算する(4 スレッドで 30 分ほど。2.5 m の 2 ケースが大半)
#   make quick    40・20・10 m の 8 近傍と 4 近傍の 18 ケースだけ計算する(数分)
#   make clean    リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
# 計算の順(速い順)。dx5_r0 は param.txt そのもの
ROT	= r0 r22p5 r45
QUICK	= $(foreach d,dx40 dx20 dx10,$(foreach r,$(ROT),$(d)_$(r) $(d)_$(r)_4nb))
CASES	= $(QUICK) $(foreach r,$(ROT),dx5_$(r) dx5_$(r)_4nb) dx2p5_r0 dx2p5_r0_4nb

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: data_dx5_r0/z.txt

data_dx5_r0/z.txt: make_init.py param.txt
	python3 make_init.py

# 計算済み(result_<case>/D9999.bil がある)のケースは飛ばす。設定を変えたら make clean から
run: all
	@for c in $(CASES); do $(MAKE) --no-print-directory result_$$c/D9999.bil; done

quick: all
	@for c in $(QUICK); do $(MAKE) --no-print-directory result_$$c/D9999.bil; done

result_%/D9999.bil:
	@if [ "$*" = dx5_r0 ]; then p=param.txt; else p=param_$*.txt; fi; \
	    ./encflow $$p | tee Screen_$*.log

install: all

clean:
	rm -rf result_* data_*
	rm -f encflow encflow_mpi a.out Screen_*.log param_dx*.txt houses.txt

.PHONY: all links inputs run quick install clean
