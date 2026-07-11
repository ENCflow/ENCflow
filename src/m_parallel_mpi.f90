module m_parallel
!=====================================================================
! 並列層: MPI 版
!   m_parallel_serial.f90 と同一のインターフェースを提供する。
!   両ファイルの公開手続きは常に一致させて保守すること。
!
! 注意:
!   - 本プロジェクトは -r8 等で既定 real を8バイトに昇格している
!     ため、MPI データ型は MPI_REAL でなく必ず MPI_REAL8 を使う。
!     (通信を書くときは下の MPI_WP を使うこと)
!   - OpenMP 併用のため MPI_Init_thread で FUNNELED を要求する。
!     (MPI 呼び出しはマスタースレッドのみ、が前提)
!=====================================================================
   use mpi_f08
   implicit none
   private
   public :: par_init, par_finalize, par_abort
   public :: par_allreduce_min
   public :: nrank, nproc, is_root
   public :: MPI_WP

   integer, save :: nrank  = 0
   integer, save :: nproc  = 1
   logical, save :: is_root = .true.

   ! 実数通信用データ型(既定 real = 8バイト前提)
   type(MPI_Datatype), parameter :: MPI_WP = MPI_REAL8

contains

   subroutine par_init()
      integer :: iprov
      call MPI_Init_thread(MPI_THREAD_FUNNELED, iprov)
      if (iprov < MPI_THREAD_FUNNELED) then
         write(*,*) 'ERROR: MPI thread support insufficient:', iprov
         call MPI_Abort(MPI_COMM_WORLD, 1)
      end if
      call MPI_Comm_rank(MPI_COMM_WORLD, nrank)
      call MPI_Comm_size(MPI_COMM_WORLD, nproc)
      is_root = (nrank == 0)
   end subroutine par_init

   subroutine par_finalize()
      call MPI_Finalize()
   end subroutine par_finalize

   subroutine par_abort(msg)
      character(*), intent(in) :: msg
      write(*,'(a,i0,2a)') 'ABORT (rank ', nrank, '): ', trim(msg)
      call MPI_Abort(MPI_COMM_WORLD, 1)
   end subroutine par_abort

   subroutine par_allreduce_min(val)
      ! 全ランク最小値(CFL の Δt 決定用)
      real, intent(inout) :: val
      call MPI_Allreduce(MPI_IN_PLACE, val, 1, MPI_WP, MPI_MIN, &
                         MPI_COMM_WORLD)
   end subroutine par_allreduce_min

end module m_parallel
