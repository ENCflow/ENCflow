# ENCflow/examples/mountain_valley/Makefile
#   make           ../../bin/ の実行ファイルへのリンクと入力(make_init.py)を作る
#   make run       主ケース V_a・V_b・V_c を順に計算する(V_c は V_b の save から再開。合わせて約 60 分)
#   make run-2m    解像度の確認 V_b2(Δx = 2 m。mpirun -np $(NP)。OpenMP 4 スレッドの 1 プロセスでは約 80 分)
#   make run-supp  補足の V_a_tp(約 20 分)と P_p・P_a(各約 6 分)
#   make clean     リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
NP	= 4

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: z_init.txt

z_init.txt: make_init.py
	python3 make_init.py

run: all
	./encflow param_V_a.txt 2>&1 | tee Screen_V_a.log
	./encflow param_V_b.txt 2>&1 | tee Screen_V_b.log
	rm -rf save_V_c && cp -r save_V_b save_V_c
	./encflow param_V_c.txt 2>&1 | tee Screen_V_c.log

run-2m: all
	mpirun -np $(NP) ./encflow_mpi param_V_b2.txt 2>&1 | tee Screen_V_b2.log

run-supp: all
	./encflow param_V_a_tp.txt 2>&1 | tee Screen_V_a_tp.log
	./encflow param_P_p.txt 2>&1 | tee Screen_P_p.log
	./encflow param_P_a.txt 2>&1 | tee Screen_P_a.log

install: all

clean:
	rm -rf result result_* save save_*
	rm -f encflow encflow_mpi a.out Screen.log Screen_*.log analysis*.txt
	rm -f z_init*.txt h_init*.txt sd_zero*.txt up_base*.txt up_drop*.txt wthr_hill*.txt rock_base*.txt p_*.txt

.PHONY: all links inputs run run-2m run-supp install clean
