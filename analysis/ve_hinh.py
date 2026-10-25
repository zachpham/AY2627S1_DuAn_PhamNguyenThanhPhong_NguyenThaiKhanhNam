# -*- coding: utf-8 -*-
"""Ve cac hinh cho Chuong 7 cua bao cao.

Cach dung:
    py analysis/ve_hinh.py

Ghi ra output/hinh/hinh1.png ... hinh4.png, 200 dpi, be ngang 6,1 inch cho khop
vung chu cua trang A4 trong mau bao cao cua Khoa.

So lieu KHONG go tay o day ma doc tu:
  * output/do_luong.csv                        - so do cua nhom
  * output/e8_do_luong.csv                     - bo thi nghiem E8 day du (5 lan lap)
  * output/runs/e8_quet_maxavg_mushroom.txt    - quet maxAvg so bo, co hai muc
                                                 maxAvg 500 va 50 ma E8 khong chay
Rieng cac con so cua bai bao F0 thi phai go tay, vi chung doc tu truc hinh ve
trong bai bao chu khong co file nao - xem HINH_F0 ben duoi.
"""

import csv
import io
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RA = os.path.join(GOC, 'output', 'hinh')

# So lieu doc tu truc hinh ve cua F0. Cach doc va cach kiem chung xem muc 6.5
# cua bao cao: doc lai bon gia tri ma F0 ghi bang chu cho connect_negative thi
# ra dung bon con so do, nen sai so doc truc la nho.
HINH_F0 = {
    # minUtil (trieu) -> (giay o Hinh 5(a), MB o Hinh 6(a))
    'accidents': {19: (27, 1350), 18: (45, 1415), 17: (62, 1635),
                  15: (165, 1820), 13: (310, 2150)},
    # minUtil (trieu) -> giay o Hinh 5(c)
    'pumsb': {5.8: 77, 5.6: 159, 5.0: 778},
}

# Ngoai suy hai muc khong chay, xem Bang 7.6 cua bao cao. Hai kich ban: ti le
# ung vien giu nguyen x3,29, hoac ti le tiep tuc tang x1,32 moi buoc nhu da do
# duoc giua ba muc that.
NGOAI_SUY = {
    5.2: (264e6, 348e6),
    5.0: (869e6, 1986e6),
}

# Ngoai suy CU, da bi chinh phep do phu dinh: gia dinh ti le khong doi x2,495
# thi muc 5,4 chi can 61 M ung vien, trong khi do duoc 80,4 M. Ve len hinh vi
# do chinh la lap luan "ti le tu no cung dang tang" cua muc 7.5.
NGOAI_SUY_CU = {5.4: 61.1e6}


def doc_so_do():
    """Doc output/do_luong.csv, chi lay cac lan chay cua ban da sua."""
    duong = os.path.join(GOC, 'output', 'do_luong.csv')
    hang = list(csv.DictReader(io.open(duong, encoding='utf-8', errors='replace')))
    ra = []
    for h in hang:
        if h.get('ban') != 'da_sua':
            continue
        ra.append({
            'bo': h['dataset'],
            'minUtil': int(h['minUtil']),
            'minAvg': int(h['minAvg']),
            'mau': int(h['mau']),
            'ung_vien': int(h['ung_vien']),
            'giay': float(h['thoi_gian_ms']) / 1000.0,
            'mb': float(h['bo_nho_mb']) if h['bo_nho_mb'] else None,
        })
    return ra


def doc_quet_so_bo():
    """Doc quet maxAvg so bo. Tra ve {maxAvg: {'a': (eucp, escp), 'b': (...)}}."""
    duong = os.path.join(GOC, 'output', 'runs', 'e8_quet_maxavg_mushroom.txt')
    ra = {}
    for dong in io.open(duong, encoding='utf-8'):
        truong = dong.split()
        # step: bo dong chu thich va dong tieu de cot
        if not truong or dong.startswith('#') or truong[0] == 'maxAvg':
            continue
        ma = int(truong[0])
        bien_the = truong[2][-1]          # 'e8_a' -> 'a'
        eucp, escp = int(truong[8]), int(truong[9])
        ra.setdefault(ma, {})[bien_the] = (eucp, escp)
    return ra


def doc_quet_e8():
    """Doc bo E8 day du, chi lay mushroom. Tra ve cung dang doc_quet_so_bo."""
    duong = os.path.join(GOC, 'output', 'e8_do_luong.csv')
    ra = {}
    for h in csv.DictReader(io.open(duong, encoding='utf-8', errors='replace')):
        if h['dataset'] != 'mushroom':
            continue
        ma = int(h['maxAvg'])
        bien_the = h['bien_the'][-1]
        cap = (int(h['loai_eucp']), int(h['loai_escp']))
        # step: moi lan lap phai ra y het nhau, bo dem la tat dinh
        cu = ra.setdefault(ma, {}).get(bien_the)
        if cu is not None and cu != cap:
            raise AssertionError('maxAvg %d bien the %s: %s khac %s'
                                 % (ma, bien_the, cap, cu))
        ra[ma][bien_the] = cap
    return ra


def gop_quet():
    """Gop hai nguon quet maxAvg, doi chieu cac muc trung nhau.

    E8 chay 5 muc (2000, 100, 20, 10, 5) voi 5 lan lap moi bien the; quet so bo
    chay 6 muc (2000, 500, 100, 50, 20, 10) voi 3 lan. Hai nguon do boi hai bo
    khung khac nhau cach nhau ba ngay, nen cho trung nhau chinh la mot phep kiem
    chung doc lap - khac nhau la co loi, phai dung.
    """
    so_bo = doc_quet_so_bo()
    e8 = doc_quet_e8()
    trung = sorted(set(so_bo) & set(e8), reverse=True)
    for ma in trung:
        for bt in ('a', 'b'):
            if so_bo[ma][bt] != e8[ma][bt]:
                raise AssertionError(
                    'maxAvg %d bien the %s lech giua hai nguon: so bo %s, E8 %s'
                    % (ma, bt, so_bo[ma][bt], e8[ma][bt]))
    print('  doi chieu hai nguon quet maxAvg o %d muc trung nhau (%s): khop het'
          % (len(trung), ', '.join(str(m) for m in trung)))
    gop = dict(so_bo)
    gop.update(e8)
    return gop


def venn(cap_a, cap_b):
    """Dung lai bieu do Venn tu hai thu tu chay.

    Chay EUCP truoc thi EUCP thay moi cap, nen so no loai chinh la |EUCP|; con
    so ESCP cua lan chay do la phan ESCP bat duoc ma EUCP khong bat. Chay ESCP
    truoc thi tuong tu cho |ESCP|. Hai lan chay do du ca bieu do Venn, va con
    so thu hai cua moi lan la mot phep kiem du.
    """
    eucp = cap_a[0]                       # |EUCP|
    escp = cap_b[1]                       # |ESCP|
    hop = cap_a[0] + cap_a[1]             # |EUCP hop ESCP|
    if cap_b[0] + cap_b[1] != hop:
        raise AssertionError('hai thu tu cho tong khac nhau: %d va %d'
                             % (hop, cap_b[0] + cap_b[1]))
    ca_hai = eucp + escp - hop
    rieng_escp = escp - ca_hai
    rieng_eucp = eucp - ca_hai
    # step: con so thu hai cua moi lan chay phai bang dung phan rieng cua bo loc
    #       dat sau. Neu lech thi mot trong hai lan chay sai.
    assert cap_a[1] == rieng_escp, 'kiem du ESCP: %d != %d' % (cap_a[1], rieng_escp)
    assert cap_b[0] == rieng_eucp, 'kiem du EUCP: %d != %d' % (cap_b[0], rieng_eucp)
    return {'eucp': eucp, 'escp': escp, 'hop': hop,
            'ca_hai': ca_hai, 'rieng_eucp': rieng_eucp, 'rieng_escp': rieng_escp}


def dat_khung():
    """Dat dinh dang chuan cho moi hinh trong bao cao."""
    plt.rcParams.update({
        'font.size': 9,
        'axes.labelsize': 9,
        'axes.titlesize': 9.5,
        'legend.fontsize': 8.5,
        'xtick.labelsize': 8.5,
        'ytick.labelsize': 8.5,
        'axes.grid': True,
        'grid.alpha': 0.3,
        'grid.linestyle': ':',
        'axes.spines.top': False,
        'axes.spines.right': False,
        'figure.dpi': 200,
    })


def luu(fig, ten):
    if not os.path.isdir(RA):
        os.makedirs(RA)
    duong = os.path.join(RA, ten)
    fig.savefig(duong, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('  %s (%d byte)' % (ten, os.path.getsize(duong)))
    return duong


# ---------------------------------------------------------------------------

def hinh1_thoi_gian_accidents(so_do):
    """Thoi gian chay tren accidents_negative: do duoc so voi Hinh 5(a) cua F0."""
    d = sorted((r for r in so_do if r['bo'] == 'accidents' and r['minAvg'] == 5),
               key=lambda r: r['minUtil'])
    x = [r['minUtil'] / 1e6 for r in d]
    y = [r['giay'] for r in d]
    y_f0 = [HINH_F0['accidents'][round(v)][0] for v in x]

    fig, ax = plt.subplots(figsize=(6.1, 3.2))
    ax.plot(x, y, 'o-', color='#1f4e79', label='Corrected build (measured)')
    ax.plot(x, y_f0, 's--', color='#a0a0a0', label='Figure 5(a) of F0')
    # step: ghi ti le ngay tren tung diem, vi do chinh la lap luan cua muc 7.4
    for xi, yi, yf in zip(x, y, y_f0):
        ax.annotate('x%.2f' % (yi / yf), (xi, yi), textcoords='offset points',
                    xytext=(0, 7), ha='center', fontsize=7.5, color='#1f4e79')
    ax.set_xlabel('minUtil (millions)')
    ax.set_ylabel('runtime (s)')
    ax.invert_xaxis()
    ax.legend(frameon=False)
    return luu(fig, 'hinh1.png')


def hinh2_bo_nho_accidents(so_do):
    """Bo nho dinh tren accidents_negative: do duoc so voi Hinh 6(a) cua F0."""
    d = sorted((r for r in so_do if r['bo'] == 'accidents' and r['minAvg'] == 5),
               key=lambda r: r['minUtil'])
    x = [r['minUtil'] / 1e6 for r in d]
    y = [r['mb'] for r in d]
    y_f0 = [HINH_F0['accidents'][round(v)][1] for v in x]

    fig, ax = plt.subplots(figsize=(6.1, 3.2))
    ax.plot(x, y, 'o-', color='#1f4e79', label='Corrected build (measured)')
    ax.plot(x, y_f0, 's--', color='#a0a0a0', label='Figure 6(a) of F0')
    ax.set_xlabel('minUtil (millions)')
    ax.set_ylabel('peak memory (MB)')
    ax.set_ylim(0, 2400)
    ax.invert_xaxis()
    ax.legend(frameon=False, loc='lower left')
    return luu(fig, 'hinh2.png')


def hinh3_ung_vien_pumsb(so_do):
    """So ung vien tren pumsb_negative: ba muc da xong va ngoai suy hai muc con."""
    d = sorted((r for r in so_do if r['bo'] == 'pumsb'),
               key=lambda r: -r['minUtil'])
    x = [r['minUtil'] / 1e6 for r in d]
    y = [r['ung_vien'] for r in d]

    fig, ax = plt.subplots(figsize=(6.1, 3.6))

    # step: dai ngoai suy giua hai kich ban, noi tu diem do duoc cuoi cung
    x_ns = [x[-1]] + sorted(NGOAI_SUY, reverse=True)
    duoi = [y[-1]] + [NGOAI_SUY[k][0] for k in sorted(NGOAI_SUY, reverse=True)]
    tren = [y[-1]] + [NGOAI_SUY[k][1] for k in sorted(NGOAI_SUY, reverse=True)]
    ax.fill_between(x_ns, duoi, tren, color='#c00000', alpha=0.13,
                    label='extrapolation, not measured')
    ax.plot(x_ns, duoi, '--', color='#c00000', lw=1.0)
    ax.plot(x_ns, tren, '--', color='#c00000', lw=1.0)

    # step: ngoai suy CU chi den muc 5,4 - ve len de thay no da thieu bao nhieu
    x_cu = [x[1]] + sorted(NGOAI_SUY_CU, reverse=True)
    y_cu = [y[1]] + [NGOAI_SUY_CU[k] for k in sorted(NGOAI_SUY_CU, reverse=True)]
    ax.plot(x_cu, y_cu, ':', color='#808080', lw=1.3,
            label='superseded extrapolation at a constant x2.50')
    ax.annotate('predicted 61 M', (x_cu[-1], y_cu[-1]), textcoords='offset points',
                xytext=(4, -13), fontsize=7.5, color='#808080')

    ax.plot(x, y, 'o-', color='#1f4e79', lw=1.6, markersize=6,
            label='Corrected build (completed runs)')
    for xi, yi in zip(x, y):
        ax.annotate('%.2f M' % (yi / 1e6), (xi, yi), textcoords='offset points',
                    xytext=(0, 9), ha='center', fontsize=7.5, color='#1f4e79')

    ax.set_yscale('log')
    ax.set_xlabel('minUtil (millions)')
    ax.set_ylabel('candidates examined (log scale)')
    ax.set_xticks([5.8, 5.6, 5.4, 5.2, 5.0])
    ax.invert_xaxis()
    ax.legend(frameon=False, loc='upper left', fontsize=8)
    # step: nhac lai ket qua chinh cua muc 7.1 - ban cong bo khong mo nhanh nao,
    #       khong ve len duoc vi 0 khong nam tren truc log
    ax.text(0.98, 0.04, 'Published build: 0 candidates at every level',
            transform=ax.transAxes, ha='right', fontsize=8, color='#808080')
    return luu(fig, 'hinh3.png')


def hinh4_quet_maxavg(quet):
    """Hai o: thu tu khong doi tong, va phan moi bo loc bat duoc rieng."""
    ma = sorted(quet, reverse=True)
    nhan = [str(m) for m in ma]
    v = [venn(quet[m]['a'], quet[m]['b']) for m in ma]
    x = range(len(ma))

    fig, (tren, duoi) = plt.subplots(2, 1, figsize=(6.1, 5.6))

    # --- o tren: A va B canh nhau, tong y nhau -----------------------------
    w = 0.3
    xa = [i - w / 2 - 0.045 for i in x]
    xb = [i + w / 2 + 0.045 for i in x]
    a_eucp = [quet[m]['a'][0] for m in ma]
    a_escp = [quet[m]['a'][1] for m in ma]
    b_eucp = [quet[m]['b'][0] for m in ma]
    b_escp = [quet[m]['b'][1] for m in ma]
    tren.bar(xa, a_eucp, w, color='#1f4e79', label='rejected by EUCP')
    tren.bar(xa, a_escp, w, bottom=a_eucp, color='#9dc3e6', label='rejected by ESCP')
    tren.bar(xb, b_eucp, w, color='#1f4e79')
    tren.bar(xb, b_escp, w, bottom=b_eucp, color='#9dc3e6')
    # step: dan chu A / B duoi tung cot cho ro cot nao la bien the nao
    for i in x:
        tren.annotate('A', (xa[i], 0), textcoords='offset points', xytext=(0, -13),
                      ha='center', fontsize=7.5, color='#404040')
        tren.annotate('B', (xb[i], 0), textcoords='offset points', xytext=(0, -13),
                      ha='center', fontsize=7.5, color='#404040')
        tren.annotate(str(v[i]['hop']), (i, v[i]['hop']), textcoords='offset points',
                      xytext=(0, 4), ha='center', fontsize=7.5, color='#404040')
    tren.set_xticks(list(x))
    tren.set_xticklabels(nhan)
    tren.set_xlabel('maxAvg          (A = EUCP first, B = ESCP first)')
    tren.set_ylabel('candidate pairs rejected')
    tren.tick_params(axis='x', pad=14)
    # step: de chu thich ra ngoai khung, khong thi no de len cot cao nhat
    tren.set_ylim(0, max(d['hop'] for d in v) * 1.12)
    tren.legend(frameon=False, ncol=2, loc='lower center', bbox_to_anchor=(0.5, 1.01))

    # --- o duoi: bieu do Venn dung lai tu hai thu tu -----------------------
    ca_hai = [d['ca_hai'] for d in v]
    r_eucp = [d['rieng_eucp'] for d in v]
    r_escp = [d['rieng_escp'] for d in v]
    w2 = 0.5
    duoi.bar(list(x), ca_hai, w2, color='#bfbfbf', label='rejected by both')
    duoi.bar(list(x), r_eucp, w2, bottom=ca_hai, color='#1f4e79',
             label='EUCP alone')
    duoi.bar(list(x), r_escp, w2,
             bottom=[c + e for c, e in zip(ca_hai, r_eucp)], color='#ed7d31',
             label='ESCP alone')
    # step: ghi so phan rieng cua ESCP len dau cot - day la ket qua chinh:
    #       bang 0 cho den khi maxAvg giam xuong 20
    for i in x:
        duoi.annotate(str(r_escp[i]), (i, v[i]['hop']), textcoords='offset points',
                      xytext=(0, 4), ha='center', fontsize=7.5, color='#ed7d31')
    duoi.set_xticks(list(x))
    duoi.set_xticklabels(nhan)
    duoi.set_xlabel('maxAvg')
    duoi.set_ylabel('candidate pairs rejected')
    duoi.set_ylim(0, max(d['hop'] for d in v) * 1.12)
    duoi.legend(frameon=False, ncol=3, loc='lower center', bbox_to_anchor=(0.5, 1.01))

    fig.subplots_adjust(hspace=0.62)
    return luu(fig, 'hinh4.png')


def main():
    dat_khung()
    so_do = doc_so_do()
    print('doc so lieu:')
    quet = gop_quet()
    print('ve hinh vao output/hinh/:')
    hinh1_thoi_gian_accidents(so_do)
    hinh2_bo_nho_accidents(so_do)
    hinh3_ung_vien_pumsb(so_do)
    hinh4_quet_maxavg(quet)
    print('xong')


if __name__ == '__main__':
    main()
