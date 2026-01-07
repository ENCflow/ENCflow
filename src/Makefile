FRT	= ifx
FFLAGS	= -g -fopenmp -warn all -fpe0 -O3 -ipo -fp-model fast -r8
#FFLAGS	= -g -fopenmp -fast -warn all -fpe0 -parallel -r8
#FFLAGS	= -g -fast -warn all -fpe0 -r8
#FFLAGS	= -pg -O3 -warn all -fpe0 -r8
#FFLAGS	= -g -O0 -traceback -check all -warn all -fpe0 -r8
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


OBJS	= main.o m_main.o m_sysparam.o m_geoinfo.o m_precip.o m_tide.o m_boundary.o \
	  m_state.o  m_record.o m_swflow.o m_swflow_enc.o m_swflow_stg.o \
	  list_sysparam.o list_geoinfo.o list_precip.o \
	  list_initial.o list_record.o list_tide.o list_boundary.o list_enc.o \
	  m_ffactor.o user_geoinfo.o user_initial.o sysdep_util.o m_fileio.o m_util.o

# nvfortean requiers all objectifiles
OBJS_rerec	= rerecord.o m_record.o list_record.o m_sysparam.o list_sysparam.o \
		  m_geoinfo.o list_geoinfo.o m_state.o list_initial.o \
		  user_geoinfo.o user_initial.o \
		  m_fileio.o sysdep_util.o m_util.o
#
# nvfortean requiers all objectifiles
OBJS_rmdepress_river	= rmdepress_river.o list_sysparam.o m_sysparam.o \
		  list_geoinfo.o m_geoinfo.o user_geoinfo.o m_fileio.o sysdep_util.o m_util.o

all: a.out rerecord rmdepress_river

a.out: $(OBJS)
	$(FRT) -o $@ $(FFLAGS) $(LDFLAGS) $(OBJS)

rerecord: $(OBJS_rerec)
	$(FRT) -o $@ $(FFLAGS) $(LDFLAGS) $(OBJS_rerec)

rmdepress_river: $(OBJS_rmdepress_river)
	$(FRT) -o $@ $(FFLAGS) $(LDFLAGS) $(OBJS_rmdepress_river)

main.o: m_main.o
m_main.o: m_sysparam.o m_geoinfo.o m_precip.o m_tide.o m_boundary.o m_state.o \
	m_record.o m_swflow.o m_fileio.o sysdep_util.o
m_sysparam.o: list_sysparam.o m_util.o
m_geoinfo.o: m_sysparam.o list_geoinfo.o m_fileio.o
m_precip.o: m_sysparam.o list_precip.o m_state.o m_geoinfo.o m_fileio.o
m_tide.o: m_sysparam.o list_tide.o m_geoinfo.o
m_boundary.o: m_sysparam.o m_geoinfo.o
m_state.o: m_sysparam.o m_geoinfo.o list_initial.o
m_record.o: m_sysparam.o list_record.o m_geoinfo.o m_state.o
m_swflow.o: m_sysparam.o m_geoinfo.o m_state.o m_swflow_enc.o m_swflow_stg.o
m_swflow_enc.o: m_sysparam.o list_enc.o m_geoinfo.o m_precip.o m_state.o m_ffactor.o
m_swflow_stg.o: m_sysparam.o m_geoinfo.o m_precip.o m_state.o
list_sysparam.o:
list_geoinfo.o: m_sysparam.o
list_precip.o: m_sysparam.o
list_tide.o: m_sysparam.o
list_initial.o: m_sysparam.o
list_record.o: m_sysparam.o
list_boundary.o: m_sysparam.o
list_enc.o: m_sysparam.o
user_geoinfo.o: m_sysparam.o m_geoinfo.o
user_initial.o: m_sysparam.o m_state.o m_geoinfo.o
m_fileio.o: m_sysparam.o sysdep_util.o
m_ffactor.o:
m_util.o:
sysdep_util.o: m_sysparam.o
rerecord.o: m_record.o m_geoinfo.o m_sysparam.o m_fileio.o
rmdepress_river.o: m_geoinfo.o m_sysparam.o m_fileio.o


.SUFFIXES:
.SUFFIXES: .o .f90
.f90.o:
	$(FRT) -c $(FFLAGS) $<


clean:
	rm -f *.o *.mod *.smod a.out rerecord rmdepress_river gmon.out *__genmod.*

install: a.out rerecord
	cp -f a.out rerecord rmdepress_river ../../bin
