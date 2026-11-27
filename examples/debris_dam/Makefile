# ENCflow/examples/debris_dam/Makefile
#   make          ../../bin/ の実行ファイルへのリンクと、全ケースの入力・設定(make_init.py)を作る
#   make quick    基本ケース・仮排水路と、堤体を置く系列の主な 4 ケースだけ計算する
#   make dams     堤体をはじめから置く系列(決壊の条件の比較)の 20 ケースを計算する
#   make run      32 ケースを計算する
#   make mixed    粒度の幅を持つ堤体(混合粒径と土石流の併用)の決壊と、決壊のあとの 3 時間の 10 ケースを計算する
#                 (比べる単一粒径の dam_ref・dam_d10cm と、make run に含まれない 8 ケース)
#   make perturb  結果の幅を見る 14 ケース(流入量だけを少し変える。基本ケース 6 本と、堤体を置く系列 8 本)を計算する
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

inputs: data_g10/z.txt

data_g10/z.txt: make_init.py param.txt
	python3 make_init.py

# 計算済み(result_<case>/Z9998.bil がある)のケースは飛ばす。設定を変えたら make clean から
run: all
	@for c in $$(python3 make_init.py list); do $(MAKE) --no-print-directory result_$$c/Z9998.bil; done

quick: all
	@for c in $$(python3 make_init.py quick); do $(MAKE) --no-print-directory result_$$c/Z9998.bil; done

dams: all
	@for c in $$(python3 make_init.py dams); do $(MAKE) --no-print-directory result_$$c/Z9998.bil; done

perturb: all
	@for c in $$(python3 make_init.py perturb); do $(MAKE) --no-print-directory result_$$c/Z9998.bil; done

# 決壊のあとの 6 ケースは、決壊の 4 ケース(dam_ref・mix_d3cm・dam_d10cm・mix_d10cm)が終わりに書く保存
# (save_<ケース>/)を読む
mixed: all
	@for c in $$(python3 make_init.py mixed); do $(MAKE) --no-print-directory result_$$c/Z9998.bil; done

result_%/Z9998.bil:
	@if [ "$*" = base ]; then p=param.txt; else p=param_$*.txt; fi; \
	    ./encflow $$p | tee Screen_$*.log

figs:
	python3 plot_results.py
	python3 plot_results.py en

install: all

clean:
	rm -rf result_* data_* save_*
	rm -f encflow encflow_mpi a.out Screen_*.log param_*.txt

.PHONY: all links inputs run quick dams perturb mixed figs install clean
