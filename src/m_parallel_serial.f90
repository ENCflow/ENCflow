module m_parallel
!=====================================================================
! 並列層: 逐次(OpenMP)版スタブ
!   m_parallel_mpi.f90 と同一のインターフェースを提供する。
!   両ファイルの公開手続きは常に一致させて保守すること。
!=====================================================================
   implicit none
   private
   public :: par_init, par_finalize, par_abort
   public :: par_allreduce_min
   public :: nrank, nproc, is_root

   integer, save :: nrank  = 0        ! 自ランク番号(逐次では常に0)
   integer, save :: nproc  = 1        ! 総ランク数(逐次では常に1)
   logical, save :: is_root = .true.  ! 入出力担当ランクか

contains

   subroutine par_init()
      ! 何もしない
   end subroutine par_init

   subroutine par_finalize()
      ! 何もしない
   end subroutine par_finalize

   subroutine par_abort(msg)
      character(*), intent(in) :: msg
      write(*,'(2a)') 'ABORT: ', trim(msg)
      error stop
   end subroutine par_abort

   subroutine par_allreduce_min(val)
      ! 全ランク最小値(CFL の Δt 決定用)。逐次では何もしない。
      real, intent(inout) :: val
      if (val > 0.0) continue
   end subroutine par_allreduce_min

end module m_parallel
