module m_parallel
!=====================================================================
! 並列層: MPI 版
!   m_parallel_serial.f90 と同一のインターフェースを提供する。
!   両ファイルの公開手続きは常に一致させて保守すること。
!
! メッセージ出力の使い分け:
!   par_info(msg)  進捗・情報。ランク0のみ標準出力に表示
!   par_warn(msg)  局所的な警告。検出したランクがランク番号付きで
!                  標準エラーに表示(停止しない)
!   par_stop(msg)  決定的エラー(設定不正など全ランクが同時に検出
!                  するもの)。必ず全ランクが揃って呼ぶこと
!                  (collective)。ランク0が表示して正常経路で全体停止
!   par_abort(msg) 局所的な致命的エラー。検出したランクだけが呼んで
!                  よい。ランク番号付きで表示して即時に全体強制終了
!
! 領域分割情報 dcp:
!   - par_decomp_init(nx, ny) で設定する(格子サイズ確定後、
!     m_geoinfo_init の直後に呼ぶこと)
!   - 各モジュールは use m_parallel, only: dcp で直接参照してよい
!     (protected 属性により変更は本モジュール内に限定される)
!   - 計算カーネルには dcp を見せず、範囲(js, je 等)を引数で渡す
!     (dcp の直接参照はフェーズの入口まで)
!
! 注意:
!   - 本プロジェクトは -r8 等で既定 real を8バイトに昇格している
!     ため、MPI データ型は MPI_REAL でなく必ず MPI_REAL8 を使う。
!     (通信を書くときは下の MPI_WP を使うこと)
!   - OpenMP 併用のため MPI_Init_thread で FUNNELED を要求する。
!     (MPI 呼び出しはマスタースレッドのみ、が前提)
!   - エラー・警告を error_unit に出すのは意図的(tee で作る
!     Log.txt =回帰テストの比較対象= に混入させないため)
!=====================================================================
   use mpi_f08
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
   public :: MPI_WP

   integer, protected, save :: nrank  = 0
   integer, protected, save :: nproc  = 1
   logical, protected, save :: is_root = .true.

   ! 領域分割情報(j方向分割。ブロック分割に拡張する場合は
   ! i方向成分を追加し、serial 版と同時に改定すること)
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

   ! 実数通信用データ型(既定 real = 8バイト前提)
   type(MPI_Datatype), parameter :: MPI_WP = MPI_REAL8

contains

   subroutine par_init()
      integer :: iprov
      call MPI_Init_thread(MPI_THREAD_FUNNELED, iprov)
      if (iprov < MPI_THREAD_FUNNELED) then
         write(error_unit,'(a,i0)') &
            'ERROR: MPI thread support insufficient: ', iprov
         flush(error_unit)
         call MPI_Abort(MPI_COMM_WORLD, 1)
      end if
      call MPI_Comm_rank(MPI_COMM_WORLD, nrank)
      call MPI_Comm_size(MPI_COMM_WORLD, nproc)
      is_root = (nrank == 0)
   end subroutine par_init

   subroutine par_decomp_init(nx, ny)
      ! 領域分割の決定。格子サイズ確定後(m_geoinfo_init の直後)に
      ! 全ランクが揃って呼ぶこと(collective)。
      !
      ! 現段階(冗長計算)は全ランクが全域を担当する。
      ! TODO: 分割実装時にここで j 方向の範囲・ハロ・隣接ランクを
      !       計算する(ランク数不変のビット一致検証を回帰テストで)。
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
      call MPI_Finalize()
   end subroutine par_finalize

   subroutine par_info(msg)
      ! 進捗・情報メッセージ: ランク0のみ標準出力に表示
      character(*), intent(in) :: msg
      if (is_root) then
         write(output_unit,'(a)') trim(msg)
         flush(output_unit)
      end if
   end subroutine par_info

   subroutine par_warn(msg)
      ! 局所的な警告: 検出したランクがランク番号付きで表示(停止しない)
      character(*), intent(in) :: msg
      write(error_unit,'(a,i0,2a)') 'WARNING (rank ', nrank, '): ', trim(msg)
      flush(error_unit)
   end subroutine par_warn

   subroutine par_stop(msg)
      ! 決定的エラー用: 全ランクが同時に検出する種類のエラー(設定関連)。
      ! 必ず全ランクが揃って呼ぶこと(collective)。
      ! ランク0が表示し、finalize を通して終了コード1で停止する。
      character(*), intent(in) :: msg
      if (is_root) then
         write(error_unit,'(2a)') 'ERROR: ', trim(msg)
         flush(error_unit)
      end if
      call MPI_Barrier(MPI_COMM_WORLD)
      call MPI_Finalize()
      stop 1
   end subroutine par_stop

   subroutine par_abort(msg)
      ! 局所エラー用: 検出したランクだけが呼んでよい。
      ! ランク番号付きで表示して全ランクを即時強制終了する。
      character(*), intent(in) :: msg
      write(error_unit,'(a,i0,2a)') 'ABORT (rank ', nrank, '): ', trim(msg)
      flush(error_unit)
      call MPI_Abort(MPI_COMM_WORLD, 1)
   end subroutine par_abort

   subroutine par_barrier()
      ! 全ランク同期(通常の計算では不要。時間計測・デバッグ用)
      call MPI_Barrier(MPI_COMM_WORLD)
   end subroutine par_barrier

   subroutine par_allreduce_min(val)
      ! 全ランク最小値(CFL の Δt 決定用)
      real, intent(inout) :: val
      call MPI_Allreduce(MPI_IN_PLACE, val, 1, MPI_WP, MPI_MIN, &
                         MPI_COMM_WORLD)
   end subroutine par_allreduce_min

end module m_parallel
