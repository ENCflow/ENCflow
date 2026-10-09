!======================================================================
! twin: 複数インスタンスの交互実行ドライバ(nesting_plan Phase 0c の受入試験)
!     ./twin param1.txt [param2.txt ...]
!   与えられた各パラメータファイルを別インスタンスとして同一プロセスに
!   載せ、initialize → (1 ステップずつ順番に update) → finalize を行う。
!   各インスタンスの結果(dir_result 以下)は、同じパラメータで encflow を
!   単独実行した結果とビット一致しなければならない(Run.sh が比較する)。
!   = B 群(m_swflow_enc 系・m_ffactor・dcp)の文脈の付け替えと、A 群の
!   型による所有の明示に漏れがないことの検査。MPI では全ランクが同じ
!   順序で select/update を呼ぶ(collective の整合)。
!======================================================================
program twin
  use m_main, only : m_main_instances_alloc, m_main_select, m_main_initialize, &
                     m_main_update, m_main_finished, m_main_finalize
  implicit none
  integer :: n, k
  character(len=256), allocatable :: fn(:)
  logical, allocatable :: done(:)

  n = command_argument_count()
  if (n < 1) then
    print *, "usage: twin param1.txt [param2.txt ...]"
    stop 2
  end if
  allocate(fn(n), done(n))
  do k = 1, n
    call get_command_argument(k, fn(k))
  end do

  call m_main_instances_alloc(n)
  do k = 1, n
    call m_main_select(k)
    call m_main_initialize(fn(k))
  end do

  ! 1 ステップずつ交互に進める(終了したインスタンスは飛ばす)
  done = .false.
  do while (.not. all(done))
    do k = 1, n
      if (done(k)) cycle
      call m_main_select(k)
      if (m_main_finished()) then
        done(k) = .true.
      else
        call m_main_update()
      end if
    end do
  end do

  do k = 1, n
    call m_main_select(k)
    call m_main_finalize()
  end do
end program
