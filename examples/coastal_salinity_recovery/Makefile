# ENCflow/examples/coastal_salinity_recovery/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(gen_case.py の data_coast/)を作る
#   make run    8 つの計算を順につなぐ(1 スレッドで計 20 分ほど)
#                 spinup → flood_fast・flood_slow → rec_control・rec_fast_pump・rec_fast_stop・rec_slow_pump
#                 (+ 圧縮率の確かめ rec_fast_pump_m50)
#               段の受け渡しは保存状態(f_state_restore = 2)。保存先と読込元は同じディレクトリなので、
#               前の段の保存状態を次の段の名前でコピーしてから計算する
#   make clean  リンクと生成物を削除する

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

inputs: data_coast/z.txt

data_coast/z.txt: gen_case.py
	python3 gen_case.py

# $(call chain,計算の名前,受け取る保存状態)
define chain
	rm -rf save_$(1) && cp -r $(2) save_$(1)
	OMP_NUM_THREADS=1 ./encflow param_$(1).txt > Screen_$(1).log 2>&1
	@echo "done $(1)"
endef

run: all
	rm -rf save_spinup
	OMP_NUM_THREADS=1 ./encflow param_spinup.txt > Screen_spinup.log 2>&1
	@echo "done spinup"
	$(call chain,flood_fast,save_spinup)
	$(call chain,flood_slow,save_spinup)
	$(call chain,rec_control,save_spinup)
	$(call chain,rec_fast_pump,save_flood_fast)
	$(call chain,rec_fast_stop,save_flood_fast)
	$(call chain,rec_slow_pump,save_flood_slow)
	$(call chain,rec_fast_pump_m50,save_flood_fast)

install: all

clean:
	rm -rf result_* save_* data_coast
	rm -f encflow encflow_mpi Screen*.log

.PHONY: all links inputs run install clean
