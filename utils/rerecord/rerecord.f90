!-----------------------------------------------------------------------
! 流量ファイルからプローブ・フラックスを計測する
! "rerecord"
!-----------------------------------------------------------------------
!
! 任意の時刻の流量分布ファイル QXXXX.bil に対して、
! list_record で指定したプローブとフラックス計測を実施する。
!
! フラックスの計算で流向の情報を使うので QdXXXX.bil も必要となる。
! ただし流向はあまり変化しないことが予想されるので、
! 流量と同時刻でなくてもよく、特定の時刻のものを
! 使いまわしても恐らく問題ない。
!
! 実行時の引数は以下の3つ
!   1. 計算実行時のパラメータファイル
!   2. 流向データファイル
!   3. 計測したい流量ファイル
!
!  $ ./rerecord parameterfile.txt QdXXXX.bil QXXXX.bil"
!
! 結果の出力は、probeXX_re.csv, fluxXX_re.csv, summary_re.csv
! いずれも、中身は最小限のものである。
!
! プローブの地点の水深を事後に知りたい場合、流量ファイルの代わりに
! 水深ファイルを指定すれば probeXX_csv の"流量"欄に水深が出力されるが、
! それ以外は無意味な値となる。
!
!-----------------------------------------------------------------------
module m_rerecord_main
  use m_sysparam
  use m_geoinfo
  use m_state
  use m_record
  use m_fileio
  implicit none
  private

  public :: m_rerecord_all

contains
!-----------------------------------------------------------------------
subroutine m_rerecord_all(fn_sysparam, fn_qqdir, fn_qq)
  character(len=*) :: fn_sysparam, fn_qqdir, fn_qq
  type(t_sysparam) :: p
  type(t_geoinfo) :: g
  type(t_state) :: s
  type(t_record) :: r

  call m_sysparam_init(p, fn_sysparam)    ! sysparam を初期化
  p%outfn_suffix = trim(p%outfn_suffix)//"_re"
  call m_geoinfo_init(g, p)               ! geoinfo を初期化

  ! 最小限の状態変数を設定
  s%t = 0.0
  allocate(s%h(1:g%nx,1:g%ny), source=0.0)
  allocate(s%u(1:g%nx,1:g%ny), source=0.0)
  allocate(s%v(1:g%nx,1:g%ny), source=0.0)
  allocate(s%m(1:g%nx,1:g%ny), source=0.0)
  allocate(s%n(1:g%nx,1:g%ny), source=0.0)
  allocate(s%vv(1:g%nx,1:g%ny), source=0.0)
  allocate(s%qq(1:g%nx,1:g%ny), source=0.0)
  allocate(s%qqdir(1:g%nx,1:g%ny), source=0.0)
  s%initialized = .true.

  ! 条件を画面表示
  print *, "nx =", g%nx
  print *, "ny =", g%ny

  ! モジュールの初期化
  call m_record_init(r, p, g)

  ! データの読み込み
  print *, "reading discharge direction from ", trim(fn_qqdir)
  call fileio_read_matrix(fn_qqdir, g%nx, g%ny, s%qqdir, e_fmt_bil)
  print *, "reading discharge from ", trim(fn_qq)
  call fileio_read_matrix(fn_qq, g%nx, g%ny, s%qq, e_fmt_bil)

  ! 流量の計算
  block
  integer :: i, j
  do j = 1, g%ny
    do i = 1, g%nx
      s%m(i,j) = s%qq(i,j) * cos(s%qqdir(i,j))
      s%n(i,j) = s%qq(i,j) * sin(s%qqdir(i,j))
    end do
  end do
  end block

  ! レコードの出力
  call m_record_probe(r, p, s)
  call m_record_flux(r, p, s)
  print *, "write to probeXX_re.csv"
  print *, "write to fluxXX_re.csv"

  ! 最大流量の一覧を出力
  print *, "write to summary_re.csv"
  call m_record_summary(r, p)

  ! 終了
  call m_record_dispose(r)
  deallocate(g%x)
  deallocate(g%z)
  deallocate(s%h)
  deallocate(s%u)
  deallocate(s%v)
  deallocate(s%m)
  deallocate(s%n)
  deallocate(s%vv)
  deallocate(s%qq)
  deallocate(s%qqdir)
  print *, "Done."

end subroutine
end module


!=======================================================================
!=======================================================================
program rerecord
  use m_rerecord_main, only : m_rerecord_all
  implicit none
  character(len=256) :: fn_sysparam, fn_qqdir, fn_qq

  call get_fn(fn_sysparam, fn_qqdir, fn_qq)
  call m_rerecord_all(fn_sysparam, fn_qqdir, fn_qq)

contains
!-----------------------------------------------------------------------
! コマンドライン引数からファイル名を取得する
!-----------------------------------------------------------------------
subroutine get_fn(fn_sysparam, fn_qqdir, fn_qq)
  character(len=*) :: fn_sysparam, fn_qqdir, fn_qq

  ! コマンドライン引数の文字列を保存する構造体の宣言
  !  可変長文字列の配列が直接作れないため構造体の配列を利用
  type :: arguments
    character(:), allocatable :: v           ! 無指定文字長（可変長）文字列変数vを要素に持つ
  end type

  ! コマンドライン引数の数と文字列
  integer :: argc
  type(arguments), allocatable :: arg(:)

  
  !--- コマンドライン引数取得の準備 ---
  argc = command_argument_count()            ! 引数の数を取得
  allocate(arg(0:argc))                      ! 構造体のメモリを確保
  !print *, argc

  !--- コマンドライン引数を取得 ---
  get_arguments: block
    integer :: i, l
    do i = 0, argc
      call get_command_argument(number=i, length=l)         ! i番目の引数の長さを取得
      allocate(character(l) :: arg(i)%v)                    ! 構造体中の文字列用メモリを確保
      call get_command_argument(number=i, value=arg(i)%v)   ! 引数の文字列を取得
      !print *, i, arg(i)%v
    end do
  end block get_arguments

  if (argc >= 3) then
    fn_sysparam = arg(1)%v
    fn_qqdir = arg(2)%v
    fn_qq = arg(3)%v
  else
    print ('(a, a, a)'), "usage: ", arg(0)%v, " parameterfile.txt QdXXXX.bil QXXXX.bil"
    stop
  end if
end subroutine

end program
