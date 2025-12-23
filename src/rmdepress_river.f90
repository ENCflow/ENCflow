!----------------------------------------------------------------------
! 河道セルの窪地を除去する
! "rmdepress_river"
!----------------------------------------------------------------------
!
! このプログラムは、 河道床の標高が下流に向かい単調減少となるよう、
! 準備計算で求めた流下方向にしたがって河道床を掘削することで窪地を除去する。
! 窪地の低い所が真の標高で高い所が離散化誤差である、との仮定に基づき、
! 窪地を埋めることはせず掘削・開削のみを行う。
!
! 実行時の引数は以下の二つ
!   1. 準備計算のときのシステムパラメータファイル
!   2. 流下方向の基準とする全流下方向フラグファイル
!
! $ ./rmdepress_river parameterfile DdaXXXX.bil
!
! 実行時には準備計算時の入力データが全て揃っている必要がある。
! しかし計算結果は流下方向を除き不要であり DdaXXXX.bil だけあればよい。
! 全流下方向の代わりに卓越流下方向 DddXXXX.bil を指定した場合でも
! 窪地は除去されるが、幅の広い河道において澪筋以外の彫りが浅くなる。
!
! 流下方向フラグファイルは、準備計算時にパラメータファイルの
! list_sysparam の中で以下のオプションを追加することで出力される。
!   -----------------------------------------------------------------
!   f_out_ddd = 1            ! ファイル出力(卓越流下方向Ddd0001)
!   f_out_dda = 1            ! ファイル出力(全流下方向Dda0001)
!   -----------------------------------------------------------------
!       ※ 他の変数の出力については list_sysparam.f90 を参照
!
! rmdepress_riveの出力ファイルは以下の二つ
!   1. 窪地除去後の標高データ Z0000.bil
!   2. 窪地除去のために掘削した河道床の深さZd0000.bil
!
! 下流に向かって掘削した区間は、水平に掘り進めるため真っ平になってしまう。
! 現実世界では下り勾配のはずなので、掘削開始点から終了点までの間を、
! 一様な下り勾配となる様にスムージングをかける。
! このとき、掘削区間同士の合流がある場合に逆勾配が生じてしまうため、
! スムージング前の標高以上には修正されないよう制限をかけている。
!
! ちなみに水平に掘る理由は、現実の勾配が不明であることと、
! 湖などで渦が発生し流向がループしている場合に無限ループとなり、
! 際限なく掘り込まれてしまうことを避けるためである。
!
!----------------------------------------------------------------------
!
! 準備計算では河道に窪地が無い場合の自然な流向を求める。
! そのために、以下の条件を満たす必要がある。
!
!   1. 窪地の無い河道での流れ
!   2. 全ての河道で十分な水量
!   3. 自然な流向
!
! 窪地を除去するために、事前に窪地の無い地形を用いた計算をする、
! というのは一見、自己矛盾しているように感じられるかもしれない。
! しかし、窪地を「埋めた」地形で計算した流向にしたがって、
! 窪地の原因となっている逆勾配を「削る」のがこの手法のアイディアである。
! この手法では、河道内の窪地を埋めても河道外に水が溢れ出ないことが重要である。
! したがって、河道セルが十分に深く彫り込まれている必要がある。
!
! 条件1、河道の窪地を埋めるために、初期条件設定の list_initial の中に、
! 次のパラメータを追加する。
!   ---------------------------------------------------------------------------
!   f_fill_depres = 3    ! 窪地満水 (0:無効, 1:有効, 2:河道のみ, 3:河道床上げ)
!   ---------------------------------------------------------------------------
! この値が0の場合は、全ての場所で初期水深ゼロで計算が始まる。(デフォルト)
! この値が1の場合は、全ての窪地を満水にした状態で計算が始まる。
! この値が2の場合は、河道の窪地を満水にした状態で計算が始まる。
! この値が3の場合は、河道の窪地を全て埋めた標高データで初期水深ゼロとする。
! 窪地の中を水で満たした状態で多量の水を流した場合、窪地部分で波や逆流など、
! 好ましくない流向が生じるケースがあるため、河道床自体を上げる3を指定する。
! ちなみに、値を1として計算したときの初期水深H0000.bilが、
! その計算で指定した標高データの窪地の水深に相当する。
!
! 条件2、河道に十分な水量を流すために、以下の条件を設定する。
! ・粗度係数は現実の値である必要はないので、小さめの値を与えて流出を早める。
!   そのために地理条件 list_geoinfo の中で以下のパラメータを設定、追加する。
!   現実の粗度係数マップを用いてもよいが、流出が遅くなるため長めの計算時間が必要。
!     ---------------------------------------------------------------------------
!     f_rntype = 0    ! 粗度係数タイプ (0:固定値, 1:ファイル, 2:土地利用から計算)
!     rn0 = 0.012     ! 粗度係数固定値
!     ---------------------------------------------------------------------------
! ・長大河川の下流端まで十分満水にするために、以下の降雨を与える。
!     ---------------------------------------------------------------------------
!     ! 降水データのタイプ (0:降水なし, 1:設定時系列, 2:ファイル×設定倍率)
!     prtype = 1
!     ! 降水の時系列 (時刻(min), 雨量強度(mm/h)) for prtype=1
!     prval(:,1) =    0,   25
!     ---------------------------------------------------------------------------
!   ここでprvalに時刻0の値だけ指定して、終了時刻を指定しない場合は、
!   計算の最後までこの降雨強度が維持される。
!   総計算時間は最も長い河川の下流端までの到達時間以上が望ましいが、
!   絶対的な条件ではない。全国計算の場合、48時間程度で十分かと思われる。
!   降雨強度を大きくすると時間刻みを大きくできず計算速度が遅くなり、
!   降雨強度を小さくすると流出が遅くなり総計算時間を長くしなければならない、
!   というジレンマがある。降雨強度が小さすぎると流れが不自然になるので、
!   それなりに大きな値でじゃぶじゃぶ流した方がよい。
!
! 条件3、河道の縦断・横断方向の勾配のムラを減らすために局所慣性方程式を用いる。
! 移流項を入れると、勾配や川幅の変化する場所や、幅の広い河川などで、
! 望ましくない方向に流れるため、純粋に水面勾配のみで流下方向が決まる
! 局所慣性方程式の方が自然な掘削結果が得られる。
!
!======================================================================
!======================================================================
module m_rmdepress_river
  use m_sysparam
  use m_geoinfo
  use m_fileio
  implicit none
  private

  real, parameter :: s0 = 0.                 ! 掘削時の勾配(0でないと渦で無限ループに)
  integer, parameter :: ncycle = 1000        ! 掘削ループの最大数
  integer, parameter :: ncycle2 = 2000       ! 平均化ループの最大数

  integer, parameter :: din(0:8) = [ 0, -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(0:8) = [ 0, -1, -1, -1,  0,  0,  1,  1,  1]

  public m_main_all
contains
!======================================================================
!======================================================================
subroutine m_main_all(fn_sysparam, fn_ddir)
  character(len=*), intent(in) :: fn_sysparam
  character(len=*), intent(in) :: fn_ddir
  type(t_sysparam) :: p
  type(t_geoinfo) :: g

  call m_sysparam_init(p, fn_sysparam)    ! sysparam を初期化
  call m_geoinfo_init(g, p)               ! geoinfo を初期化

  call do_all(p, g, fn_ddir)

  call m_geoinfo_dispose(g)
  call m_sysparam_dispose(p)
end subroutine

!----------------------------------------------------------------------
! 作業本体
!----------------------------------------------------------------------
subroutine do_all(p, g, fn_ddir)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  character(len=*), intent(in) :: fn_ddir
  integer :: ddir(1:p%nx,1:p%ny)     ! douwstream direction (1~8)
  integer :: irm(1:p%nx,1:p%ny)      ! river mouth mask
  integer :: icv(1:p%nx,1:p%ny)      ! carved mark
  integer :: ism(1:p%nx,1:p%ny)      ! smoothing target
  real :: z(1:p%nx,1:p%ny)           ! modified elevation
  real :: dz(1:p%nx,1:p%ny)          ! carved depth


  call fileio_read_matrix_int(fn_ddir, p%nx, p%ny, ddir, e_fmt_bil)
  call check_rivermouth(p, g, irm)
  call carve(p, g, irm, ddir, icv, ism, z)
  call smooth(p, g, irm, icv, ism, z)
  call smooth2(p, g, irm, ddir, z)
  dz(:,:) = g%z(:,:) - z(:,:)

  !call fileio_write_matrix_int("RM.bil", g%nx, g%ny, irm, 2, 0)
  call fileio_write_matrix_real("Z0000.bil", g%nx, g%ny, z, e_fmt_bil, e_cmp_off)
  call fileio_write_matrix_real("Zd0000.bil", g%nx, g%ny, dz, e_fmt_bil, e_cmp_off)
  
end subroutine

!----------------------------------------------------------------------
! 流向に対して逆勾配のセルを掘削
!----------------------------------------------------------------------
subroutine carve(p, g, irm, ddir, icv, ism, z)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: irm(1:p%nx,1:p%ny)
  integer, intent(in) :: ddir(1:p%nx,1:p%ny)
  integer, intent(inout) :: icv(1:p%nx,1:p%ny)
  integer, intent(inout) :: ism(1:p%nx,1:p%ny)
  real, intent(inout) :: z(1:p%nx,1:p%ny)
  integer :: i, j, k, l
  integer :: in, jn
  integer :: nc
  real :: dr(0:8)
  real, parameter :: rdz(0:8) = [ 0., sqrt(2.), 1., sqrt(2.), 1., 1., sqrt(2.), 1., sqrt(2.)]

  do k = 1, 8
    dr(k) = sqrt((p%dx * din(k)**2)**2 + (p%dy * djn(k)**2)**2)
  end do

  z(:,:) = g%z(:,:)
  icv(:,:) = 0
  ism(:,:) = 0

  do l = 1, ncycle
    nc = 0
    do j = g%wy(1), g%wy(2)
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) < 1) cycle                   ! 領域外は無視
        if (g%rw(i,j) < 1) cycle                  ! 河道以外は無視
        if (irm(i,j) > 0) cycle                   ! 河口は無視
        do k = 1, 8                               ! 八近傍全てをチェック
          if (iand(ddir(i,j), 2**k) == 0) cycle   ! k方向に流出が無い場合はスキップ
          in = i + din(k)                         ! 下流側セルのインデックス
          jn = j + djn(k)                         ! 下流側セルのインデックス
          if (g%rw(in,jn) < 1) cycle              ! 河道以外の行き先は無視
          if (z(i,j) < z(in,jn)) then             ! 下流側セルの標高の方が高い場合は
            z(in,jn) = z(i,j) - dr(k) * s0        ! 下流側セルの標高を自セルよりも下げる
            icv(in,jn) = 1                        ! 相手セルは掘削済み
            ism(in,jn) = 1                        ! 相手セルは平均化対象
            ism(i,j) = 1                          ! 自セルも平均化対象
            nc = nc + 1
          else if (icv(i,j) > 0) then             ! 自セルが掘削済みで相手が下方なら掘削明け
            ism(in,jn) = 1                        ! 相手セルは平均化対象
          end if
        end do
      end do
    end do
    print *, "carving", l, nc
    if (nc == 0) exit
  end do


end subroutine


!----------------------------------------------------------------------
! 掘削されたセルのスムージング
!----------------------------------------------------------------------
subroutine smooth(p, g, irm, icv, ism, z)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: irm(1:p%nx,1:p%ny)
  integer, intent(in) :: icv(1:p%nx,1:p%ny)
  integer, intent(in) :: ism(1:p%nx,1:p%ny)
  real, intent(inout) :: z(1:p%nx,1:p%ny)
  real :: z0(1:p%nx,1:p%ny)
  real :: z1(1:p%nx,1:p%ny)
  integer :: i, j, k, l
  integer :: in, jn
  integer :: n
  integer :: ns
  real :: zz, sz
  real, parameter :: eps = 1.e-3

  z0(:,:) = z(:,:)
  z1(:,:) = z(:,:)

  do l = 1, ncycle2
    ns = 0
    do j = g%wy(1), g%wy(2)
      do i = g%wx(1,j), g%wx(2,j)
        if (g%x(i,j) < 1) cycle               ! 領域外は無視
        if (g%rw(i,j) < 1) cycle              ! 河道以外は無視
        if (irm(i,j) > 0) cycle               ! 河口は無視
        if (icv(i,j) < 1) cycle               ! 掘削されていないセルは無視
        n = 1
        sz = z(i,j)
        do k = 1, 8
          in = i + din(k)                     ! 近傍セルのインデックス
          jn = j + djn(k)                     ! 近傍セルのインデックス
          if (g%rw(in,jn) < 1) cycle          ! 河道以外の近傍は無視
          if (ism(i,j) < 1) cycle             ! 平均化対象セル以外の近傍は無視
                                              !   対象は、掘削セル、掘削元セル、掘削明けセル
          sz = sz + z(in,jn)
          n = n + 1
        end do
        zz = min(sz / n, z0(i,j))             ! 平均化するとき最初より上昇はさせない
                                              !   この制限は掘削河川同士の合流点で必要となる
        if (abs(zz - z1(i,j)) > eps) then     ! 収束判定
          z1(i,j) = sz / n
          ns = ns + 1
        end if
      end do
    end do
    z(:,:) = z1(:,:)
    print *, "smoothing", l, ns
    if (ns == 0) exit
  end do

end subroutine


!----------------------------------------------------------------------
! 仕上げのスムージング
!----------------------------------------------------------------------
subroutine smooth2(p, g, irm, ddir, z)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  integer, intent(in) :: irm(1:p%nx,1:p%ny)
  integer, intent(in) :: ddir(1:p%nx,1:p%ny)
  real, intent(inout) :: z(1:p%nx,1:p%ny)
  real :: z1(1:p%nx,1:p%ny)
  integer :: i, j, k
  integer :: in, jn
  integer :: n
  real :: sum

  z1(:,:) = z(:,:)

  do j = 2, p%ny-1
    do i = 2, p%nx-1
      if (g%x(i,j) < 1) cycle               ! 領域外は無視
      if (g%rw(i,j) < 1) cycle              ! 河道以外は無視
      if (irm(i,j) > 0) cycle               ! 河口は無視
      n = 1
      sum = z(i,j)
      do k = 1, 8
        in = i + din(k)                     ! 近傍セルのインデックス
        jn = j + djn(k)                     ! 近傍セルのインデックス
        if (g%rw(in,jn) < 1) cycle          ! 河道以外の近傍は無視
        if (iand(ddir(i,j), 2**k) == 0) cycle   ! k方向に流出が無い場合はスキップ
        sum = sum + z(in,jn)
        n = n + 1
      end do
      z1(i,j) = sum / n
    end do
  end do
  
  z(:,:) = z1(:,:)

end subroutine




!----------------------------------------------------------------------
! 河口セルの検出
!----------------------------------------------------------------------
subroutine check_rivermouth(p, g, irm)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  integer, intent(inout) :: irm(1:p%nx,1:p%ny)
  integer :: i, j, k, ii, jj
  integer :: nvc   ! number of valid cells
  integer :: nrc   ! number of river cells
  integer :: nrm   ! number of river mouth cells
  integer, parameter :: din(1:8) = [ -1,  0,  1, -1,  1, -1,  0,  1]
  integer, parameter :: djn(1:8) = [ -1, -1, -1,  0,  0,  1,  1,  1]

  irm(:,:) = 0
  nvc = 0
  nrc = 0
  nrm = 0

  do j = 2, p%ny - 1
    do i = 2, p%nx - 1
      if (g%x(i,j) <= 0) cycle
      nvc = nvc + 1
      if (g%rw(i,j) <= 0) cycle
      nrc = nrc + 1
      do k = 1, 8
        ii = i + din(k)
        jj = j + djn(k)
        !if (g%sw(ii,jj) > 0 .or. g%x(ii,jj) <= 0) then
        if (g%sw(ii,jj) > 0) then
          irm(i,j) = 1
          nrm = nrm + 1
          !print *, "River mouth", i, j
          exit
        end if
      end do
    end do
  end do
  print *, "Number of valid cells =", nvc
  print *, "Number of river cells =", nrc
  print *, "Number of river mouth =", nrm

end subroutine

end module

!======================================================================
! メインルーチン
!======================================================================
program rmdepression
  use m_rmdepress_river, only : m_main_all
  implicit none
  character(len=256) :: fn_param   ! パラメータファイル名
  character(len=256) :: fn_ddir    ! 流下方向ファイル名

  call get_fn_param(fn_param, fn_ddir)
  call m_main_all(fn_param, fn_ddir)

contains
!----------------------------------------------------------------------
! コマンドライン引数から設定ファイル名を取得する
!----------------------------------------------------------------------
subroutine get_fn_param(fn_param, fn_ddir)
  character(len=*) :: fn_param   ! パラメータファイル名
  character(len=*) :: fn_ddir    ! 流下方向ファイル名

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

  if (argc >= 2) then
    fn_param = arg(1)%v
    fn_ddir = arg(2)%v
  else
    print ('(a, a, a)'), "usage: ", arg(0)%v, " parameterfile DdaXXXX.bil"
    stop
  end if
end subroutine

end program
