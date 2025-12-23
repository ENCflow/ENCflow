FRT	= ifx
#FFLAGS	= -g -fopenmp -warn all -fpe0 -O3 -ipo -fp-model fast -r8
#FFLAGS	= -g -fopenmp -fast -warn all -fpe0 -parallel -r8
#FFLAGS	= -g -fast -warn all -fpe0 -r8
#FFLAGS	= -pg -O3 -warn all -fpe0 -r8
FFLAGS	= -g -O0 -traceback -check all -warn all -fpe0 -r8
#LDFLAGS	

#FRT	= ifort
#FFLAGS  = -g -warn all -xHOST -O3 -ipo -no-prec-div -qopenmp -parallel -fpe0 -r8
#FFLAGS	= -g -O0 -traceback -check all -warn all -fpe0 -r8
#LDFLAGS	=

#FRT	= gfortran
#FFLAGS	= -g -fopenmp -Ofast -Wall -ffpe-trap=zero,overflow -fdefault-real-8
#FFLAGS	= -g -fopenmp -Ofast -Wall -ffpe-trap=invalid,zero,overflow -fdefault-real-8
#FFLAGS	= -g -Ofast -Wall -ffpe-trap=invalid,zero,overflow -fdefault-real-8
#FFLAGS	= -pg -Ofast -Wall -ffpe-trap=invalid,zero,overflow -fdefault-real-8
#FFLAGS	= -g -Og -fcheck=all -Wall -ffpe-trap=invalid,zero,overflow -fdefault-real-8 -Wno-conversion
#LDFLAGS	=

#FRT	= nvfortran
#FFLAGS	= -g -mp=multicore -Ofast -Minform=inform -Ktrap=fp -Mr8
#FFLAGS	= -g -Ofast -Minform=inform -Ktrap=fp -Mr8
#FFLAGS	= -pg -Ofast -Minform=inform -Ktrap=fp -Mr8
#FFLAGS	= -g -O0 -Mbounds -Mchkptr -Mchkstk -Minform=inform -Ktrap=fp -Mr8
#LDFLAGS	=

#FRT	= flang-20
#FRT	= flang-new-20
#FFLAGS	= -g -O3 -ffast-math -Werror -fdefault-real-8
#LDFLAGS	=


OBJS	= modify_sealand.o

all: a.out

a.out: $(OBJS)
	$(FRT) -o $@ $(FFLAGS) $(LDFLAGS) $(OBJS)

modify_sealand.o:


.SUFFIXES:
.SUFFIXES: .o .f90
.f90.o:
	$(FRT) -c $(FFLAGS) $<


clean:
	rm -f *.o *.mod *.smod a.out gmon.out *__genmod.*
