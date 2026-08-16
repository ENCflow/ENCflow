! このモジュールは旧プログラムとの互換性を確認するために存在している
! そのため古い書式をできるだけ変更しないよう維持している
!
! stgは浸食に非対応
!
module m_swflow_stg
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_boundary, only : t_boundary, e_bc_wall
  use m_state, only : t_state
  use m_parallel, only : dcp, par_stop
  implicit none
  private

  public :: m_swflow_stg_init
  public :: m_swflow_stg_calc
  public :: m_swflow_stg_dispose

  logical :: f_advection_term
  logical :: f_pressure_term
  logical :: f_advection_upwind = .true.

 
  real,ALLOCATABLE:: D(:,:)                  ! D:浸水深
  real,ALLOCATABLE:: M(:,:),M0(:,:),M1(:,:)  ! X方向の流量フラックス
  real,ALLOCATABLE:: N(:,:),N0(:,:),N1(:,:)  ! Y方向の流量フラックス

  real,ALLOCATABLE:: H(:,:)            ! H:標高
  real,ALLOCATABLE:: HQ(:,:)           ! HQ:降雨データ（計算用）
  real,ALLOCATABLE:: GV(:,:)           ! GV:1-家屋占有率,BB:家屋の大きさ
  real,ALLOCATABLE:: DN(:,:)           ! DN:土地利用の合成粗度
  real,ALLOCATABLE:: BB(:,:)           ! 家屋の平均寸法
  INTEGER,ALLOCATABLE:: X(:,:)         ! 海陸判別パラメータ
  INTEGER,ALLOCATABLE:: R(:,:)         ! 河道判別パラメータ

  INTEGER:: IG  ! 格子数（X方向）
  INTEGER:: JG  ! 格子数（Y方向）

  INTEGER,ALLOCATABLE:: I1(:),I2(:) ! 計算範囲（X方向）
  INTEGER:: J1,J2         ! 計算範囲（Y方向）

  real::DT           ! 時間ステップ
  real::DX           ! 計算格子の大きさ（X方向）
  real::DY           ! 計算格子の大きさ（Y方向）
  real::GG           ! 重力加速度
  real::DD           ! この水深以上なら移流項を計算する（限界水深）
  real::DV           ! これ以下なら強制的にこの水深にする（仮想水深）
  real::CM           ! 家屋の付加質量係数
  real::CD           ! 家屋の効力係数
  real::KK           ! 抗力項補正係数
      

  real::A(4) !ルンゲクッタ回数
  DATA A / 4., 3., 2., 1. / !ルンゲクッタ係数

contains
!======================================================================
!======================================================================
subroutine m_swflow_stg_init(p, g, b, s)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(in) :: b
  type(t_state), intent(inout) :: s
  INTEGER :: I,J
  if (b%initialized) continue  ! 引数未使用の警告を抑制

  ! STG は運動量(M,N)を保存しないため restart 非対応(developer.md §7)
  if (p%f_state_restore > 0) then
    call par_stop("list_sysparam: restart (f_state_restore) is not supported " &
                  //"with STG (f_gridsystem=1)")
  end if

  ! 辺境界条件は STG 非対応(凍結方針 §7)。既定(全辺不透過)以外は停止
  if (any(b%edge%btype /= e_bc_wall)) then
    call par_stop("list_bound_edge: edge boundary conditions are not supported " &
                  //"with STG (f_gridsystem=1)")
  end if
  if (b%nstage > 0) then
    call par_stop("list_bound_stage: prescribed water level cells are not supported " &
                  //"with STG (f_gridsystem=1)")
  end if
  if (b%ninflow > 0) then
    call par_stop("list_bound_inflow: segment inflow is not supported with STG (f_gridsystem=1)")
  end if
  ! 河道水理モデル(堤防・サブグリッド河道幅)は ENC 専用(§17, §18)
  if (g%bank_active .or. g%width_active) then
    call par_stop("list_channel: the channel hydraulics model (fn_channel) is not supported " &
                  //"with STG (f_gridsystem=1)")
  end if
  if (b%nstruct > 0) then
    call par_stop("list_structure: internal hydraulic structures (fn_structure) are not " &
                  //"supported with STG (f_gridsystem=1)")
  end if

  select case (p%f_govequation)
    case (0)      ! DynWE
      f_advection_term = .true.
      f_pressure_term = .true.
    case (1)      ! DifWE
      f_advection_term = .false.
      f_pressure_term = .true.
    case default  ! KinWE
      f_advection_term = .false.
      f_pressure_term = .false.
  end select

  DX = g%dx
  DY = g%dy
  DT = p%dt
  IG = g%nx
  JG = g%ny
  ! 動的状態: セル量は jsh:jeh、y面フラックス(N系)は
  ! 「セル j を挟む面は j-1 と j」の規約により jsh-1:jeh
  ALLOCATE(D(1:IG,dcp%jsh:dcp%jeh),SOURCE=0.0)
  ALLOCATE(M(0:IG,dcp%jsh:dcp%jeh),SOURCE=0.0)
  ALLOCATE(M0(0:IG,dcp%jsh:dcp%jeh),SOURCE=0.0)
  ALLOCATE(M1(0:IG,dcp%jsh:dcp%jeh),SOURCE=0.0)
  ALLOCATE(N(1:IG,dcp%jsh-1:dcp%jeh),SOURCE=0.0)
  ALLOCATE(N0(1:IG,dcp%jsh-1:dcp%jeh),SOURCE=0.0)
  ALLOCATE(N1(1:IG,dcp%jsh-1:dcp%jeh),SOURCE=0.0)
  ! 静的コピー(H/GV/DN/BB/X/R)と行別窓 I1/I2 は全域保持のまま
  ! H/GV/DN/BB のコピー元(s%z, g%gv, g%rn, g%bb)は帯確保のため
  ! 同じ帯で確保する(全域のままだと全配列代入が形状不一致で np>=2 で破綻)。
  ! X/R のコピー元(g%sw, g%rw)は init 時点(ゾーン2)では全域なので全域のまま
  ALLOCATE(H(1:IG,dcp%jsh:dcp%jeh),SOURCE=0.0)
  ALLOCATE(HQ(1:IG,dcp%jsh:dcp%jeh),SOURCE=0.0)
  ALLOCATE(GV(1:IG,dcp%jsh:dcp%jeh),SOURCE=0.0)
  ALLOCATE(DN(1:IG,dcp%jsh:dcp%jeh),SOURCE=0.0)
  ALLOCATE(BB(1:IG,dcp%jsh:dcp%jeh),SOURCE=1.e10)
  ALLOCATE(X(1:IG,1:JG),SOURCE=0)
  ALLOCATE(R(1:IG,1:JG),SOURCE=0)
  allocate(I1(1:JG))
  allocate(I2(1:JG))

  
  !GG=9.8            ! 重力加速度
  !DD=0.001          ! この水深以上なら移流項を計算する（限界水深）
  !DV=0.002          ! これ以下なら強制的にこの水深にする（仮想水深）
  !CM=2.0            ! 家屋の付加質量係数
  !CD=1.0            ! 家屋の効力係数
  !KK=0.5            ! 抗力項補正係数

  GG=p%gg             ! 重力加速度
  DD=p%dd             ! この水深以上なら移流項を計算する（限界水深）
  DV=p%dv             ! これ以下なら強制的にこの水深にする（仮想水深）
  CM=p%cm             ! 家屋の付加質量係数
  CD=p%cd             ! 家屋の効力係数
  KK=p%kk             ! 抗力項補正係数

  H(:,:)=s%z(:,:)     ! H:標高
  GV(:,:)=g%gv(:,:)   ! GV:1-家屋占有率
  BB(:,:)=g%bb(:,:)   ! BB:家屋の平均寸法
  DN(:,:)=g%rn(:,:)   ! DN:土地利用の合成粗度
  X(:,:)=g%sw(:,:)    ! X:海陸判別パラメータ
  R(:,:)=g%rw(:,:)    ! R:河道判別パラメータ
  D(:,:)=s%h(:,:)     ! D:水深


! 計算範囲を決める  都道府県番号で判別
      I1(:)=2
      I2(:)=2
      ! 全域の格子端で1行縮めた範囲と自ランク担当帯の交差。
      ! 全計算ループは J1/J2 を参照するため、分割の注入点はここだけ
      J1=max(dcp%js, 2)
      J2=min(dcp%je, JG-1)
      !$omp parallel
      !$omp do
      DO J=J1,J2
        !DO I=2,IG-1    ! 領域端での移流項の計算でI=0へのアクセスが生じる
        DO I=3,IG-2     ! 両側は3セルの余地が必要
          IF(X(I,J).EQ.0)THEN
            I1(J)=I-1
            EXIT
          ENDIF
        ENDDO
        DO I=IG-1,2,-1
          IF(X(I,J).EQ.0)THEN
            I2(J)=I
            EXIT
          ENDIF
        ENDDO
      ENDDO
      !$omp end do
      !$omp end parallel

      !DO J=J1,J2
      !PRINT *, I1(J), I2(J)
      !ENDDO
      !pause

END SUBROUTINE

!----------------------------------------------------------------------
!----------------------------------------------------------------------
SUBROUTINE m_swflow_stg_dispose(p)
  type(t_sysparam), intent(in) :: p
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  DEALLOCATE(D)
  DEALLOCATE(M)
  DEALLOCATE(M0)
  DEALLOCATE(M1)
  DEALLOCATE(N)
  DEALLOCATE(N0)
  DEALLOCATE(N1)
  DEALLOCATE(H)
  DEALLOCATE(HQ)
  DEALLOCATE(GV)
  DEALLOCATE(DN)
  DEALLOCATE(BB)
  DEALLOCATE(X)
  DEALLOCATE(R)
END SUBROUTINE


!----------------------------------------------------------------------
!----------------------------------------------------------------------
SUBROUTINE m_swflow_stg_calc(p, g, b, s, ierror)
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_boundary), intent(inout) :: b   ! calc 共通インターフェースに合わせる(§22)
  type(t_state), intent(inout) :: s
  integer, intent(inout) :: ierror

  REAL:: DC           ! 計算用（水深）
  REAL:: DH           ! 計算用（水位差）
  REAL:: VNC          ! 計算用（粗度係数）
  REAL:: FC           ! 計算用（摩擦・抗力項）半陰解法
  REAL:: FT1,FT2,FG   ! 計算用（移流項，重力項）
  REAL:: MM1,MM2,MM3,MMC,NN1,NN2,NN3,NNC
  REAL:: D1,D2,D3
  REAL:: GV1,GV2,GV3,GVC,LM1,LM2,LM3,LMC,BBC
  REAL:: OUTMN,OUTD !,V,QF  !QF:単位幅流量（スカラー）　rev0827
  ! 帯スケール(逐次では全域)の作業配列はヒープに置く(§40)
  REAL, ALLOCATABLE :: OUTD_(:,:)
  INTEGER:: I,J,L
  INTEGER:: ITER
  REAL:: Mm,Nm,QF
  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  if (b%initialized) continue  ! 引数未使用の警告を抑制

  ALLOCATE(OUTD_(IG,dcp%jsh:dcp%jeh))

  s%n_runge = s%n_valcells * 4
  ierror = ierror + 0

        !$omp parallel
!===== 流量の計算(運動方程式) ==========================================
!      時間計算->4段階Runge-Kutta(Jameson-Baker)
!      時間項->前進差分
!      移流項->1次精度風上差分
!      摩擦・抗力項->半陰的な差分（単位幅流量…根号内:陽的，根号外:陰的）
!      重力項->風上側の水深を使用，d(D+h)/dx (= tanθ) をsinθに置き換えたバージョン
!     （∵過大な重力項を抑制するため）
!      摩擦項・摩擦項の水深の扱いも重力項と同じで風上側の水深を使用
!     （風上・風下の平均水深を用いたら河道付近の計算が不安定）
!=======================================================================
        !$omp do
        DO J=J1,J2
        DO I=I1(J),I2(J)
          M0(I,J)=M(I,J)
          N0(I,J)=N(I,J)
        ENDDO
        ENDDO
        !$omp end do
!===== ルンゲクッタループ ==============================================
        DO L=1,4
!     ***** Mの計算 *****
          !ループの中で使う一時変数は private() の中で宣言しておくこと
          !$omp do private(I,GV1,GV2,GV3,LM1,LM2,LM3,MM1,MM2,MM3,NN1,NN2,NN3,D1,D2,D3,FT1,FT2,GVC,LMC,DC,DH,FG,VNC,MMC,NNC,FC,BBC)
          DO J=J1,J2
          DO I=I1(J),I2(J)
            IF(X(I,J).EQ.0 .OR. X(I+1,J).EQ.0)THEN ! 陸
            M1(I,J)=0.0
            IF(D(I+1,J).GT.DD .OR. D(I,J).GT.DD)THEN ! 限界水深
!     --- M 移流項1 ---
            ! 風上差分
            GV1=GV(I,J)
            GV2=(GV(I,J)+GV(I+1,J))*0.5
            GV3=GV(I+1,J)
            LM1=GV1+(1.0-GV1)*CM
            LM2=GV2+(1.0-GV2)*CM
            LM3=GV3+(1.0-GV3)*CM
            MM1=(M(I,J)+M(I-1,J))*0.5
            MM2=M(I,J)
            MM3=(M(I,J)+M(I+1,J))*0.5
            D1=D(I,J)
            D2=(D(I,J)+D(I+1,J))*0.5
            D3=D(I+1,J)
            D1=MAX(D1,DV)
            D2=MAX(D2,DV)
            D3=MAX(D3,DV)
            if (f_advection_upwind) then
              IF(M(I,J).GT.0.0)THEN
                FT1=(LM2*MM2**2.0/D2-LM1*MM1**2.0/D1)/DX
              ELSEIF(M(I,J).LT.0.0)THEN
                FT1=(LM3*MM3**2.0/D3-LM2*MM2**2.0/D2)/DX
              ELSE
                FT1=(LM3*MM3**2.0/D3-LM1*MM1**2.0/D1)/DX
              ENDIF
            else
              FT1=(LM3*MM3**2.0/D3-LM1*MM1**2.0/D1)/DX
            end if
!     --- M 移流項2 ---
            ! 風上差分
            GV1=(GV(I,J)+GV(I+1,J)+GV(I,J-1)+GV(I+1,J-1))*0.25
            GV2=(GV(I,J)+GV(I+1,J))*0.5
            GV3=(GV(I,J)+GV(I+1,J)+GV(I,J+1)+GV(I+1,J+1))*0.25
            LM1=GV1+(1.0-GV1)*CM
            LM2=GV2+(1.0-GV2)*CM
            LM3=GV3+(1.0-GV3)*CM
            MM1=(M(I,J)+M(I,J-1))*0.5
            MM2=M(I,J)
            MM3=(M(I,J)+M(I,J+1))*0.5
            NN1=(N(I,J-1)+N(I+1,J-1))*0.5
            NN2=(N(I,J)+N(I+1,J)+N(I,J-1)+N(I+1,J-1))*0.25
            NN3=(N(I,J)+N(I+1,J))*0.5
            D1=(D(I,J)+D(I+1,J)+D(I,J-1)+D(I+1,J-1))*0.25
            D2=(D(I,J)+D(I+1,J))*0.5
            D3=(D(I,J)+D(I+1,J)+D(I,J+1)+D(I+1,J+1))*0.25
            D1=MAX(D1,DV)
            D2=MAX(D2,DV)
            D3=MAX(D3,DV)
            if (f_advection_upwind) then
              IF(NN2.GT.0.0)THEN
                FT2=(LM2*MM2*NN2/D2-LM1*MM1*NN1/D1)/DY
              ELSEIF(NN2.LT.0.0)THEN
                FT2=(LM3*MM3*NN3/D3-LM2*MM2*NN2/D2)/DY
              ELSE
                FT2=(LM3*MM3*NN3/D3-LM1*MM1*NN1/D1)/DY
              ENDIF
            else
              FT2=(LM3*MM3*NN3/D3-LM1*MM1*NN1/D1)/DY
            end if
            if (f_advection_term .eqv. .false.) then
              FT1=0
              FT2=0
            end if
!     --- M 重力項 ---
            GVC=(GV(I,J)+GV(I+1,J))*0.5
            LMC=GVC+(1.0-GVC)*CM
            IF(M(I,J).GT.0)THEN
              DC=D(I,J)
            ELSEIF(M(I,J).LT.0)THEN
              DC=D(I+1,J)
            ELSE
              DC=(D(I+1,J)+D(I,J))*0.5
            ENDIF
            if (f_pressure_term) then
              DH=(D(I+1,J)+H(I+1,J))-(D(I,J)+H(I,J)) ! 海：D=SK, H=0
            else
              DH=H(I+1,J)-H(I,J)
            end if
            FG=GG*DC*DH/SQRT(DH**2.0+DX**2.0)*GVC
!     --- M 摩擦項 ---
            DC=MAX(DC,DV)
            VNC=(DN(I,J)+DN(I+1,J))*0.5
            MMC=M(I,J)
            NNC=(N(I,J)+N(I,J-1)+N(I+1,J)+N(I+1,J-1))*0.25
            FC=GG*VNC**2.0/DC**(7.0/3.0)*SQRT(MMC**2.0+NNC**2.0)*GVC
!     --- M 抗力項 ---
            BBC=(BB(I,J)+BB(I+1,J))*0.5
            FC=FC+KK*CD/DC/BBC*SQRT(MMC**2.0+NNC**2.0)*(1.0-GVC)
!     --- M 計算 ---
            M1(I,J)=(M0(I,J)-(FT1+FT2+FG)*DT/LMC/A(L))/(1.0+FC*DT/LMC/A(L))
!     --- M 河道から海への流量フラックスを段落ち式により計算 ---
!     --- >>河道を掘り下げて計算するときに河口周辺の標高が0を下回るため<< ---
            IF(R(I,J).EQ.1 .AND. X(I+1,J).EQ.1)THEN
              M1(I,J)= ((2.0/3.0)**(3.0/2.0))*D(I  ,J)*SQRT(GG*D(I  ,J))
            ELSEIF(X(I,J).EQ.1 .AND. R(I+1,J).EQ.1)THEN
              M1(I,J)=-((2.0/3.0)**(3.0/2.0))*D(I+1,J)*SQRT(GG*D(I+1,J))
            ENDIF
!     --- 移動限界水深に基づく流量フラックスの修正 ---
            IF(D(I  ,J).LE.DD .AND. M1(I,J).GT.0.0) M1(I,J)=0.0
            IF(D(I+1,J).LE.DD .AND. M1(I,J).LT.0.0) M1(I,J)=0.0

            ENDIF ! 限界水深ループの終わり
            ENDIF ! X=0 ループの終わり
          ENDDO
          ENDDO
          !$omp end do
!     ***** Nの計算 *****
          !ループの中で使う一時変数は private() の中で宣言しておくこと
          !$omp do private(I,GV1,GV2,GV3,LM1,LM2,LM3,MM1,MM2,MM3,NN1,NN2,NN3,D1,D2,D3,FT1,FT2,GVC,LMC,DC,DH,FG,VNC,NNC,MMC,FC,BBC)
          DO J=J1,J2
          DO I=I1(J),I2(J)
            IF(X(I,J).EQ.0 .OR. X(I,J+1).EQ.0)THEN ! 陸
            N1(I,J)=0.0
            IF(D(I,J+1).GT.DD .OR. D(I,J).GT.DD)THEN ! 限界水深
!     --- N 移流項1 ---
            ! 風上差分
            GV1=GV(I,J)
            GV2=(GV(I,J)+GV(I,J+1))*0.5
            GV3=GV(I,J+1)
            LM1=GV1+(1.0-GV1)*CM
            LM2=GV2+(1.0-GV2)*CM
            LM3=GV3+(1.0-GV3)*CM
            NN1=(N(I,J)+N(I,J-1))*0.5
            NN2=N(I,J)
            NN3=(N(I,J)+N(I,J+1))*0.5
            D1=D(I,J)
            D2=(D(I,J)+D(I,J+1))*0.5
            D3=D(I,J+1)
            D1=MAX(D1,DV)
            D2=MAX(D2,DV)
            D3=MAX(D3,DV)
            if (f_advection_upwind) then
              IF(N(I,J).GT.0.0)THEN
                FT1=(LM2*NN2**2.0/D2-LM1*NN1**2.0/D1)/DY
              ELSEIF(N(I,J).LT.0.0)THEN
                FT1=(LM3*NN3**2.0/D3-LM2*NN2**2.0/D2)/DY
              ELSE
                FT1=(LM3*NN3**2.0/D3-LM1*NN1**2.0/D1)/DY
              ENDIF
            else
              FT1=(LM3*NN3**2.0/D3-LM1*NN1**2.0/D1)/DY
            end if
!     --- N 移流項2 ---
            ! 風上差分
            GV1=(GV(I,J)+GV(I,J+1)+GV(I-1,J)+GV(I-1,J+1))*0.25
            GV2=(GV(I,J)+GV(I,J+1))*0.5
            GV3=(GV(I,J)+GV(I,J+1)+GV(I+1,J)+GV(I+1,J+1))*0.25
            LM1=GV1+(1.0-GV1)*CM
            LM2=GV2+(1.0-GV2)*CM
            LM3=GV3+(1.0-GV3)*CM
            NN1=(N(I,J)+N(I-1,J))*0.5
            NN2=N(I,J)
            NN3=(N(I,J)+N(I+1,J))*0.5
            MM1=(M(I-1,J)+M(I-1,J+1))*0.5
            MM2=(M(I,J)+M(I,J+1)+M(I-1,J)+M(I-1,J+1))*0.25
            MM3=(M(I,J)+M(I,J+1))*0.5
            D1=(D(I,J)+D(I,J+1)+D(I-1,J)+D(I-1,J+1))*0.25
            D2=(D(I,J)+D(I,J+1))*0.5
            D3=(D(I,J)+D(I,J+1)+D(I+1,J)+D(I+1,J+1))*0.25
            D1=MAX(D1,DV)
            D2=MAX(D2,DV)
            D3=MAX(D3,DV)
            if (f_advection_upwind) then
              IF(MM2.GT.0.0)THEN
                FT2=(LM2*NN2*MM2/D2-LM1*NN1*MM1/D1)/DX
              ELSEIF(MM2.LT.0.0)THEN
                FT2=(LM3*NN3*MM3/D3-LM2*NN2*MM2/D2)/DX
              ELSE
                FT2=(LM3*NN3*MM3/D3-LM1*NN1*MM1/D1)/DX
              ENDIF
            else
              FT2=(LM3*NN3*MM3/D3-LM1*NN1*MM1/D1)/DX
            end if
            if (f_advection_term .eqv. .false.) then
              FT1=0
              FT2=0
            end if
!     --- N 重力項 ---
            GVC=(GV(I,J)+GV(I,J+1))*0.5
            LMC=GVC+(1.0-GVC)*CM
            IF(N(I,J).GT.0)THEN
              DC=D(I,J)
            ELSEIF(N(I,J).LT.0)THEN
              DC=D(I,J+1)
            ELSE
              DC=(D(I,J+1)+D(I,J))*0.5
            ENDIF
            if (f_pressure_term) then
              DH=(D(I,J+1)+H(I,J+1))-(D(I,J)+H(I,J)) ! 海：D=SK, H=0
            else
              DH=H(I,J+1)-H(I,J)
            end if
            FG=GG*DC*DH/SQRT(DH**2.0+DY**2.0)*GVC
!     --- N 摩擦項 ---
            DC=MAX(DC,DV)
            VNC=(DN(I,J)+DN(I,J+1))*0.5
            NNC=N(I,J)
            MMC=(M(I-1,J+1)+M(I-1,J)+M(I,J+1)+M(I,J))*0.25
            FC=GG*VNC**2.0/DC**(7.0/3.0)*SQRT(NNC**2.0+MMC**2.0)*GVC
!     --- N 抗力項 ---
            BBC=(BB(I,J)+BB(I,J+1))*0.5
            FC=FC+KK*CD/DC/BBC*SQRT(NNC**2.0+MMC**2.0)*(1.0-GVC)
!     --- N 計算 ---
            N1(I,J)=(N0(I,J)-(FT1+FT2+FG)*DT/LMC/A(L))/(1.+FC*DT/LMC/A(L))
!     --- M 河道から海への流量フラックスを段落ち式により計算[MODE=3：洪水単独] ---
!     --- >>河道を掘り下げて計算するときに河口周辺の標高が0を下回るため<< ---
            IF(R(I,J).EQ.1 .AND. X(I,J+1).EQ.1)THEN
              N1(I,J)= ((2.0/3.0)**(3.0/2.0))*D(I,J  )*SQRT(GG*D(I,J  ))
            ELSEIF(X(I,J).EQ.1 .AND. R(I,J+1).EQ.1)THEN
              N1(I,J)=-((2.0/3.0)**(3.0/2.0))*D(I,J+1)*SQRT(GG*D(I,J+1))
            ENDIF
!     --- 移動限界水深に基づく流量フラックスの修正 ---
            IF(D(I,J  ).LE.DD .AND. N1(I,J).GT.0.0) N1(I,J)=0.0
            IF(D(I,J+1).LE.DD .AND. N1(I,J).LT.0.0) N1(I,J)=0.0

            ENDIF !限界水深ループの終わり
            ENDIF !X=0 ループの終わり
          ENDDO
          ENDDO
          !$omp end do
!      ***** 計算結果をコピー *****
          !$omp do
          DO J=J1,J2
          DO I=I1(J),I2(J)
            M(I,J)=M1(I,J)
            N(I,J)=N1(I,J)
          ENDDO
          ENDDO
          !$omp end do
        ENDDO !Lループの終わり
!===== ルンゲクッタ終了 ================================================
!===== 流量配分 ========================================================
        s%n_exfluxes = 0
        ITER=10 ! 緩和係数
        !ITER=0 ! 緩和係数
        DO L=1,ITER
          !$omp do private(OUTMN)
          DO J=J1,J2
          DO I=I1(J),I2(J)
            IF(X(I,J).EQ.0)THEN
              OUTMN=0.0
              IF(M(I-1,J  ).LT.0.0) OUTMN=OUTMN-M(I-1,J  )/DX
              IF(M(I  ,J  ).GT.0.0) OUTMN=OUTMN+M(I  ,J  )/DX
              IF(N(I  ,J-1).LT.0.0) OUTMN=OUTMN-N(I  ,J-1)/DY
              IF(N(I  ,J  ).GT.0.0) OUTMN=OUTMN+N(I  ,J  )/DY
              OUTD_(I,J)=OUTMN*DT/GV(I,J)
            ENDIF
          ENDDO
          ENDDO
          !$omp end do
          !$omp do private(OUTD)
          DO J=J1,J2
          DO I=I1(J),I2(J)
            IF(X(I,J).EQ.0)THEN
              IF(OUTD_(I,J).GT.D(I,J) .AND. OUTD_(I,J).NE.0.0)THEN
                OUTD=D(I,J)/OUTD_(I,J)/ITER
                IF(M(I  ,J  ).GT.0.0) M(I  ,J  )=M(I  ,J  )*OUTD
                IF(M(I-1,J  ).LT.0.0) M(I-1,J  )=M(I-1,J  )*OUTD
                IF(N(I  ,J  ).GT.0.0) N(I  ,J  )=N(I  ,J  )*OUTD
              ENDIF
            ENDIF
          ENDDO
          ENDDO
          !$omp end do
          !$omp do private(OUTD)
          DO J=J1,J2
          DO I=I1(J),I2(J)
            IF(X(I,J).EQ.0)THEN
              IF(OUTD_(I,J).GT.D(I,J) .AND. OUTD_(I,J).NE.0.0)THEN
                OUTD=D(I,J)/OUTD_(I,J)/ITER
                IF(N(I  ,J-1).LT.0.0) N(I  ,J-1)=N(I  ,J-1)*OUTD
              ENDIF
            ENDIF
          ENDDO
          ENDDO
          !$omp end do
        ENDDO ! ITER
!===== 流量配分終了 ====================================================
!===== EQ. OF CONTINUITY [ 連続方程式 ] ================================
! 浸水深推定
        !$omp do
        DO J=J1,J2
        DO I=I1(J),I2(J)
          IF(X(I,J).EQ.0)THEN
            D(I,J)=D(I,J) &
            &      -DT/DX*(M(I,J)-M(I-1,J))/GV(I,J) &
            &      -DT/DY*(N(I,J)-N(I,J-1))/GV(I,J) &
            &      +s%pre(I,J)*DT/GV(I,J)
            Mm=(M(I,J)+M(I-1,J))/2.0
            Nm=(N(I,J)+N(I,J-1))/2.0
            QF=SQRT(Mm**2.0+Nm**2.0)    ! 単位幅流量[m^2/s] !rev082
            s%m(i,j) = Mm
            s%n(i,j) = Nm
            s%qq(i,j) = QF
            IF(D(I,J).GE.DD)THEN
              s%u(i,j) = Mm/D(I,J)
              s%v(i,j) = Nm/D(I,J)
              s%vv(i,j) = QF/D(I,J)
            ELSE
              s%u(i,j) = 0.0
              s%v(i,j) = 0.0
              s%vv(i,j) = 0.0
            ENDIF
            s%h(i,j) = D(i,j)
            s%e(i,j) = s%z(i,j) + D(i,j)
          ELSE
            D(I,J)=0.0 ! 海であればD=0
          ENDIF
        ENDDO
        ENDDO
        !$omp end do
!===== 連続方程式終了 ==================================================

    !$omp end parallel

end subroutine

!======================================================================
!========================== PRIVATE ROUTINES ==========================
!======================================================================


end module
