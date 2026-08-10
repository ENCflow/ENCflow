module m_intercept
  ! ================ 降雨遮断プロセスモジュール(切替器) ================
  ! 植生・林冠による降雨遮断(interception)のモデル群
  ! (固定遮断率 / 初期損失 / キャノピー貯留 …)を排他切替で使う。
  ! m_gwflow と同じ構造:
  !   - 有効化は fn_intercept の指定の有無(未指定なら完全に不活性)
  !   - モデル選択は fn_intercept 内の &list_intercept の f_icmodel
  !     (0 なら fn を書いたまま一時無効化できる)
  !   - 束縛は t_intercept の手続きポインタ成分(abstract interface + nopass)
  !   - 各モデルの固有設定・内部状態・リスタート保存はモデル私有
  !     (実装の契約は m_intercept_fixed のヘッダを参照)
  !
  ! 【呼び出しタイミングの契約】
  !   m_main は「降雨分布が実際に更新された直後」(m_precip_makepre が
  !   updated を返したとき)にのみ calc を呼び、makepre が作った
  !   s%pre / s%prh を有効雨量(地表到達雨量)に減じる。更新されない
  !   ステップに再適用すると二重減衰になるため、makepre の updated が
  !   このガードの正本(prtype=3 では makepre が呼ばれても分布を更新
  !   しないステップがある)。
  !   貯留型モデル(状態が毎ステップ発展する)は2口で動く:
  !     calc(降雨更新直後)= 原雨量を私有配列へ写し取る(s%pre は不変)
  !     step(毎ステップ、swflow が s%pre を読む前)= 貯留を発展させ、
  !       s%pre / s%prh を原雨量から計算し直す
  !   固定遮断率のような無状態モデルは step を束縛しない(calc で破壊的に
  !   適用して終わり)。貯留型の実装契約は m_intercept_initloss のヘッダ。
  ! ====================================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use list_intercept, only : t_list_intercept, list_intercept_read
  use m_intercept_fixed, only : intercept_fixed_init, intercept_fixed_calc, &
                                intercept_fixed_dispose
  use m_intercept_initloss, only : intercept_initloss_init, intercept_initloss_calc, &
                                intercept_initloss_step, intercept_initloss_draw, &
                                intercept_initloss_dispose
  use m_parallel, only : par_stop
  use m_util, only : itoa
  implicit none
  private
  public :: t_intercept
  public :: m_intercept_init
  public :: m_intercept_calc
  public :: m_intercept_step
  public :: m_intercept_has_step
  public :: m_intercept_dispose

  !-------------------------------------------
  ! 遮断モデルのインターフェース
  ! (型成分で参照するため、型定義より前に置くこと)
  !-------------------------------------------
  abstract interface
    subroutine procedure_intercept_init(p, g)
      import :: t_sysparam, t_geoinfo
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
    end subroutine

    subroutine procedure_intercept_calc(p, g, s, it)
      import :: t_sysparam, t_geoinfo, t_state
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
      integer, intent(in) :: it
    end subroutine

    subroutine procedure_intercept_dispose(p)
      import :: t_sysparam
      type(t_sysparam), intent(in) :: p
    end subroutine

    ! 蒸発散による貯留の引き落とし口(m_evap が毎ステップ・セルごとに呼ぶ。
    ! §27)。需要 dem (m) のうち貯留から引けた量を返し、内部状態を減じる
    ! (=遮断容量の乾き戻り)。貯留を持つモデルのみ束縛する
    function procedure_intercept_draw(i, j, dem) result(w)
      integer, intent(in) :: i, j
      real, intent(in) :: dem
      real :: w
    end function
  end interface
  !-------------------------------------------


  type t_intercept
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    procedure(procedure_intercept_init),    pointer, nopass :: init    => null()
    procedure(procedure_intercept_calc),    pointer, nopass :: calc    => null()
    procedure(procedure_intercept_calc),    pointer, nopass :: step    => null()
                                     ! 毎ステップ口(貯留型のみ束縛。calc と同シグネチャ)
    procedure(procedure_intercept_draw),    pointer, nopass :: draw    => null()
                                     ! 蒸発散の引き落とし口(貯留型のみ束縛。§27)
    procedure(procedure_intercept_dispose), pointer, nopass :: dispose => null()
    logical :: enabled = .false.     ! fn_intercept の有無と f_icmodel で決まる
    logical :: initialized = .false.
  end type

contains


!----------------------------------------------------------------------
! 降雨遮断モジュールを初期化する
!   fn_intercept 未指定 or f_icmodel=0 なら何もしない(enabled = .false.)
!----------------------------------------------------------------------
subroutine m_intercept_init(ic, p, g)
  type(t_intercept), intent(out) :: ic
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_intercept) :: list

  if (len_trim(p%fn_intercept) == 0) return

  call list_intercept_read(p, list)

  if (list%f_icmodel == 0) return    ! fn を書いたまま一時無効化する経路

  ! --- モデルの束縛(新モデルの追加はここに case を足す) ---
  select case (list%f_icmodel)
    case (1)
      ic%init    => intercept_fixed_init
      ic%calc    => intercept_fixed_calc
      ic%dispose => intercept_fixed_dispose
    case (2)
      ic%init    => intercept_initloss_init
      ic%calc    => intercept_initloss_calc
      ic%step    => intercept_initloss_step
      ic%draw    => intercept_initloss_draw
      ic%dispose => intercept_initloss_dispose
    case default
      call par_stop("list_intercept: f_icmodel must be 0(none), 1(fixed) or 2(initloss): " &
                    // itoa(list%f_icmodel))
  end select

  ic%enabled = .true.
  call ic%init(p, g)
  ic%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 降雨遮断を適用する(降雨分布の更新直後に run_main から呼ばれる。
! 呼び出しガードはヘッダの契約を参照)
!   冒頭の return 判定は全ランクで同一(collective 安全)
!----------------------------------------------------------------------
subroutine m_intercept_calc(ic, p, g, s, it)
  type(t_intercept), intent(in) :: ic
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it

  if (.not. ic%enabled) return
  call ic%calc(p, g, s, it)
end subroutine


!----------------------------------------------------------------------
! 貯留型モデルの毎ステップ更新(run_main が swflow の前に毎ステップ呼ぶ)
!   step 口を持たないモデル(固定遮断率)では何もしない。
!   冒頭の return 判定は全ランクで同一(collective 安全)
!----------------------------------------------------------------------
subroutine m_intercept_step(ic, p, g, s, it)
  type(t_intercept), intent(in) :: ic
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it

  if (.not. ic%enabled) return
  if (.not. associated(ic%step)) return
  call ic%step(p, g, s, it)
end subroutine


!----------------------------------------------------------------------
! 貯留型(毎ステップ s%pre を書き直す step 口)を持つか(m_snow の
! スナップショット更新判定に使う。§31)
!----------------------------------------------------------------------
function m_intercept_has_step(ic) result(res)
  type(t_intercept), intent(in) :: ic
  logical :: res
  res = ic%enabled .and. associated(ic%step)
end function


!----------------------------------------------------------------------
! 降雨遮断モジュールを破棄する
!----------------------------------------------------------------------
subroutine m_intercept_dispose(ic, p)
  type(t_intercept), intent(inout) :: ic
  type(t_sysparam), intent(in) :: p
  if (ic%enabled) call ic%dispose(p)
  ic%init    => null()
  ic%calc    => null()
  ic%step    => null()
  ic%draw    => null()
  ic%dispose => null()
  ic%enabled = .false.
  ic%initialized = .false.
end subroutine

end module
