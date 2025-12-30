FRT	= ifx
#FFLAGS	= -g -fast -warn all -fpe0
FFLAGS	= -g -O2 -warn all -fpe0
#FFLAGS	= -g -O0 -traceback -check all -warn all -fpe0
#LDFLAGS	

#FRT	= ifort
#FFLAGS  = -g -warn all -xHOST -O3 -ipo -no-prec-div -qopenmp -parallel -fpe0
#FFLAGS	= -g -O0 -traceback -check all -warn all -fpe0
#LDFLAGS	=

#FRT	= gfortran
#FFLAGS	= -g -Ofast -Wall -ffpe-trap=invalid,zero,overflow
#FFLAGS	= -g -Og -fcheck=all -Wall -ffpe-trap=invalid,zero,overflow -Wno-conversion
#LDFLAGS	=

#FRT	= nvfortran
#FFLAGS	= -g -Ofast -Minform=inform -Ktrap=fp
#FFLAGS	= -g -O0 -Mbounds -Mchkptr -Mchkstk -Minform=inform -Ktrap=fp
#LDFLAGS	=

#FRT	= flang-20
#FRT	= flang-new-20
#FFLAGS	= -g -O3 -ffast-math -Werror
#LDFLAGS	=


#OBJS	= mkdowndir.o chkdowndir.o calcarea.o pickuparea.o

all: mkdowndir chkdowndir calcarea pickuparea

mkdowndir: mkdowndir.o
	$(FRT) -o $@ $(FFLAGS) $(LDFLAGS) mkdowndir.o

chkdowndir: chkdowndir.o
	$(FRT) -o $@ $(FFLAGS) $(LDFLAGS) chkdowndir.o

calcarea: calcarea.o
	$(FRT) -o $@ $(FFLAGS) $(LDFLAGS) calcarea.o

pickuparea: pickuparea.o
	$(FRT) -o $@ $(FFLAGS) $(LDFLAGS) pickuparea.o

#a.out: $(OBJS)
#	$(FRT) -o $@ $(FFLAGS) $(LDFLAGS) $(OBJS)


.SUFFIXES:
.SUFFIXES: .o .f90
.f90.o:
	$(FRT) -c $(FFLAGS) $<


clean:
	rm -f *.o *.mod *.smod a.out gmon.out *__genmod.* mkdowndir chkdowndir calcarea pickuparea
