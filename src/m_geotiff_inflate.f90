!======================================================================
! m_geotiff_inflate: Deflate(zlib)復号(docs/geotiff_plan.md §6.1, Phase 2)
!   TIFF の Compression=8(Adobe Deflate)/ 32946(旧 Deflate)は
!   どちらも zlib ストリーム(RFC 1950 ヘッダ + RFC 1951 deflate)。
!   ENCflow 本体のどのモジュールにも依存しない。エラーは stat で返す。
!
!   実装メモ:
!   - ビット列は LSB-first(LZW の MSB-first と逆)。ハフマン符号自体は
!     コードの上位ビットから流れるので、1 ビットずつ読み進める正準符号の
!     逐次復号(zlib の puff.c と同じ方式)を使う。
!   - 窓(32KB)は別に持たず、出力バッファ自身を参照する(strip/tile
!     1 ブロックを丸ごと展開するため。距離コピーの重なりは 1 バイトずつの
!     コピーで自然に正しくなる)。
!   - 末尾の Adler32 は検証しない(値の正しさは上位の回帰テストで担保。
!     長さの過不足・符号の破損はここで検出する)。
!======================================================================
module m_geotiff_inflate
  use, intrinsic :: iso_fortran_env, only : int8, int32, int64
  implicit none
  private

  public :: gtc_inflate_zlib

  ! 長さ符号(257..285)の基底と追加ビット
  integer, parameter :: lbase(29) = [3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, &
                                     35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258]
  integer, parameter :: lextra(29) = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, &
                                      3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0]
  ! 距離符号(0..29)の基底と追加ビット
  integer, parameter :: dbase(30) = [1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, &
                                     257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145, &
                                     8193, 12289, 16385, 24577]
  integer, parameter :: dextra(30) = [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, &
                                      7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13]
  ! 符号長符号の並び順
  integer, parameter :: clorder(19) = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]

  ! 正準ハフマン表(長さごとの符号数と、(長さ, 記号) 順の記号表)
  type t_huff
    integer :: cnt(0:15) = 0
    integer :: sym(288) = 0
  end type

contains

!----------------------------------------------------------------------
! zlib ストリームを復号する。ubuf が過不足なく埋まらなければ stat=1
!----------------------------------------------------------------------
subroutine gtc_inflate_zlib(cbuf, ubuf, stat)
  integer(int8), intent(in) :: cbuf(:)
  integer(int8), intent(out) :: ubuf(:)
  integer, intent(out) :: stat

  integer(int64) :: nc, nu, ipos, o
  integer :: bitbuf, bitcnt
  integer :: bfinal, btype

  nc = size(cbuf, kind=int64)
  nu = size(ubuf, kind=int64)
  stat = 1

  ! zlib ヘッダ(CMF/FLG)。方式=deflate、プリセット辞書なしのみ対応
  if (nc < 3) return
  if (iand(u8(cbuf(1)), 15) /= 8) return             ! CM /= deflate
  if (iand(u8(cbuf(2)), 32) /= 0) return             ! FDICT は未対応
  ipos = 3
  bitbuf = 0
  bitcnt = 0
  o = 0

  do
    bfinal = bits(1)
    btype = bits(2)
    if (bfinal < 0 .or. btype < 0) return
    select case (btype)
      case (0)
        if (.not. stored_block()) return
      case (1)
        if (.not. huff_block(fixed_lit(), fixed_dist())) return
      case (2)
        block
          type(t_huff) :: hlit, hdist
          if (.not. dynamic_tables(hlit, hdist)) return
          if (.not. huff_block(hlit, hdist)) return
        end block
      case default
        return                                       ! btype=3 は不正
    end select
    if (bfinal == 1) exit
  end do
  if (o /= nu) return                                ! 長さの過不足
  stat = 0

contains

  ! バイト値の符号なし解釈
  pure integer function u8(b)
    integer(int8), intent(in) :: b
    u8 = iand(int(b, int32), 255)
  end function

  ! LSB-first のビット読み出し(n <= 16)。尽きたら負値
  integer function bits(n)
    integer, intent(in) :: n
    do while (bitcnt < n)
      if (ipos > nc) then
        bits = -1
        return
      end if
      bitbuf = ior(bitbuf, ishft(u8(cbuf(ipos)), bitcnt))
      ipos = ipos + 1
      bitcnt = bitcnt + 8
    end do
    bits = iand(bitbuf, 2**n - 1)
    bitbuf = ishft(bitbuf, -n)
    bitcnt = bitcnt - n
  end function

  ! 無圧縮ブロック(バイト境界に揃えて LEN/NLEN+生データ)
  logical function stored_block()
    integer(int64) :: len
    integer :: l1, l2, n1, n2
    stored_block = .false.
    bitbuf = 0                                       ! バイト境界へ捨てる
    bitcnt = 0
    if (ipos + 3 > nc) return
    l1 = u8(cbuf(ipos)); l2 = u8(cbuf(ipos+1))
    n1 = u8(cbuf(ipos+2)); n2 = u8(cbuf(ipos+3))
    ipos = ipos + 4
    if (ieor(l1, n1) /= 255 .or. ieor(l2, n2) /= 255) return
    len = l1 + 256*l2
    if (ipos + len - 1 > nc .or. o + len > nu) return
    ubuf(o+1:o+len) = cbuf(ipos:ipos+len-1)
    ipos = ipos + len
    o = o + len
    stored_block = .true.
  end function

  ! 正準ハフマン表の構築(lens(i) = 記号 i-1 の符号長。0 = 不使用)
  subroutine huff_build(lens, n, h)
    integer, intent(in) :: lens(:), n
    type(t_huff), intent(out) :: h
    integer :: i, len, offs(0:15)
    h%cnt(:) = 0
    do i = 1, n
      h%cnt(lens(i)) = h%cnt(lens(i)) + 1
    end do
    h%cnt(0) = 0
    offs(0) = 0
    do len = 1, 15
      offs(len) = offs(len-1) + h%cnt(len-1)
    end do
    do i = 1, n
      if (lens(i) /= 0) then
        offs(lens(i)) = offs(lens(i)) + 1
        h%sym(offs(lens(i))) = i - 1
      end if
    end do
  end subroutine

  ! 1 記号の復号(puff.c 方式の逐次復号)。破損は負値
  integer function decode_sym(h)
    type(t_huff), intent(in) :: h
    integer :: len, code, first, index, b, n
    code = 0
    first = 0
    index = 0
    do len = 1, 15
      b = bits(1)
      if (b < 0) then
        decode_sym = -1
        return
      end if
      code = ior(code, b)
      n = h%cnt(len)
      if (code - first < n) then
        decode_sym = h%sym(index + code - first + 1)
        return
      end if
      index = index + n
      first = ishft(first + n, 1)
      code = ishft(code, 1)
    end do
    decode_sym = -1
  end function

  ! 固定ハフマン表
  function fixed_lit() result(h)
    type(t_huff) :: h
    integer :: lens(288), i
    do i = 1, 144
      lens(i) = 8
    end do
    do i = 145, 256
      lens(i) = 9
    end do
    do i = 257, 280
      lens(i) = 7
    end do
    do i = 281, 288
      lens(i) = 8
    end do
    call huff_build(lens, 288, h)
  end function

  function fixed_dist() result(h)
    type(t_huff) :: h
    integer :: lens(30)
    lens(:) = 5
    call huff_build(lens, 30, h)
  end function

  ! 動的ハフマン表の読み込み(HLIT/HDIST/HCLEN と符号長列)
  logical function dynamic_tables(hlit, hdist)
    type(t_huff), intent(out) :: hlit, hdist
    type(t_huff) :: hcl
    integer :: nlit, ndist, ncl, i, v, sym, rep, prev
    integer :: cl_lens(19), lens(320)

    dynamic_tables = .false.
    nlit = bits(5)
    ndist = bits(5)
    ncl = bits(4)
    if (nlit < 0 .or. ndist < 0 .or. ncl < 0) return
    nlit = nlit + 257
    ndist = ndist + 1
    ncl = ncl + 4
    cl_lens(:) = 0
    do i = 1, ncl
      v = bits(3)
      if (v < 0) return
      cl_lens(clorder(i) + 1) = v
    end do
    call huff_build(cl_lens, 19, hcl)

    ! 符号長列(16: 直前を 3-6 回、17: 0 を 3-10 回、18: 0 を 11-138 回)
    i = 0
    prev = 0
    do while (i < nlit + ndist)
      sym = decode_sym(hcl)
      if (sym < 0) return
      if (sym < 16) then
        i = i + 1
        lens(i) = sym
        prev = sym
      else
        select case (sym)
          case (16)
            rep = bits(2)
            if (rep < 0 .or. i == 0) return
            rep = rep + 3
            v = prev
          case (17)
            rep = bits(3)
            if (rep < 0) return
            rep = rep + 3
            v = 0
          case default                               ! 18
            rep = bits(7)
            if (rep < 0) return
            rep = rep + 11
            v = 0
        end select
        if (i + rep > nlit + ndist) return
        lens(i+1:i+rep) = v
        i = i + rep
        prev = v
      end if
    end do
    if (lens(257) == 0) return                       ! 終端記号 256 は必須
    call huff_build(lens(1:nlit), nlit, hlit)
    call huff_build(lens(nlit+1:nlit+ndist), ndist, hdist)
    dynamic_tables = .true.
  end function

  ! 圧縮ブロック本体(リテラル/長さ+距離)
  logical function huff_block(hlit, hdist)
    type(t_huff), intent(in) :: hlit, hdist
    integer :: sym, eb
    integer(int64) :: len, dist, k

    huff_block = .false.
    do
      sym = decode_sym(hlit)
      if (sym < 0) return
      if (sym < 256) then                            ! リテラル
        if (o + 1 > nu) return
        o = o + 1
        ubuf(o) = int(sym - merge(256, 0, sym > 127), int8)
      else if (sym == 256) then                      ! ブロック終端
        huff_block = .true.
        return
      else                                           ! 長さ+距離のコピー
        if (sym > 285) return
        eb = bits(lextra(sym - 256))
        if (eb < 0) return
        len = lbase(sym - 256) + eb
        sym = decode_sym(hdist)
        if (sym < 0 .or. sym > 29) return
        eb = bits(dextra(sym + 1))
        if (eb < 0) return
        dist = dbase(sym + 1) + int(eb, int64)
        if (dist > o .or. o + len > nu) return
        do k = 1, len                                ! 重なりは逐次コピーで正
          ubuf(o+k) = ubuf(o+k-dist)
        end do
        o = o + len
      end if
    end do
  end function

end subroutine

end module
