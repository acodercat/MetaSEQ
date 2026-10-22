"""Per-criterion deployment means, from the local fixed judge panel."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import table_deployment as td
from data_figure_style import setup,save,WIDTH,MM,INK,BLUE_MAP
setup()
OUT=Path(__file__).resolve().parents[1]/'manuscript/figures/supp_heatmap.pdf'


def main():
    data={m:[np.mean(td.query_scores(td.load(m),criterion=c)) for c in td.CRITERIA] for m in td.MODELS}
    models=sorted(data,key=lambda m:-np.mean(data[m]));values=np.array([data[m] for m in models])
    fig=plt.figure(figsize=(WIDTH,85*MM));ax=fig.add_axes([.205,.22,.625,.62])
    im=ax.imshow(values,cmap=BLUE_MAP,vmin=.65,vmax=1,aspect='auto',interpolation='none')
    ax.set(xticks=range(5),yticks=range(6),yticklabels=[td.LABELS[m] for m in models],
           xticklabels=['Methodological\nsoundness','Technical\nimplementation','Data integration\nand synthesis',
                        'Response\nalignment','Faithfulness'])
    ax.xaxis.tick_top();ax.tick_params(length=0,pad=5)
    for spine in ax.spines.values():spine.set_visible(False)
    for i in range(6):
        for j in range(5):
            v=values[i,j]
            rgb=np.array(im.cmap(im.norm(v))[:3])
            linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
            luminance=linear @ np.array([.2126,.7152,.0722])
            ax.text(j,i,f'{v:.2f}',ha='center',va='center',
                    color='white' if luminance<.179 else INK,fontsize=8)
    ax.set_xticks(np.arange(-.5,5),minor=True);ax.set_yticks(np.arange(-.5,6),minor=True)
    ax.grid(which='minor',color='white',lw=2);ax.tick_params(which='minor',length=0)
    for i,m in enumerate(models):fig.text(.89,.22+.62*(1-(i+.5)/6),f'{np.mean(data[m]):.3f}',ha='center',va='center',weight='bold',fontsize=8)
    fig.text(.89,.86,'Mean',ha='center',weight='bold')
    cb=fig.colorbar(im,cax=fig.add_axes([.205,.12,.625,.025]),orientation='horizontal',ticks=[.65,.75,.85,1])
    cb.outline.set_visible(False);cb.set_label('Mean judge score',labelpad=1)
    save(fig,OUT)


if __name__=='__main__':main()
