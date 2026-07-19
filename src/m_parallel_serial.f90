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
!
! 領域分割情報 dcp(MPI 版と共通のルール):
!   - par_decomp_init(nx, ny) で設定する(格子サイズ確定後、
!     m_geoinfo_init の直後に呼ぶこと)。逐次では常に全域を担当する。
!   - 各モジュールは use m_parallel, only: dcp で直接参照してよい
!     (protected 属性により変更は本モジュール内に限定される)
!   - 計算カーネルには dcp を見せず、範囲(js, je 等)を引数で渡す
!=====================================================================
   use, intrinsic :: iso_fortran_env, only: output_unit, error_unit
   implicit none
   private
   public :: par_init, par_finalize
   public :: par_decomp_init
   public :: par_info, par_warn, par_stop, par_abort
   public :: par_barrier
   public :: par_allreduce_min
   public :: nrank, nproc, is_root
   public :: t_decomp, dcp

   integer, protected, save :: nrank  = 0        ! 自ランク番号(逐次では常に0)
   integer, protected, save :: nproc  = 1        ! 総ランク数(逐次では常に1)
   logical, protected, save :: is_root = .true.  ! 入出力担当ランクか

   ! 領域分割情報(逐次では常に全域。型定義は MPI 版と一致させること)
   type :: t_decomp
      integer :: nx_g = 0        ! 全領域サイズ x(参考保持)
      integer :: ny_g = 0        ! 全領域サイズ y(参考保持)
      integer :: js = 1          ! 自ランク担当範囲の開始 j
      integer :: je = 0          ! 自ランク担当範囲の終了 j
      integer :: jsh = 1         ! ハロ込み範囲の開始 j
      integer :: jeh = 0         ! ハロ込み範囲の終了 j
      integer :: rank_n = -1     ! j+側の隣接ランク(なければ負)
      integer :: rank_s = -1     ! j-側の隣接ランク(なければ負)
   end type t_decomp

   type(t_decomp), protected, save :: dcp

contains

   subroutine par_init()
      ! 何もしない
   end subroutine par_init

   subroutine par_decomp_init(nx, ny)
      ! 領域分割の決定。逐次では全域を担当範囲とする。
      integer, intent(in) :: nx, ny
      dcp%nx_g = nx
      dcp%ny_g = ny
      dcp%js  = 1
      dcp%je  = ny
      dcp%jsh = 1
      dcp%jeh = ny
      dcp%rank_n = -1
      dcp%rank_s = -1
   end subroutine par_decomp_init

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
