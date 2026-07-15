module m_parallel
!=====================================================================
! 並列層: 逐次(OpenMP)版スタブ
!   m_parallel_mpi.f90 と同一のインターフェースを提供する。
!   両ファイルの公開手続きは常に一致させて保守すること。
!
! メッセージ出力の使い分け(MPI 版と共通のルール):
!   par_info(msg)  進捗・情報。標準出力に表示
!   par_warn(msg)  局所的な警告。標準エラーに表示(停止しない)
!   par_stop(msg)  決定的エラー(設定不正など)。表示して停止
!   par_abort(msg) 局所的な致命的エラー。表示して即時停止
!=====================================================================
   use, intrinsic :: iso_fortran_env, only: output_unit, error_unit
   implicit none
   private
   public :: par_init, par_finalize
   public :: par_info, par_warn, par_stop, par_abort
   public :: par_barrier
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

   subroutine par_info(msg)
      ! 進捗・情報メッセージ: 標準出力に表示
      character(*), intent(in) :: msg
      write(output_unit,'(a)') trim(msg)
      flush(output_unit)
   end subroutine par_info

   subroutine par_warn(msg)
      ! 局所的な警告: 標準エラーに表示(停止しない)
      character(*), intent(in) :: msg
      write(error_unit,'(2a)') 'WARNING: ', trim(msg)
      flush(error_unit)
   end subroutine par_warn

   subroutine par_stop(msg)
      ! 決定的エラー用: 表示して終了コード1で停止
      character(*), intent(in) :: msg
      write(error_unit,'(2a)') 'ERROR: ', trim(msg)
      flush(error_unit)
      stop 1
   end subroutine par_stop

   subroutine par_abort(msg)
      ! 局所エラー用: 表示して即時停止
      character(*), intent(in) :: msg
      write(error_unit,'(2a)') 'ABORT: ', trim(msg)
      flush(error_unit)
      error stop 1
   end subroutine par_abort

   subroutine par_barrier()
      ! 全ランク同期。逐次では何もしない。
   end subroutine par_barrier

   subroutine par_allreduce_min(val)
      ! 全ランク最小値(CFL の Δt 決定用)。逐次では何もしない。
      real, intent(inout) :: val
      if (val > 0.0) continue    ! 未使用引数警告の抑制
   end subroutine par_allreduce_min

end module m_parallel
