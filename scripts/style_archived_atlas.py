"""Apply the shared palette to vector symbols in the archived map atlas.

Only exact vector colour operators are replaced. Map imagery, geographical
coordinates, legends, values and raster population data are unchanged. The
original is retained once in figures/archive_sources for reproducible reruns.
"""
from pathlib import Path
import shutil
import pymupdf
from pypdf import PdfReader,PdfWriter
from pypdf.generic import ContentStream,FloatObject
from figure_style import MULTI,VOTE,SINGLE_LIGHT,MULTI_LIGHT
ROOT=Path(__file__).resolve().parents[1];FIG=ROOT/'manuscript/figures'
MAPPING={'#2E86AB':MULTI,'#1F5F75':'#00517F','#F24236':VOTE,'#B8312F':'#963F00',
         '#2f9e44':SINGLE_LIGHT,'#f2c14e':MULTI_LIGHT,'#e8590c':'#367DA8','#c92a2a':'#15486D',
         '#1e4e9e':MULTI}


def rgb(h):return tuple(int(h[i:i+2],16)/255 for i in (1,3,5))


def main():
    src=FIG/'archive_sources/supp_atlas.pdf';src.parent.mkdir(exist_ok=True)
    if not src.exists():shutil.copy2(FIG/'supp_atlas.pdf',src)
    writer=PdfWriter(clone_from=src);page=writer.pages[0]
    stream=ContentStream(page.get_contents(),writer);count=0
    mapping=[(rgb(a),rgb(b)) for a,b in MAPPING.items()]
    for operands,op in stream.operations:
        if op not in (b'RG',b'rg'):continue
        for old,new in mapping:
            if max(abs(float(a)-b) for a,b in zip(operands,old))<1e-5:
                operands[:]=[FloatObject(v) for v in new];count+=1;break
    page.replace_contents(stream)
    with (FIG/'supp_atlas.pdf').open('wb') as f:writer.write(f)
    doc=pymupdf.open(FIG/'supp_atlas.pdf');doc[0].get_pixmap(dpi=180).save(FIG/'supp_atlas.png')
    assert count>=10,count
    print('Updated vector colour operators:',count)


if __name__=='__main__':main()
